"""
Unit tests for retry logic
"""
import pytest
import asyncio
from retry_logic import (
    RetryConfig, RetryStrategy, retry_async, retry_sync,
    CircuitBreaker, CircuitBreakerState
)


class TestRetryConfig:
    """Tests for RetryConfig"""
    
    def test_default_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
    
    def test_custom_config(self):
        """Test custom retry configuration"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            strategy=RetryStrategy.FIXED_DELAY
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.strategy == RetryStrategy.FIXED_DELAY
    
    def test_should_retry(self):
        """Test should_retry logic"""
        config = RetryConfig(max_attempts=3)
        
        # Should retry on first attempt
        assert config.should_retry(Exception(), 1) is True
        
        # Should not retry after max attempts
        assert config.should_retry(Exception(), 3) is False
        assert config.should_retry(Exception(), 4) is False


class TestCircuitBreaker:
    """Tests for CircuitBreaker"""
    
    def test_circuit_breaker_closed(self):
        """Test circuit breaker in closed state"""
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Successful call should reset failure count
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after threshold"""
        cb = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise ValueError("Test error")
        
        # First failure
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Second failure - should open
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.failure_count == 2
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when open"""
        cb = CircuitBreaker(failure_threshold=1)
        cb.state = CircuitBreakerState.OPEN
        
        def any_func():
            return "should not execute"
        
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            cb.call(any_func)


class TestRetryAsync:
    """Tests for async retry logic"""
    
    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test successful call doesn't retry"""
        call_count = 0
        
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await retry_async(success_func)
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry on failure"""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        result = await retry_async(failing_func, config=config)
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Test all retries exhausted"""
        call_count = 0
        
        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        config = RetryConfig(max_attempts=2, initial_delay=0.1)
        with pytest.raises(ValueError, match="Always fails"):
            await retry_async(always_failing_func, config=config)
        
        assert call_count == 2


class TestRetrySync:
    """Tests for sync retry logic"""
    
    def test_successful_call(self):
        """Test successful call doesn't retry"""
        call_count = 0
        
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = retry_sync(success_func)
        assert result == "success"
        assert call_count == 1
    
    def test_retry_on_failure(self):
        """Test retry on failure"""
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        config = RetryConfig(max_attempts=3, initial_delay=0.1)
        result = retry_sync(failing_func, config=config)
        assert result == "success"
        assert call_count == 2

