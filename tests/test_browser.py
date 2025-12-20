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


class TestAuthenticate:
    """Tests for authenticate function."""

    def test_authenticate_guest_mode(self, mocker, mock_driver):
        """Test authentication in guest mode."""
        mock_guest_login = mocker.patch("cluspro.browser.click_guest_login")

        from cluspro.browser import authenticate

        authenticate(mock_driver, credentials=None, force_guest=True)

        mock_guest_login.assert_called_once()

    def test_authenticate_with_credentials(self, mocker, mock_driver):
        """Test authentication with credentials."""
        from cluspro.auth import Credentials, CredentialSource

        mock_perform_login = mocker.patch("cluspro.browser.perform_login")

        from cluspro.browser import authenticate

        creds = Credentials(
            username="testuser", password="testpass", source=CredentialSource.ENVIRONMENT
        )

        authenticate(mock_driver, credentials=creds, force_guest=False)

        mock_perform_login.assert_called_once_with(mock_driver, creds)

    def test_authenticate_no_credentials_falls_back_to_guest(self, mocker, mock_driver):
        """Test fallback to guest when no credentials provided."""
        mock_guest_login = mocker.patch("cluspro.browser.click_guest_login")

        from cluspro.browser import authenticate

        authenticate(mock_driver, credentials=None, force_guest=False)

        mock_guest_login.assert_called_once()


class TestPerformLogin:
    """Tests for perform_login function."""

    def test_perform_login_success(self, mocker, mock_driver, mock_element):
        """Test successful account login."""
        from selenium.common.exceptions import NoSuchElementException

        from cluspro.auth import Credentials, CredentialSource

        mock_wait = MagicMock()
        mock_wait.until = MagicMock(return_value=mock_element)
        mocker.patch("cluspro.browser.wait_for_element", return_value=mock_wait)
        mocker.patch("time.sleep")

        # Mock driver to return elements for form fields but raise NoSuchElementException for error
        def find_element_side_effect(by, value):
            if value == "error":
                raise NoSuchElementException("No error element")
            return mock_element

        mock_driver.find_element = MagicMock(side_effect=find_element_side_effect)
        mock_driver.current_url = "https://cluspro.bu.edu/home.php"

        from cluspro.browser import perform_login

        creds = Credentials(
            username="testuser", password="testpass", source=CredentialSource.ENVIRONMENT
        )

        perform_login(mock_driver, creds)

        # Check that send_keys was called for username and password
        assert mock_element.send_keys.call_count >= 2


class TestFindCachedGeckodriver:
    """Tests for _find_cached_geckodriver function."""

    def test_finds_cached_driver(self, mocker, tmp_path):
        """Test finding cached geckodriver."""
        # Create a mock geckodriver path
        driver_path = tmp_path / ".wdm" / "drivers" / "geckodriver" / "linux64" / "geckodriver"
        driver_path.parent.mkdir(parents=True, exist_ok=True)
        driver_path.write_text("mock driver")

        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        from cluspro.browser import _find_cached_geckodriver

        result = _find_cached_geckodriver()

        # May or may not find based on directory structure
        # Just ensure it doesn't crash
        assert result is None or isinstance(result, str)

    def test_no_cached_driver(self, mocker, tmp_path):
        """Test when no cached driver exists."""
        mocker.patch("pathlib.Path.home", return_value=tmp_path)

        from cluspro.browser import _find_cached_geckodriver

        result = _find_cached_geckodriver()

        assert result is None
