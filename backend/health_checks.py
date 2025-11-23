"""
Enhanced health check endpoints
Provides liveness, readiness, and dependency health checks
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from fastapi import HTTPException
from database import SessionLocal, AnalysisSession
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth:
    """Health status of a dependency"""
    
    def __init__(self, name: str, status: HealthStatus, message: str = "", response_time_ms: float = 0):
        self.name = name
        self.status = status
        self.message = message
        self.response_time_ms = response_time_ms
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": round(self.response_time_ms, 2)
        }


class HealthChecker:
    """Health check manager"""
    
    def __init__(self):
        self.dependencies: List[str] = []
    
    async def check_database(self) -> DependencyHealth:
        """Check database connectivity"""
        start_time = datetime.utcnow()
        
        try:
            db = SessionLocal()
            try:
                # Try a simple query
                db.query(AnalysisSession).limit(1).all()
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return DependencyHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection successful",
                    response_time_ms=response_time
                )
            finally:
                db.close()
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Database health check failed: {str(e)}")
            
            return DependencyHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_redis(self) -> DependencyHealth:
        """Check Redis connectivity (if used)"""
        start_time = datetime.utcnow()
        
        try:
            from caching import cache_manager
            await cache_manager.initialize()
            
            # Try a simple get/set
            test_key = "health_check_test"
            await cache_manager.set(test_key, "test", ttl=10)
            value = await cache_manager.get(test_key)
            await cache_manager.delete(test_key)
            
            if value == "test":
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return DependencyHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection successful",
                    response_time_ms=response_time
                )
            else:
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return DependencyHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    message="Redis test failed",
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            # Redis is optional, so degraded not unhealthy
            return DependencyHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis not available: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_llm_apis(self) -> DependencyHealth:
        """Check LLM API availability"""
        start_time = datetime.utcnow()
        
        configured_count = sum(1 for key in [
            settings.OPENAI_API_KEY,
            settings.ANTHROPIC_API_KEY,
            settings.DEEPSEEK_API_KEY,
            settings.REPLICATE_API_TOKEN
        ] if key)
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if configured_count == 0:
            return DependencyHealth(
                name="llm_apis",
                status=HealthStatus.UNHEALTHY,
                message="No LLM API keys configured",
                response_time_ms=response_time
            )
        elif configured_count < 4:
            return DependencyHealth(
                name="llm_apis",
                status=HealthStatus.DEGRADED,
                message=f"{configured_count}/4 LLM services configured",
                response_time_ms=response_time
            )
        else:
            return DependencyHealth(
                name="llm_apis",
                status=HealthStatus.HEALTHY,
                message="All LLM services configured",
                response_time_ms=response_time
            )
    
    async def check_disk_space(self) -> DependencyHealth:
        """Check available disk space"""
        start_time = datetime.utcnow()
        
        try:
            import shutil
            from pathlib import Path
            
            # Check temp_sessions directory
            temp_dir = Path(settings.TEMP_SESSIONS_DIR)
            if temp_dir.exists():
                stat = shutil.disk_usage(temp_dir)
                free_gb = stat.free / (1024 ** 3)
                total_gb = stat.total / (1024 ** 3)
                free_percent = (stat.free / stat.total) * 100
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if free_percent < 5:
                    return DependencyHealth(
                        name="disk_space",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Low disk space: {free_percent:.1f}% free ({free_gb:.2f} GB)",
                        response_time_ms=response_time
                    )
                elif free_percent < 10:
                    return DependencyHealth(
                        name="disk_space",
                        status=HealthStatus.DEGRADED,
                        message=f"Disk space warning: {free_percent:.1f}% free ({free_gb:.2f} GB)",
                        response_time_ms=response_time
                    )
                else:
                    return DependencyHealth(
                        name="disk_space",
                        status=HealthStatus.HEALTHY,
                        message=f"Disk space OK: {free_percent:.1f}% free ({free_gb:.2f} GB / {total_gb:.2f} GB)",
                        response_time_ms=response_time
                    )
            else:
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                return DependencyHealth(
                    name="disk_space",
                    status=HealthStatus.DEGRADED,
                    message="Temp directory does not exist",
                    response_time_ms=response_time
                )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return DependencyHealth(
                name="disk_space",
                status=HealthStatus.DEGRADED,
                message=f"Could not check disk space: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_all_dependencies(self) -> Dict[str, Any]:
        """Check all dependencies"""
        dependencies = []
        
        # Check all dependencies in parallel
        results = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_llm_apis(),
            self.check_disk_space(),
            return_exceptions=True
        )
        
        for result in results:
            if isinstance(result, DependencyHealth):
                dependencies.append(result.to_dict())
            else:
                logger.error(f"Dependency check failed: {str(result)}")
                dependencies.append({
                    "name": "unknown",
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f"Check failed: {str(result)}",
                    "response_time_ms": 0
                })
        
        # Determine overall status
        statuses = [d["status"] for d in dependencies]
        if HealthStatus.UNHEALTHY.value in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED.value in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": dependencies
        }


# Global health checker instance
health_checker = HealthChecker()


async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe - indicates if the application is running
    Should be fast and not check dependencies
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


async def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe - indicates if the application is ready to serve traffic
    Checks critical dependencies
    """
    # Check only critical dependencies
    db_health = await health_checker.check_database()
    
    if db_health.status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=503,
            detail="Service not ready: Database unavailable"
        )
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_health.to_dict()
    }


async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check with all dependencies
    """
    return await health_checker.check_all_dependencies()

