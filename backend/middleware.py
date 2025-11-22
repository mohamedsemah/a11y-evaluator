"""
Custom middleware for security headers and rate limiting
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Rate limiting storage (in-memory, should use Redis in production)
rate_limit_store: Dict[str, list] = defaultdict(list)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # unsafe-inline/eval needed for React
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self' http://localhost:8000 https://api.openai.com https://api.anthropic.com https://api.deepseek.com https://api.replicate.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/detailed"]:
            return await call_next(request)
        
        now = datetime.utcnow()
        
        # Clean old entries (older than 1 hour)
        if client_ip in rate_limit_store:
            rate_limit_store[client_ip] = [
                timestamp for timestamp in rate_limit_store[client_ip]
                if now - timestamp < timedelta(hours=1)
            ]
        
        # Check per-minute limit
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [
            ts for ts in rate_limit_store[client_ip]
            if ts > minute_ago
        ]
        
        if len(recent_requests) >= settings.RATE_LIMIT_PER_MINUTE:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Check per-hour limit
        hour_ago = now - timedelta(hours=1)
        hourly_requests = [
            ts for ts in rate_limit_store[client_ip]
            if ts > hour_ago
        ]
        
        if len(hourly_requests) >= settings.RATE_LIMIT_PER_HOUR:
            logger.warning(f"Hourly rate limit exceeded for IP {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {settings.RATE_LIMIT_PER_HOUR} requests per hour allowed",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )
        
        # Add current request timestamp
        rate_limit_store[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining_minute = max(0, settings.RATE_LIMIT_PER_MINUTE - len(recent_requests) - 1)
        remaining_hour = max(0, settings.RATE_LIMIT_PER_HOUR - len(hourly_requests) - 1)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.RATE_LIMIT_PER_HOUR)
        response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_hour)
        
        return response

