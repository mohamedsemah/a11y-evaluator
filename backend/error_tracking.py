"""
Error tracking module with Sentry integration
Provides centralized error tracking and monitoring
"""
import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

# Sentry integration (optional, only if DSN is provided)
sentry_sdk = None
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
except ImportError:
    logger.warning("sentry-sdk not installed. Error tracking will be limited to logging.")


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    release: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
    enable_tracing: bool = True
) -> bool:
    """
    Initialize Sentry error tracking
    
    Args:
        dsn: Sentry DSN (if None, will try to get from SENTRY_DSN env var)
        environment: Environment name (development, staging, production)
        release: Application release version
        traces_sample_rate: Sample rate for performance traces (0.0 to 1.0)
        profiles_sample_rate: Sample rate for profiling (0.0 to 1.0)
        enable_tracing: Whether to enable performance tracing
    
    Returns:
        True if Sentry was initialized, False otherwise
    """
    if sentry_sdk is None:
        logger.warning("Sentry SDK not available. Install with: pip install sentry-sdk")
        return False
    
    dsn = dsn or os.getenv("SENTRY_DSN")
    if not dsn:
        logger.info("Sentry DSN not provided. Error tracking disabled.")
        return False
    
    try:
        integrations = [
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            AsyncioIntegration(),
        ]
        
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
            profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
            integrations=integrations,
            # Set user context
            before_send=before_send_filter,
            # Ignore certain exceptions
            ignore_errors=[
                KeyboardInterrupt,
                SystemExit,
            ],
            # Additional context
            max_breadcrumbs=50,
            attach_stacktrace=True,
        )
        
        logger.info(f"Sentry initialized for environment: {environment}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {str(e)}")
        return False


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry
    Can be used to filter out sensitive information or certain error types
    """
    # Remove sensitive data from event
    if "request" in event and "data" in event["request"]:
        # Remove API keys from request data
        data = event["request"]["data"]
        if isinstance(data, dict):
            for key in list(data.keys()):
                if "key" in key.lower() or "password" in key.lower() or "secret" in key.lower():
                    data[key] = "[REDACTED]"
    
    # Add custom tags
    event.setdefault("tags", {})
    
    return event


def capture_exception(
    exception: Exception,
    level: str = "error",
    context: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Capture an exception to Sentry
    
    Args:
        exception: The exception to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context to include
        user: User information (id, username, email)
        tags: Additional tags for filtering
    
    Returns:
        Event ID if captured, None otherwise
    """
    if sentry_sdk is None:
        logger.error(f"Exception not captured (Sentry not available): {exception}")
        return None
    
    try:
        with sentry_sdk.push_scope() as scope:
            # Set level
            scope.level = level
            
            # Add context
            if context:
                scope.set_context("custom", context)
            
            # Set user
            if user:
                scope.user = user
            
            # Add tags
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)
            
            # Capture exception
            event_id = sentry_sdk.capture_exception(exception)
            return event_id
    except Exception as e:
        logger.error(f"Failed to capture exception to Sentry: {str(e)}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Capture a message to Sentry
    
    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context to include
        tags: Additional tags for filtering
    
    Returns:
        Event ID if captured, None otherwise
    """
    if sentry_sdk is None:
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        return None
    
    try:
        with sentry_sdk.push_scope() as scope:
            scope.level = level
            
            if context:
                scope.set_context("custom", context)
            
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)
            
            event_id = sentry_sdk.capture_message(message, level=level)
            return event_id
    except Exception as e:
        logger.error(f"Failed to capture message to Sentry: {str(e)}")
        return None


def set_user_context(user_id: Optional[str] = None, username: Optional[str] = None, 
                     email: Optional[str] = None, **kwargs):
    """Set user context for Sentry"""
    if sentry_sdk:
        sentry_sdk.set_user({
            "id": user_id,
            "username": username,
            "email": email,
            **kwargs
        })


def add_breadcrumb(message: str, category: str = "default", level: str = "info", 
                  data: Optional[Dict[str, Any]] = None):
    """Add a breadcrumb to Sentry"""
    if sentry_sdk:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data
        )


def track_performance(operation: str, duration_ms: float, **kwargs):
    """Track performance metrics"""
    if sentry_sdk:
        sentry_sdk.set_measurement(operation, duration_ms, unit="millisecond")
        if kwargs:
            with sentry_sdk.push_scope() as scope:
                scope.set_context("performance", kwargs)
                sentry_sdk.capture_message(
                    f"Performance: {operation} took {duration_ms}ms",
                    level="info"
                )


def error_tracker(func):
    """Decorator to automatically track errors in functions"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            capture_exception(
                e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:200],  # Limit length
                    "kwargs": {k: str(v)[:200] for k, v in kwargs.items()}
                }
            )
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            capture_exception(
                e,
                context={
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": {k: str(v)[:200] for k, v in kwargs.items()}
                }
            )
            raise
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

