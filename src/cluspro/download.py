"""
Download module for ClusPro automation.

Downloads PDB models and energy scores from ClusPro job results.
"""

import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm

from cluspro.auth import Credentials
from cluspro.browser import authenticate, browser_session, wait_for_element
from cluspro.retry import retry_download, with_retry
from cluspro.utils import ensure_dir, expand_sequences, load_config

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Exception raised when download fails."""

    pass


@retry_download
def _download_pdb_models(driver, wait, download_wait: int) -> None:
    """
    Download PDB models with retry on transient failures.

    Args:
        driver: WebDriver instance
        wait: WebDriverWait instance
        download_wait: Time to wait for download to complete
    """
    download_link = wait.until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "Download all Models for all Coefficients")
        )
    )
    download_link.click()
    logger.debug("Clicked download models link")
    time.sleep(download_wait)


@retry_download
def _download_scores(driver, wait) -> None:
    """
    Download model scores with retry on transient failures.

    Args:
        driver: WebDriver instance
        wait: WebDriverWait instance
    """
    scores_link = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "View Model Scores"))
    )
    scores_link.click()
    time.sleep(2)

    download_scores_link = wait.until(
        EC.element_to_be_clickable(
            (By.LINK_TEXT, "Download Model Scores for this Coefficient")
        )
    )
    download_scores_link.click()
    logger.debug("Clicked download scores link")
    time.sleep(5)


def download_results(
    job_id: int,
    output_dir: str | Path | None = None,
    download_pdb: bool = True,
    headless: bool = True,
    config: dict[str, Any] | None = None,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> Path:
    """
    Download results for a single ClusPro job.

    Args:
        job_id: ClusPro job ID
        output_dir: Directory to save results (default from config)
        download_pdb: Whether to download PDB model files
        headless: Run browser in headless mode
        config: Optional configuration dict
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        Path to the job results directory

    Raises:
        DownloadError: If download fails

    Example:
        >>> result_dir = download_results(1154309, download_pdb=True)
        >>> print(f"Results saved to: {result_dir}")
    """
    if config is None:
        config = load_config()

    urls = config.get("cluspro", {}).get("urls", {})
    paths = config.get("paths", {})
    timeouts = config.get("timeouts", {})

    models_url = urls.get("models", "https://cluspro.bu.edu/models.php")
    job_url = f"{models_url}?job={job_id}"

    if output_dir is None:
        output_dir = paths.get("output_dir", "~/Desktop/ClusPro_results")

    output_path = ensure_dir(output_dir)
    download_wait = timeouts.get("download_wait", 10)

    logger.info(f"Downloading results for job {job_id}...")

    with browser_session(
        headless=headless, download_dir=str(output_path), config=config
    ) as driver:
        try:
            # Navigate to job results page
            driver.get(job_url)
            logger.debug(f"Navigated to: {job_url}")

            # Authenticate (guest or account login)
            authenticate(driver, credentials=credentials, force_guest=force_guest)
            time.sleep(2)

            wait = wait_for_element(driver, timeout=15)

            # Extract job name from page
            try:
                job_header = driver.find_element(
                    By.XPATH, "//div[@id='main-header-right']//following-sibling::h3"
                )
                job_name = job_header.text.replace("Job Details: ", "").strip()
                logger.debug(f"Job name: {job_name}")
            except NoSuchElementException:
                job_name = f"cluspro.{job_id}"
                logger.warning(f"Could not extract job name, using: {job_name}")

            # Create job-specific output directory
            job_output_dir: Path = output_path / job_name
            job_output_dir.mkdir(parents=True, exist_ok=True)

            # Download PDB models if requested (with automatic retry)
            if download_pdb:
                try:
                    _download_pdb_models(driver, wait, download_wait)
                    extract_archive(output_path, job_output_dir)
                except NoSuchElementException:
                    logger.warning("Download models link not found, skipping PDB download")

            # Download model scores (with automatic retry)
            try:
                _download_scores(driver, wait)
                move_score_file(output_path, job_output_dir)
            except NoSuchElementException:
                logger.warning("Model scores link not found")

            logger.info(f"Results for job {job_id} saved to: {job_output_dir}")
            return job_output_dir

        except Exception as e:
            logger.error(f"Failed to download results for job {job_id}: {e}")
            raise DownloadError(f"Failed to download job {job_id}: {e}") from e


@with_retry(max_attempts=3, min_wait=2, exceptions=(OSError, IOError, subprocess.CalledProcessError))
def extract_archive(download_dir: Path, output_dir: Path) -> None:
    """
    Extract downloaded tar.bz2 archive.

    Automatically retries on transient I/O failures.

    Args:
        download_dir: Directory where archive was downloaded
        output_dir: Directory to extract files to
    """
    # Find tar.bz2 file
    archives = list(download_dir.glob("*.tar.bz2"))

    if not archives:
        logger.warning("No tar.bz2 archive found to extract")
        return

    archive_path = archives[0]
    logger.debug(f"Extracting archive: {archive_path}")

    try:
        # Extract using tar command
        subprocess.run(
            ["tar", "-xvjf", str(archive_path), "-C", str(download_dir)],
            check=True,
            capture_output=True,
        )

        # Find extracted directory (usually named cluspro.JOBID)
        extracted_dirs = [
            d
            for d in download_dir.iterdir()
            if d.is_dir() and d.name.startswith("cluspro.")
        ]

        if extracted_dirs:
            extracted_dir = extracted_dirs[0]
            # Move contents to output directory
            for item in extracted_dir.iterdir():
                dest = output_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))

            # Remove empty extracted directory
            extracted_dir.rmdir()
            logger.debug(f"Extracted contents to: {output_dir}")

        # Remove archive file
        archive_path.unlink()
        logger.debug(f"Removed archive: {archive_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to extract archive: {e}")
    except Exception as e:
        logger.error(f"Error during extraction: {e}")


def move_score_file(download_dir: Path, output_dir: Path) -> None:
    """
    Move and rename downloaded score CSV file.

    Args:
        download_dir: Directory where CSV was downloaded
        output_dir: Directory to move file to
    """
    # Find CSV files
    csv_files = list(download_dir.glob("*.csv"))

    if not csv_files:
        logger.warning("No CSV file found to move")
        return

    csv_path = csv_files[0]

    # Rename with .balanced.csv suffix
    base_name = csv_path.stem
    new_name = f"{base_name}.balanced.csv"
    dest_path = output_dir / new_name

    shutil.move(str(csv_path), str(dest_path))
    logger.debug(f"Moved score file to: {dest_path}")


def download_batch(
    job_ids: str | list[int],
    output_dir: str | Path | None = None,
    download_pdb: bool = True,
    continue_on_error: bool = True,
    headless: bool = True,
    config: dict[str, Any] | None = None,
    progress: bool = True,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> dict[int, dict[str, str]]:
    """
    Download results for multiple jobs.

    Args:
        job_ids: List of job IDs or compressed string (e.g., "1154309:1154338")
        output_dir: Directory to save results
        download_pdb: Whether to download PDB files
        continue_on_error: Continue with next job if one fails
        headless: Run browser in headless mode
        config: Optional configuration dict
        progress: Show progress bar
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        Dict mapping job_id to result (path or error message)

    Example:
        >>> results = download_batch("1154309:1154320", download_pdb=True)
        >>> for job_id, result in results.items():
        ...     print(f"Job {job_id}: {result}")
    """
    if config is None:
        config = load_config()

    # Parse job IDs if string
    if isinstance(job_ids, str):
        job_ids = expand_sequences(job_ids)

    if not job_ids:
        logger.warning("No job IDs provided")
        return {}

    timeouts = config.get("timeouts", {})
    between_jobs = timeouts.get("between_jobs", 10)

    results = {}
    job_iter = job_ids

    if progress:
        job_iter = tqdm(job_ids, desc="Downloading jobs", unit="job")

    for job_id in job_iter:
        try:
            result_path = download_results(
                job_id=job_id,
                output_dir=output_dir,
                download_pdb=download_pdb,
                headless=headless,
                config=config,
                credentials=credentials,
                force_guest=force_guest,
            )
            results[job_id] = {"status": "success", "path": str(result_path)}

        except Exception as e:
            logger.error(f"Failed to download job {job_id}: {e}")
            results[job_id] = {"status": "error", "error": str(e)}

            if not continue_on_error:
                raise

        # Delay between downloads
        time.sleep(between_jobs)

    # Summary
    success = sum(1 for r in results.values() if r["status"] == "success")
    failed = len(results) - success
    logger.info(f"Download complete: {success} successful, {failed} failed")

    return results


def get_job_name_from_page(
    job_id: int,
    headless: bool = True,
    config: dict[str, Any] | None = None,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> str | None:
    """
    Get job name from ClusPro job page.

    Args:
        job_id: ClusPro job ID
        headless: Run browser in headless mode
        config: Optional configuration dict
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        Job name or None if not found

    Example:
        >>> name = get_job_name_from_page(1154309)
        >>> print(f"Job name: {name}")
    """
    if config is None:
        config = load_config()

    urls = config.get("cluspro", {}).get("urls", {})
    models_url = urls.get("models", "https://cluspro.bu.edu/models.php")
    job_url = f"{models_url}?job={job_id}"

    with browser_session(headless=headless, config=config) as driver:
        try:
            driver.get(job_url)
            authenticate(driver, credentials=credentials, force_guest=force_guest)
            time.sleep(2)

            job_header = driver.find_element(
                By.XPATH, "//div[@id='main-header-right']//following-sibling::h3"
            )
            job_name: str = job_header.text.replace("Job Details: ", "").strip()
            return job_name

        except Exception as e:
            logger.error(f"Failed to get job name for {job_id}: {e}")
            return None
