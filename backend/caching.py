"""
Caching layer for sessions and API responses
Uses Redis for distributed caching with fallback to in-memory cache
"""
import json
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import hashlib
import pickle

logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory cache
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Using in-memory cache only.")

from config import get_settings

settings = get_settings()


class CacheBackend:
    """Abstract cache backend interface"""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL"""
        raise NotImplementedError
    
    async def delete(self, key: str):
        """Delete key from cache"""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        raise NotImplementedError
    
    async def clear(self):
        """Clear all cache"""
        raise NotImplementedError


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else "redis://localhost:6379/0"
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis not available")
        
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False  # We'll handle serialization ourselves
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Disconnected from Redis cache")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self._connected or not self.redis:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in Redis"""
        if not self._connected or not self.redis:
            return
        
        try:
            data = pickle.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, data)
            else:
                await self.redis.set(key, data)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
    
    async def delete(self, key: str):
        """Delete key from Redis"""
        if not self._connected or not self.redis:
            return
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        if not self._connected or not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False
    
    async def clear(self):
        """Clear all cache (use with caution!)"""
        if not self._connected or not self.redis:
            return
        
        try:
            await self.redis.flushdb()
            logger.warning("Redis cache cleared")
        except Exception as e:
            logger.error(f"Redis clear error: {str(e)}")


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend (fallback when Redis is not available)"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._max_size = 1000  # Maximum number of items
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        
        # Check if expired
        if expiry and datetime.utcnow() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in memory cache"""
        # Evict oldest if cache is full
        if len(self._cache) >= self._max_size and key not in self._cache:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1] or datetime.max)
            del self._cache[oldest_key]
        
        expiry = None
        if ttl:
            expiry = datetime.utcnow() + timedelta(seconds=ttl)
        
        self._cache[key] = (value, expiry)
    
    async def delete(self, key: str):
        """Delete key from memory cache"""
        self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache"""
        if key not in self._cache:
            return False
        
        # Check if expired
        _, expiry = self._cache[key]
        if expiry and datetime.utcnow() > expiry:
            del self._cache[key]
            return False
        
        return True
    
    async def clear(self):
        """Clear all cache"""
        self._cache.clear()


class CacheManager:
    """Cache manager with automatic backend selection"""
    
    def __init__(self):
        self.backend: Optional[CacheBackend] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize cache backend"""
        if self._initialized:
            return
        
        # Try Redis first
        if REDIS_AVAILABLE:
            try:
                backend = RedisCacheBackend()
                await backend.connect()
                self.backend = backend
                logger.info("Using Redis cache backend")
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to memory cache: {str(e)}")
                self.backend = MemoryCacheBackend()
        else:
            self.backend = MemoryCacheBackend()
            logger.info("Using in-memory cache backend")
        
        self._initialized = True
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._initialized:
            await self.initialize()
        
        if not self.backend:
            return None
        
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache"""
        if not self._initialized:
            await self.initialize()
        
        if not self.backend:
            return
        
        await self.backend.set(key, value, ttl)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self._initialized:
            await self.initialize()
        
        if not self.backend:
            return
        
        await self.backend.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self._initialized:
            await self.initialize()
        
        if not self.backend:
            return False
        
        return await self.backend.exists(key)
    
    async def clear(self):
        """Clear all cache"""
        if not self._initialized:
            await self.initialize()
        
        if not self.backend:
            return
        
        await self.backend.clear()
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional args
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword args (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        # Create hash for long keys
        key_str = ":".join(key_parts)
        if len(key_str) > 200:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key_str
    
    async def get_or_set(
        self,
        key: str,
        fetch_func,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Get value from cache, or fetch and cache if not present
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch value if not in cache
            ttl: Time to live in seconds
            *args, **kwargs: Arguments to pass to fetch_func
        """
        # Try to get from cache
        cached_value = await self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Fetch value
        if asyncio.iscoroutinefunction(fetch_func):
            value = await fetch_func(*args, **kwargs)
        else:
            value = fetch_func(*args, **kwargs)
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value


# Global cache manager instance
cache_manager = CacheManager()


# Convenience functions
async def get_cached(key: str) -> Optional[Any]:
    """Get value from cache"""
    return await cache_manager.get(key)


async def set_cached(key: str, value: Any, ttl: Optional[int] = None):
    """Set value in cache"""
    await cache_manager.set(key, value, ttl)


async def delete_cached(key: str):
    """Delete key from cache"""
    await cache_manager.delete(key)


async def cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate cache key"""
    return cache_manager._generate_key(prefix, *args, **kwargs)

