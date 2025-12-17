"""Tests for retry module."""

import pytest
from unittest.mock import MagicMock

from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
)


class TestRetryDecorators:
    """Tests for retry decorator functions."""

    def test_retry_browser_success_first_try(self):
        """Test retry_browser succeeds on first try."""
        from cluspro.retry import retry_browser

        call_count = 0

        @retry_browser
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_browser_retries_on_timeout(self):
        """Test retry_browser retries on TimeoutException."""
        from cluspro.retry import create_retry_decorator

        # Create a decorator with faster retry for testing
        fast_retry = create_retry_decorator(
            max_attempts=3, min_wait=0.01, max_wait=0.02
        )

        call_count = 0

        @fast_retry
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutException("Timeout")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 2

    def test_retry_browser_gives_up_after_max_attempts(self):
        """Test retry_browser gives up after max attempts."""
        from cluspro.retry import create_retry_decorator

        fast_retry = create_retry_decorator(
            max_attempts=2, min_wait=0.01, max_wait=0.02
        )

        call_count = 0

        @fast_retry
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutException("Always fails")

        with pytest.raises(TimeoutException):
            always_fails()

        assert call_count == 2

    def test_retry_browser_does_not_retry_non_selenium_errors(self):
        """Test retry_browser doesn't retry non-Selenium exceptions."""
        from cluspro.retry import retry_browser

        call_count = 0

        @retry_browser
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a Selenium error")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # Should only be called once


class TestWithRetry:
    """Tests for with_retry decorator."""

    def test_with_retry_no_args(self):
        """Test with_retry without arguments."""
        from cluspro.retry import with_retry

        call_count = 0

        @with_retry
        def simple_function():
            nonlocal call_count
            call_count += 1
            return "done"

        result = simple_function()
        assert result == "done"
        assert call_count == 1

    def test_with_retry_custom_attempts(self):
        """Test with_retry with custom max_attempts."""
        from cluspro.retry import with_retry

        call_count = 0

        @with_retry(max_attempts=5, min_wait=0.01, max_wait=0.02)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutException("Flaky")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 3

    def test_with_retry_custom_exceptions(self):
        """Test with_retry with custom exception types."""
        from cluspro.retry import with_retry

        call_count = 0

        @with_retry(
            max_attempts=3,
            min_wait=0.01,
            max_wait=0.02,
            exceptions=(ValueError,),
        )
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom error")
            return "done"

        result = raises_value_error()

        assert result == "done"
        assert call_count == 2


class TestGetRetryConfig:
    """Tests for get_retry_config function."""

    def test_get_retry_config_defaults(self):
        """Test get_retry_config returns defaults."""
        from cluspro.retry import get_retry_config, DEFAULT_RETRY_CONFIG

        config = get_retry_config()

        assert config["max_attempts"] == DEFAULT_RETRY_CONFIG["max_attempts"]
        assert config["min_wait"] == DEFAULT_RETRY_CONFIG["min_wait"]
        assert config["max_wait"] == DEFAULT_RETRY_CONFIG["max_wait"]
        assert config["multiplier"] == DEFAULT_RETRY_CONFIG["multiplier"]

    def test_get_retry_config_from_dict(self):
        """Test get_retry_config from config dict."""
        from cluspro.retry import get_retry_config

        config_dict = {
            "retry": {
                "max_attempts": 5,
                "min_wait": 10,
            }
        }

        config = get_retry_config(config_dict)

        assert config["max_attempts"] == 5
        assert config["min_wait"] == 10

    def test_get_retry_config_empty_dict(self):
        """Test get_retry_config with empty config."""
        from cluspro.retry import get_retry_config, DEFAULT_RETRY_CONFIG

        config = get_retry_config({})

        assert config == DEFAULT_RETRY_CONFIG


class TestPreConfiguredDecorators:
    """Tests for pre-configured decorators."""

    def test_retry_browser_exists(self):
        """Test retry_browser decorator exists."""
        from cluspro.retry import retry_browser

        assert callable(retry_browser)

    def test_retry_network_exists(self):
        """Test retry_network decorator exists."""
        from cluspro.retry import retry_network

        assert callable(retry_network)

    def test_retry_download_exists(self):
        """Test retry_download decorator exists."""
        from cluspro.retry import retry_download

        assert callable(retry_download)
