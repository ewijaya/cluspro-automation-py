"""
Browser management module for ClusPro automation.

Provides unified browser setup with automatic driver management.
No external Selenium server required - uses webdriver-manager.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

from cluspro.utils import load_config
from cluspro.retry import retry_browser
from cluspro.auth import Credentials, AuthenticationError

logger = logging.getLogger(__name__)


def create_browser(
    headless: bool = True,
    download_dir: Optional[str] = None,
    config: Optional[dict] = None,
) -> webdriver.Firefox:
    """
    Create and configure a Firefox browser instance.

    Args:
        headless: Run browser without visible window (default: True)
        download_dir: Directory for downloaded files (auto-downloads without prompt)
        config: Optional configuration dict (loaded from settings.yaml if not provided)

    Returns:
        Configured Firefox WebDriver instance

    Example:
        >>> driver = create_browser(headless=True, download_dir="/tmp/downloads")
        >>> driver.get("https://cluspro.bu.edu")
        >>> driver.quit()
    """
    if config is None:
        config = load_config()

    browser_config = config.get("browser", {})
    download_config = config.get("download", {})

    # Firefox options
    options = FirefoxOptions()

    # Headless mode
    if headless:
        options.add_argument("--headless")
        logger.debug("Browser configured for headless mode")

    # Custom Firefox binary (optional)
    firefox_binary = browser_config.get("firefox_binary")
    if firefox_binary:
        options.binary_location = firefox_binary
        logger.debug(f"Using Firefox binary: {firefox_binary}")

    # Download configuration
    if download_dir:
        download_path = str(Path(download_dir).expanduser().resolve())
        Path(download_path).mkdir(parents=True, exist_ok=True)

        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", download_path)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.useDownloadDir", True)

        # MIME types to auto-download
        mime_types = download_config.get(
            "mime_types",
            [
                "application/x-bzip2",
                "text/csv",
                "text/plain",
                "application/json",
                "application/zip",
            ],
        )
        options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk", ",".join(mime_types)
        )
        logger.debug(f"Download directory set to: {download_path}")

    # Disable notifications and other popups
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("dom.push.enabled", False)

    # Use webdriver-manager to automatically download and manage geckodriver
    logger.info("Initializing Firefox WebDriver...")

    # Check for direct geckodriver path in config (bypasses GitHub API calls)
    geckodriver_path = browser_config.get("geckodriver_path")
    if geckodriver_path:
        geckodriver_path = str(Path(geckodriver_path).expanduser().resolve())
        logger.debug(f"Using geckodriver from config: {geckodriver_path}")
        service = FirefoxService(geckodriver_path)
    else:
        service = FirefoxService(GeckoDriverManager().install())

    driver = webdriver.Firefox(service=service, options=options)

    # Configure timeouts
    implicit_wait = browser_config.get("implicit_wait", 10)
    page_load_timeout = browser_config.get("page_load_timeout", 30)

    driver.implicitly_wait(implicit_wait)
    driver.set_page_load_timeout(page_load_timeout)

    logger.info("Firefox WebDriver initialized successfully")
    return driver


@contextmanager
def browser_session(
    headless: bool = True,
    download_dir: Optional[str] = None,
    config: Optional[dict] = None,
):
    """
    Context manager for browser sessions with automatic cleanup.

    Ensures the browser is properly closed even if exceptions occur.

    Args:
        headless: Run browser without visible window
        download_dir: Directory for downloaded files
        config: Optional configuration dict

    Yields:
        Configured Firefox WebDriver instance

    Example:
        >>> with browser_session(download_dir="/tmp") as driver:
        ...     driver.get("https://cluspro.bu.edu")
        ...     # Browser automatically closed after this block
    """
    driver = create_browser(
        headless=headless, download_dir=download_dir, config=config
    )
    try:
        yield driver
    finally:
        logger.debug("Closing browser session")
        driver.quit()


def wait_for_element(driver: webdriver.Firefox, timeout: int = 10):
    """
    Create a WebDriverWait instance for explicit waits.

    Args:
        driver: WebDriver instance
        timeout: Maximum wait time in seconds

    Returns:
        WebDriverWait instance

    Example:
        >>> from selenium.webdriver.common.by import By
        >>> from selenium.webdriver.support import expected_conditions as EC
        >>> wait = wait_for_element(driver, timeout=15)
        >>> element = wait.until(EC.presence_of_element_located((By.ID, "myid")))
    """
    return WebDriverWait(driver, timeout)


@retry_browser
def click_guest_login(driver: webdriver.Firefox) -> None:
    """
    Click the guest login link on ClusPro pages.

    This is required on most ClusPro pages before accessing content.
    Automatically retries on transient Selenium failures.

    Args:
        driver: WebDriver instance on a ClusPro page
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    wait = wait_for_element(driver, timeout=15)
    guest_link = wait.until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "Use the server without the benefits of your own account")
        )
    )
    guest_link.click()
    logger.debug("Clicked guest login link")


