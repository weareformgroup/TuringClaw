# -*- coding: utf-8 -*-
"""
M5: Error handling and resilience framework.
Provides structured error handling, retry logic, and graceful degradation.
"""
import functools
import time
import logging
from typing import Callable, Any, Optional, Type, Tuple

logger = logging.getLogger("TuringClaw.error")


class ErrorCategory:
    """Error categories for structured handling."""
    NETWORK = "network"        # Connection issues
    AUTH = "auth"              # API key invalid
    RATE_LIMIT = "rate_limit"  # 429 errors
    TIMEOUT = "timeout"        # Request timeout
    MODEL = "model"            # Model unavailable
    PARSE = "parse"            # Response parsing error
    UNKNOWN = "unknown"


class TuringClawError(Exception):
    """Base exception with category and retry hint."""
    def __init__(self, message: str, category: str = ErrorCategory.UNKNOWN,
                 retryable: bool = False, provider: str = ""):
        super().__init__(message)
        self.category = category
        self.retryable = retryable
        self.provider = provider

    def user_message(self) -> str:
        """Generate user-friendly error message."""
        msgs = {
            ErrorCategory.NETWORK: f"无法连接 {self.provider}，请检查网络",
            ErrorCategory.AUTH: f"{self.provider} API Key 无效，请检查配置",
            ErrorCategory.RATE_LIMIT: f"{self.provider} 请求过快，请稍后再试",
            ErrorCategory.TIMEOUT: f"{self.provider} 响应超时",
            ErrorCategory.MODEL: f"{self.provider} 模型不可用",
            ErrorCategory.PARSE: f"{self.provider} 响应解析失败",
            ErrorCategory.UNKNOWN: str(self),
        }
        return msgs.get(self.category, str(self))


def classify_error(error: Exception, provider: str = "") -> TuringClawError:
    """Classify a raw exception into a TuringClawError."""
    msg = str(error).lower()

    if "401" in msg or "unauthorized" in msg or "invalid api key" in msg:
        return TuringClawError(str(error), ErrorCategory.AUTH, retryable=False, provider=provider)
    if "429" in msg or "rate" in msg:
        return TuringClawError(str(error), ErrorCategory.RATE_LIMIT, retryable=True, provider=provider)
    if "timeout" in msg or "timed out" in msg:
        return TuringClawError(str(error), ErrorCategory.TIMEOUT, retryable=True, provider=provider)
    if "connection" in msg or "refused" in msg or "resolve" in msg:
        return TuringClawError(str(error), ErrorCategory.NETWORK, retryable=True, provider=provider)
    if "404" in msg or "model" in msg:
        return TuringClawError(str(error), ErrorCategory.MODEL, retryable=False, provider=provider)

    return TuringClawError(str(error), ErrorCategory.UNKNOWN, retryable=False, provider=provider)


def with_retry(max_retries: int = 3, delay: float = 1.0,
               backoff: float = 2.0, exceptions: Tuple[Type[Exception]] = (Exception,)):
    """Decorator: retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    tc_error = classify_error(e)

                    if not tc_error.retryable and attempt == 0:
                        raise tc_error

                    if attempt < max_retries and tc_error.retryable:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise tc_error

            raise last_error  # type: ignore
        return wrapper
    return decorator


def graceful_degradation(fallback: Any = None):
    """Decorator: return fallback value on error instead of raising.

    Args:
        fallback: Value to return on error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} failed: {e}. Returning fallback.")
                return fallback
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for provider calls.

    After N consecutive failures, circuit opens and blocks calls
    for a cooldown period before trying again.
    """

    def __init__(self, failure_threshold: int = 5, cooldown: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = "closed"  # closed, open, half-open

    @property
    def state(self) -> str:
        return self._state

    def record_success(self):
        """Record a successful call."""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker OPENED after {self._failure_count} failures")

    def can_call(self) -> bool:
        """Check if calls are allowed."""
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.time() - self._last_failure_time > self.cooldown:
                self._state = "half-open"
                return True
            return False
        return True  # half-open allows one attempt


if __name__ == "__main__":
    # Self-test
    @with_retry(max_retries=2, delay=0.1)
    def flaky_function():
        import random
        if random.random() < 0.7:
            raise ConnectionError("Connection refused")
        return "success"

    try:
        result = flaky_function()
        print(f"Result: {result}")
    except TuringClawError as e:
        print(f"Error: {e.user_message()} (retryable={e.retryable})")

    # Circuit breaker test
    cb = CircuitBreaker(failure_threshold=3, cooldown=1.0)
    for i in range(5):
        if cb.can_call():
            print(f"Call {i+1}: allowed")
            cb.record_failure()
        else:
            print(f"Call {i+1}: blocked (state={cb.state})")