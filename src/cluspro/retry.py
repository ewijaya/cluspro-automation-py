"""
Retry configuration and decorators for ClusPro automation.

Provides configurable retry logic with exponential backoff for
browser operations, network requests, and file downloads.
"""

import logging
from collections.abc import Callable

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_RETRY_CONFIG = {
    "max_attempts": 3,
    "min_wait": 1,
    "max_wait": 30,
    "multiplier": 2,
}

# Selenium exceptions to retry on
SELENIUM_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    WebDriverException,
    TimeoutException,
    StaleElementReferenceException,
)

# Network-related exceptions to retry on
NETWORK_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def get_retry_config(config: dict | None = None) -> dict:
    """
    Get retry configuration from config or defaults.

    Args:
        config: Optional configuration dict with "retry" section

    Returns:
        Retry configuration dict
    """
    if config is None:
        return DEFAULT_RETRY_CONFIG.copy()

    retry_config = config.get("retry", {})
    result = DEFAULT_RETRY_CONFIG.copy()
    result.update(retry_config)
    return result


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 30,
    multiplier: float = 2,
    exceptions: tuple[type[Exception], ...] = SELENIUM_RETRY_EXCEPTIONS,
):
    """
    Create a retry decorator with specified configuration.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        multiplier: Exponential backoff multiplier
        exceptions: Tuple of exception types to retry on

    Returns:
        Configured retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Pre-configured decorators for common use cases

retry_browser = create_retry_decorator(
    max_attempts=3,
    min_wait=2,
    max_wait=30,
    exceptions=SELENIUM_RETRY_EXCEPTIONS,
)

retry_network = create_retry_decorator(
    max_attempts=5,
    min_wait=1,
    max_wait=60,
    exceptions=NETWORK_RETRY_EXCEPTIONS,
)

retry_download = create_retry_decorator(
    max_attempts=3,
    min_wait=5,
    max_wait=60,
    exceptions=(*SELENIUM_RETRY_EXCEPTIONS, *NETWORK_RETRY_EXCEPTIONS),
)


def with_retry(
    func: Callable | None = None,
    *,
    max_attempts: int = 3,
    min_wait: float = 1,
    max_wait: float = 30,
    exceptions: tuple[type[Exception], ...] = SELENIUM_RETRY_EXCEPTIONS,
):
    """
    Decorator to add retry logic to a function.

    Can be used with or without arguments:

        @with_retry
        def my_function():
            ...

        @with_retry(max_attempts=5, min_wait=2)
        def my_function():
            ...

    Args:
        func: Function to wrap (when used without arguments)
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait between retries
        max_wait: Maximum wait between retries
        exceptions: Exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    decorator = create_retry_decorator(
        max_attempts=max_attempts,
        min_wait=min_wait,
        max_wait=max_wait,
        exceptions=exceptions,
    )

    if func is not None:
        return decorator(func)
    return decorator


__all__ = [
    "retry_browser",
    "retry_network",
    "retry_download",
    "with_retry",
    "create_retry_decorator",
    "get_retry_config",
    "SELENIUM_RETRY_EXCEPTIONS",
    "NETWORK_RETRY_EXCEPTIONS",
    "DEFAULT_RETRY_CONFIG",
    "RetryError",
]