@retry_browser
def perform_login(driver: webdriver.Firefox, credentials: Credentials) -> None:
    """
    Perform account login on ClusPro login page.

    Fills in the login form with username/password and submits.
    Verifies successful login by checking redirect to /home.php.

    Args:
        driver: WebDriver instance (should be on login.php or will navigate there)
        credentials: Credentials object with username and password

    Raises:
        AuthenticationError: If login fails (invalid credentials, page error)

    Example:
        >>> from cluspro.auth import Credentials, CredentialSource
        >>> creds = Credentials("user", "pass", CredentialSource.ENVIRONMENT)
        >>> perform_login(driver, creds)
    """
    import time

    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC

    login_url = "https://cluspro.bu.edu/login.php"

    # Navigate to login page if not already there
    if "login.php" not in driver.current_url:
        driver.get(login_url)
        logger.debug(f"Navigated to login page: {login_url}")

    wait = wait_for_element(driver, timeout=15)

    # Fill username
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    username_field.clear()
    username_field.send_keys(credentials.username)

    # Fill password
    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(credentials.password)

    # Click login button
    login_button = driver.find_element(
        By.XPATH, "//input[@name='action'][@value='Login']"
    )
    login_button.click()
    logger.debug("Submitted login form")

    # Wait for page to load
    time.sleep(2)

    # Check for login error on page
    try:
        error_elem = driver.find_element(By.CLASS_NAME, "error")
        error_text = error_elem.text
        raise AuthenticationError(f"Login failed: {error_text}")
    except NoSuchElementException:
        pass  # No error element, continue

    # Verify redirect to home.php (successful login)
    if "/home.php" not in driver.current_url and "/login.php" in driver.current_url:
        raise AuthenticationError(
            f"Login may have failed. Expected redirect to /home.php, "
            f"but still on {driver.current_url}"
        )

    logger.info(f"Logged in as: {credentials.username}")


def authenticate(
    driver: webdriver.Firefox,
    credentials: Optional[Credentials] = None,
    force_guest: bool = False,
) -> None:
    """
    Authenticate to ClusPro using appropriate method.

    Routes to either guest login or account login based on parameters.

    Args:
        driver: WebDriver instance on a ClusPro page
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Behavior:
        - If force_guest=True: Always use guest login
        - If credentials=None: Use guest login
        - Otherwise: Use account login with provided credentials

    Example:
        >>> # Auto-select based on credentials
        >>> authenticate(driver, credentials=my_creds)
        >>> # Force guest mode
        >>> authenticate(driver, credentials=my_creds, force_guest=True)
    """
    if force_guest:
        logger.debug("Using guest login (forced)")
        click_guest_login(driver)
    elif credentials is None:
        logger.debug("Using guest login (no credentials)")
        click_guest_login(driver)
    else:
        logger.debug(f"Using account login (source: {credentials.source.value})")
        perform_login(driver, credentials)
