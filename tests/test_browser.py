"""Tests for browser module."""

from unittest.mock import MagicMock

import pytest


class TestCreateBrowser:
    """Tests for create_browser function."""

    def test_create_browser_headless(self, mocker, mock_config):
        """Test browser creation in headless mode."""
        mock_webdriver = mocker.patch("cluspro.browser.webdriver")
        mocker.patch("cluspro.browser.GeckoDriverManager")
        mocker.patch("cluspro.browser.load_config", return_value=mock_config)

        from cluspro.browser import create_browser

        _driver = create_browser(headless=True, config=mock_config)

        mock_webdriver.Firefox.assert_called_once()

    def test_create_browser_with_download_dir(self, mocker, mock_config, tmp_path):
        """Test browser creation with download directory."""
        mocker.patch("cluspro.browser.webdriver")
        mocker.patch("cluspro.browser.GeckoDriverManager")
        mocker.patch("cluspro.browser.load_config", return_value=mock_config)

        from cluspro.browser import create_browser

        _driver = create_browser(download_dir=str(tmp_path), config=mock_config)

        assert tmp_path.exists()


class TestBrowserSession:
    """Tests for browser_session context manager."""

    def test_browser_session_cleanup(self, mocker, mock_config):
        """Test that browser is cleaned up after session."""
        mock_driver = MagicMock()
        mocker.patch("cluspro.browser.create_browser", return_value=mock_driver)

        from cluspro.browser import browser_session

        with browser_session(config=mock_config) as driver:
            assert driver is mock_driver

        mock_driver.quit.assert_called_once()

    def test_browser_session_cleanup_on_exception(self, mocker, mock_config):
        """Test browser cleanup even when exception occurs."""
        mock_driver = MagicMock()
        mocker.patch("cluspro.browser.create_browser", return_value=mock_driver)

        from cluspro.browser import browser_session

        with pytest.raises(ValueError):
            with browser_session(config=mock_config) as _driver:
                raise ValueError("Test error")

        mock_driver.quit.assert_called_once()


class TestWaitForElement:
    """Tests for wait_for_element function."""

    def test_returns_webdriverwait(self, mock_driver):
        """Test that wait_for_element returns WebDriverWait."""
        from cluspro.browser import wait_for_element

        wait = wait_for_element(mock_driver, timeout=10)
        assert wait is not None

    def test_custom_timeout(self, mock_driver):
        """Test wait_for_element with custom timeout."""
        from cluspro.browser import wait_for_element

        wait = wait_for_element(mock_driver, timeout=30)
        assert wait is not None


class TestClickGuestLogin:
    """Tests for click_guest_login function."""

    def test_click_guest_login_success(self, mocker, mock_driver, mock_element):
        """Test successful guest login click."""
        mock_wait = MagicMock()
        mock_wait.until = MagicMock(return_value=mock_element)
        mocker.patch("cluspro.browser.wait_for_element", return_value=mock_wait)

        from cluspro.browser import click_guest_login

        click_guest_login(mock_driver)

        mock_element.click.assert_called_once()
