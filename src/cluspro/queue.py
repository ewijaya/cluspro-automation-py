"""
Queue monitoring module for ClusPro automation.

Parses the ClusPro job queue to check status of submitted jobs.
"""

import logging
import re
import time
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from cluspro.browser import browser_session, click_guest_login
from cluspro.utils import load_config

logger = logging.getLogger(__name__)


def get_queue_status(
    filter_user: Optional[str] = None,
    filter_pattern: Optional[str] = None,
    headless: bool = True,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Get current ClusPro job queue status.

    Args:
        filter_user: Filter by username (exact match)
        filter_pattern: Filter job names by regex pattern
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        DataFrame with queue entries:
        - job_name: Job identifier
        - job_id: Numeric job ID
        - user: Username who submitted
        - status: Current status (waiting, running, etc.)
        - submitted: Submission timestamp

    Example:
        >>> df = get_queue_status(filter_user="piper", filter_pattern="bb-.*")
        >>> print(df[["job_name", "status"]])
    """
    if config is None:
        config = load_config()

    urls = config.get("cluspro", {}).get("urls", {})
    timeouts = config.get("timeouts", {})

    queue_url = urls.get("queue", "https://cluspro.org/queue.php")
    page_load_wait = timeouts.get("page_load_wait", 3)

    logger.info("Fetching ClusPro queue status...")

    with browser_session(headless=headless, config=config) as driver:
        try:
            # Navigate to queue page
            driver.get(queue_url)
            logger.debug(f"Navigated to: {queue_url}")

            # Click guest login
            click_guest_login(driver)
            time.sleep(page_load_wait)

            # Parse page source
            html = driver.page_source
            soup = BeautifulSoup(html, "lxml")

            # Find the queue table
            table = soup.find("table", class_="nice")

            if table is None:
                logger.warning("Queue table not found on page")
                return pd.DataFrame()

            # Parse table to DataFrame
            df = parse_html_table(table)

            if df.empty:
                logger.info("Queue is empty")
                return df

            # Standardize column names
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]

            # Rename common columns
            if "name" in df.columns:
                df = df.rename(columns={"name": "job_name"})
            if "id" in df.columns:
                df = df.rename(columns={"id": "job_id"})

            # Convert job_id to numeric if present
            if "job_id" in df.columns:
                df["job_id"] = pd.to_numeric(df["job_id"], errors="coerce")

            # Apply filters
            if filter_user and "user" in df.columns:
                df = df[df["user"] == filter_user]
                logger.debug(f"Filtered to user: {filter_user}")

            if filter_pattern and "job_name" in df.columns:
                pattern = re.compile(filter_pattern)
                df = df[df["job_name"].str.match(pattern, na=False)]
                logger.debug(f"Filtered by pattern: {filter_pattern}")

            logger.info(f"Found {len(df)} jobs in queue")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch queue status: {e}")
            raise


def parse_html_table(table) -> pd.DataFrame:
    """
    Parse BeautifulSoup table element to DataFrame.

    Args:
        table: BeautifulSoup table element

    Returns:
        DataFrame with table contents
    """
    # Get headers
    headers = []
    header_row = table.find("tr")
    if header_row:
        headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

    # Get data rows
    rows = []
    for tr in table.find_all("tr")[1:]:  # Skip header row
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    if not headers and rows:
        # Generate generic headers if none found
        headers = [f"col_{i}" for i in range(len(rows[0]))]

    if not rows:
        return pd.DataFrame(columns=headers)

    return pd.DataFrame(rows, columns=headers[: len(rows[0])])


def check_job_in_queue(
    job_name: str,
    headless: bool = True,
    config: Optional[dict] = None,
) -> Optional[dict]:
    """
    Check if a specific job is in the queue.

    Args:
        job_name: Job name to search for
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        Dict with job info if found, None otherwise

    Example:
        >>> job = check_job_in_queue("my-job-123")
        >>> if job:
        ...     print(f"Job status: {job['status']}")
    """
    df = get_queue_status(headless=headless, config=config)

    if df.empty or "job_name" not in df.columns:
        return None

    matches = df[df["job_name"] == job_name]

    if matches.empty:
        return None

    return matches.iloc[0].to_dict()


def wait_for_queue_clear(
    filter_user: Optional[str] = None,
    filter_pattern: Optional[str] = None,
    check_interval: int = 60,
    max_wait: int = 3600,
    headless: bool = True,
    config: Optional[dict] = None,
) -> bool:
    """
    Wait until filtered queue is empty.

    Useful for waiting until all submitted jobs have started processing.

    Args:
        filter_user: Filter by username
        filter_pattern: Filter by job name pattern
        check_interval: Seconds between checks
        max_wait: Maximum wait time in seconds
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        True if queue cleared, False if timeout

    Example:
        >>> # Wait up to 1 hour for all "bb-" jobs to start
        >>> cleared = wait_for_queue_clear(filter_pattern="bb-.*", max_wait=3600)
    """
    import time

    start_time = time.time()

    while time.time() - start_time < max_wait:
        df = get_queue_status(
            filter_user=filter_user,
            filter_pattern=filter_pattern,
            headless=headless,
            config=config,
        )

        if df.empty:
            logger.info("Queue is now empty")
            return True

        logger.info(f"{len(df)} jobs still in queue, waiting {check_interval}s...")
        time.sleep(check_interval)

    logger.warning(f"Timeout after {max_wait}s, {len(df)} jobs still in queue")
    return False
