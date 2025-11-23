"""
Retry logic module with exponential backoff for LLM API calls
Provides robust retry mechanisms with circuit breaker pattern
"""
import asyncio
import logging
from typing import Callable, TypeVar, Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import time

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitBreakerState.CLOSED
        self.success_count = 0
        self.half_open_success_threshold = 2
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker: Moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs):
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker: Moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker: Service recovered, moving to CLOSED state")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker: Service still failing, moving back to OPEN state")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.error(f"Circuit breaker: OPENED after {self.failure_count} failures")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker: Manually reset")


class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_exceptions: Optional[List[type]] = None,
        jitter: bool = True,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.strategy = strategy
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.jitter = jitter
        self.circuit_breaker = circuit_breaker
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should be retried"""
        if attempt >= self.max_attempts:
            return False
        
        # Check if exception is retryable
        if not any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions):
            return False
        
        # Check circuit breaker
        if self.circuit_breaker and self.circuit_breaker.state == CircuitBreakerState.OPEN:
            return False
        
        return True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        if self.strategy == RetryStrategy.NO_RETRY:
            return 0
        
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.initial_delay
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay * attempt
        else:  # EXPONENTIAL_BACKOFF
            delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        
        # Apply max delay cap
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Retry an async function with exponential backoff
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        config: Retry configuration
        **kwargs: Keyword arguments for func
    
    Returns:
        Result from func
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            # Check circuit breaker
            if config.circuit_breaker:
                return await config.circuit_breaker.call_async(func, *args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        except Exception as e:
            last_exception = e
            
            if not config.should_retry(e, attempt):
                logger.error(f"Retry failed after {attempt} attempts: {str(e)}")
                raise
            
            delay = config.get_delay(attempt)
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            await asyncio.sleep(delay)
    
    # All retries exhausted
    logger.error(f"All {config.max_attempts} retry attempts exhausted")
    raise last_exception


def retry_sync(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> T:
    """
    Retry a synchronous function with exponential backoff
    
    Args:
        func: Function to retry
        *args: Positional arguments for func
        config: Retry configuration
        **kwargs: Keyword arguments for func
    
    Returns:
        Result from func
    
    Raises:
        Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            # Check circuit breaker
            if config.circuit_breaker:
                return config.circuit_breaker.call(func, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        except Exception as e:
            last_exception = e
            
            if not config.should_retry(e, attempt):
                logger.error(f"Retry failed after {attempt} attempts: {str(e)}")
                raise
            
            delay = config.get_delay(attempt)
            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            time.sleep(delay)
    
    # All retries exhausted
    logger.error(f"All {config.max_attempts} retry attempts exhausted")
    raise last_exception


# Pre-configured retry configs for common scenarios
LLM_API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    retryable_exceptions=[
        Exception,  # Will be narrowed down in actual usage
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError
    ],
    jitter=True
)

# Circuit breakers for different LLM providers
circuit_breakers: Dict[str, CircuitBreaker] = {
    "openai": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "anthropic": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "deepseek": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
    "replicate": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
}

