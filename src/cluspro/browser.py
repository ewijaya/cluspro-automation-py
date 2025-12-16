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


def click_guest_login(driver: webdriver.Firefox) -> None:
    """
    Click the guest login link on ClusPro pages.

    This is required on most ClusPro pages before accessing content.

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
