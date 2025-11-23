"""
Structured logging module for production-ready logging
Provides JSON-formatted logs with context and correlation IDs
"""
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None
            }
        
        # Add extra context if present
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add user ID if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        # Add request path if present
        if hasattr(record, "request_path"):
            log_data["request_path"] = record.request_path
        
        # Add session ID if present
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        
        # Add performance metrics if present
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info"
            ] and not key.startswith("_"):
                if key not in log_data:
                    log_data[key] = value
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class StructuredLogger:
    """Wrapper for structured logging with context management"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}
        self.correlation_id: Optional[str] = None
    
    def set_context(self, **kwargs):
        """Set context that will be included in all subsequent log messages"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context"""
        self.context.clear()
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing"""
        self.correlation_id = correlation_id
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context"""
        extra = {
            "context": self.context.copy(),
            **kwargs
        }
        if self.correlation_id:
            extra["correlation_id"] = self.correlation_id
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """Log error message with optional exception info"""
        if exc_info:
            kwargs["exc_info"] = exc_info
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, exc_info=None, **kwargs):
        """Log critical message with optional exception info"""
        if exc_info:
            kwargs["exc_info"] = exc_info
        self._log(logging.CRITICAL, message, **kwargs)
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        self.info(
            f"Performance: {operation}",
            duration_ms=duration_ms,
            operation=operation,
            **kwargs
        )
    
    def log_api_call(self, method: str, url: str, status_code: Optional[int] = None, 
                     duration_ms: Optional[float] = None, **kwargs):
        """Log API call details"""
        self.info(
            f"API call: {method} {url}",
            api_method=method,
            api_url=url,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )


def setup_structured_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_json: bool = True
) -> None:
    """
    Setup structured logging for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file (if None, logs only to console)
        enable_console: Whether to log to console
        enable_json: Whether to use JSON formatting (True) or plain text (False)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    root_logger.propagate = False


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)

