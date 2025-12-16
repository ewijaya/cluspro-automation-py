"""
Results parsing module for ClusPro automation.

Parses the ClusPro results pages to find completed jobs.
"""

import logging
import re
import time
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from cluspro.browser import browser_session, click_guest_login
from cluspro.utils import expand_sequences, group_sequences, load_config

logger = logging.getLogger(__name__)


def get_finished_jobs(
    filter_pattern: Optional[str] = None,
    max_pages: int = 50,
    headless: bool = True,
    config: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Get completed jobs from ClusPro results pages.

    Parses multiple pages of results and filters for finished jobs.

    Args:
        filter_pattern: Regex pattern to filter job names
        max_pages: Maximum number of pages to parse
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        DataFrame with completed jobs:
        - job_name: Job identifier
        - job_id: Numeric job ID
        - status: "finished"
        - submitted: Submission timestamp
        - user: Username

    Example:
        >>> df = get_finished_jobs(filter_pattern="pad-.*", max_pages=10)
        >>> job_ids = group_sequences(df["job_id"].tolist())
        >>> print(f"Finished job IDs: {job_ids}")
    """
    if config is None:
        config = load_config()

    urls = config.get("cluspro", {}).get("urls", {})
    timeouts = config.get("timeouts", {})
    batch_config = config.get("batch", {})

    results_url = urls.get("results", "https://cluspro.org/results.php")
    page_load_wait = timeouts.get("page_load_wait", 3)
    max_pages = min(max_pages, batch_config.get("max_pages_to_parse", 50))

    logger.info(f"Fetching results from up to {max_pages} pages...")

    all_tables = []

    with browser_session(headless=headless, config=config) as driver:
        try:
            # Navigate to results page
            driver.get(results_url)
            logger.debug(f"Navigated to: {results_url}")

            # Click guest login
            click_guest_login(driver)
            time.sleep(page_load_wait)

            for page_num in range(1, max_pages + 1):
                logger.debug(f"Parsing page {page_num}...")

                # Parse current page
                html = driver.page_source
                soup = BeautifulSoup(html, "lxml")

                table = soup.find("table", class_="nice")
                if table:
                    df = parse_results_table(table)
                    if not df.empty:
                        df["page"] = page_num
                        all_tables.append(df)
                        logger.debug(f"  Found {len(df)} entries on page {page_num}")

                # Try to navigate to next page
                try:
                    next_link = driver.find_element(
                        By.XPATH, "//a[contains(text(),'next ->')]"
                    )
                    next_link.click()
                    time.sleep(page_load_wait)
                except NoSuchElementException:
                    logger.debug(f"No more pages after page {page_num}")
                    break

            if not all_tables:
                logger.info("No results found")
                return pd.DataFrame()

            # Combine all pages
            combined = pd.concat(all_tables, ignore_index=True)

            # Standardize column names
            combined.columns = [c.lower().replace(" ", "_") for c in combined.columns]

            # Rename common columns
            if "name" in combined.columns:
                combined = combined.rename(columns={"name": "job_name"})
            if "id" in combined.columns:
                combined = combined.rename(columns={"id": "job_id"})

            # Convert job_id to numeric
            if "job_id" in combined.columns:
                combined["job_id"] = pd.to_numeric(combined["job_id"], errors="coerce")

            # Filter for finished jobs
            if "status" in combined.columns:
                # Exclude error states
                combined = combined[~combined["status"].str.contains("error", case=False, na=False)]
                finished = combined[combined["status"] == "finished"]
            else:
                finished = combined

            # Apply job name filter
            if filter_pattern and "job_name" in finished.columns:
                pattern = re.compile(filter_pattern)
                finished = finished[finished["job_name"].str.match(pattern, na=False)]
                logger.debug(f"Filtered by pattern: {filter_pattern}")

            # Sort by job_id
            if "job_id" in finished.columns:
                finished = finished.sort_values("job_id")

            logger.info(f"Found {len(finished)} finished jobs")
            return finished.reset_index(drop=True)

        except Exception as e:
            logger.error(f"Failed to fetch results: {e}")
            raise


def parse_results_table(table) -> pd.DataFrame:
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
        headers = [f"col_{i}" for i in range(len(rows[0]))]

    if not rows:
        return pd.DataFrame(columns=headers)

    return pd.DataFrame(rows, columns=headers[: len(rows[0])])


def get_job_ids_compressed(
    filter_pattern: Optional[str] = None,
    max_pages: int = 50,
    headless: bool = True,
    config: Optional[dict] = None,
) -> str:
    """
    Get finished job IDs in compressed notation.

    Convenience function that returns job IDs ready for batch download.

    Args:
        filter_pattern: Regex pattern to filter job names
        max_pages: Maximum number of pages to parse
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        Compressed job ID string (e.g., "1154309:1154338,1154340")

    Example:
        >>> job_ids = get_job_ids_compressed(filter_pattern="pad-.*")
        >>> print(job_ids)
        '1154309:1154338,1154340,1154345:1154350'
    """
    df = get_finished_jobs(
        filter_pattern=filter_pattern,
        max_pages=max_pages,
        headless=headless,
        config=config,
    )

    if df.empty or "job_id" not in df.columns:
        return ""

    job_ids = df["job_id"].dropna().astype(int).tolist()
    return group_sequences(job_ids)


def check_job_finished(
    job_id: int,
    headless: bool = True,
    config: Optional[dict] = None,
) -> bool:
    """
    Check if a specific job has finished.

    Args:
        job_id: Job ID to check
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        True if job is finished, False otherwise

    Example:
        >>> if check_job_finished(1154309):
        ...     print("Job is done!")
    """
    df = get_finished_jobs(max_pages=5, headless=headless, config=config)

    if df.empty or "job_id" not in df.columns:
        return False

    return job_id in df["job_id"].values


def get_results_summary(
    filter_pattern: Optional[str] = None,
    max_pages: int = 50,
    headless: bool = True,
    config: Optional[dict] = None,
) -> dict:
    """
    Get summary statistics of results.

    Args:
        filter_pattern: Regex pattern to filter job names
        max_pages: Maximum number of pages to parse
        headless: Run browser in headless mode
        config: Optional configuration dict

    Returns:
        Dict with summary statistics:
        - total: Total number of jobs
        - finished: Number of finished jobs
        - running: Number of running jobs
        - error: Number of failed jobs
        - job_ids: Compressed string of finished job IDs

    Example:
        >>> summary = get_results_summary(filter_pattern="bb-.*")
        >>> print(f"Finished: {summary['finished']}/{summary['total']}")
    """
    if config is None:
        config = load_config()

    urls = config.get("cluspro", {}).get("urls", {})
    timeouts = config.get("timeouts", {})

    results_url = urls.get("results", "https://cluspro.org/results.php")
    page_load_wait = timeouts.get("page_load_wait", 3)

    all_tables = []

    with browser_session(headless=headless, config=config) as driver:
        try:
            driver.get(results_url)
            click_guest_login(driver)
            time.sleep(page_load_wait)

            for page_num in range(1, max_pages + 1):
                html = driver.page_source
                soup = BeautifulSoup(html, "lxml")
                table = soup.find("table", class_="nice")

                if table:
                    df = parse_results_table(table)
                    if not df.empty:
                        all_tables.append(df)

                try:
                    next_link = driver.find_element(
                        By.XPATH, "//a[contains(text(),'next ->')]"
                    )
                    next_link.click()
                    time.sleep(page_load_wait)
                except NoSuchElementException:
                    break

            if not all_tables:
                return {
                    "total": 0,
                    "finished": 0,
                    "running": 0,
                    "error": 0,
                    "job_ids": "",
                }

            combined = pd.concat(all_tables, ignore_index=True)
            combined.columns = [c.lower().replace(" ", "_") for c in combined.columns]

            if "name" in combined.columns:
                combined = combined.rename(columns={"name": "job_name"})
            if "id" in combined.columns:
                combined = combined.rename(columns={"id": "job_id"})

            # Apply filter
            if filter_pattern and "job_name" in combined.columns:
                pattern = re.compile(filter_pattern)
                combined = combined[combined["job_name"].str.match(pattern, na=False)]

            # Count statuses
            status_counts = {"finished": 0, "running": 0, "error": 0}
            if "status" in combined.columns:
                for status in combined["status"].str.lower():
                    if "finished" in status:
                        status_counts["finished"] += 1
                    elif "running" in status:
                        status_counts["running"] += 1
                    elif "error" in status:
                        status_counts["error"] += 1

            # Get finished job IDs
            finished_ids = ""
            if "job_id" in combined.columns and "status" in combined.columns:
                finished_df = combined[combined["status"] == "finished"]
                if not finished_df.empty:
                    ids = pd.to_numeric(finished_df["job_id"], errors="coerce")
                    ids = ids.dropna().astype(int).tolist()
                    finished_ids = group_sequences(ids)

            return {
                "total": len(combined),
                "finished": status_counts["finished"],
                "running": status_counts["running"],
                "error": status_counts["error"],
                "job_ids": finished_ids,
            }

        except Exception as e:
            logger.error(f"Failed to get results summary: {e}")
            raise
