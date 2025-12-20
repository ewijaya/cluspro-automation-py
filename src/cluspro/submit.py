"""
Job submission module for ClusPro automation.

Handles submitting protein docking jobs to the ClusPro web server.
"""

import logging
import time
from pathlib import Path

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm

from cluspro.auth import Credentials
from cluspro.browser import authenticate, browser_session, wait_for_element
from cluspro.retry import retry_browser
from cluspro.utils import load_config, validate_pdb_file

logger = logging.getLogger(__name__)


class SubmissionError(Exception):
    """Exception raised when job submission fails."""

    pass


def _scroll_and_click(driver, element) -> None:
    """Scroll element into view and click it."""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.3)
    element.click()


@retry_browser
def _fill_and_submit_form(
    driver,
    wait,
    job_name: str,
    receptor_path: Path,
    ligand_path: Path,
    server: str,
) -> None:
    """
    Fill and submit the ClusPro job form.

    This helper is wrapped with retry to handle transient Selenium failures.
    Handles both guest and logged-in user forms.
    """
    # Fill job name
    job_name_input = wait.until(EC.presence_of_element_located((By.NAME, "jobname")))
    job_name_input.clear()
    job_name_input.send_keys(job_name)
    logger.debug(f"Entered job name: {job_name}")

    # Select server type
    server_select = driver.find_element(By.NAME, "server")
    server_select.send_keys(server)
    logger.debug(f"Selected server: {server}")

    # Upload receptor PDB
    show_rec_button = driver.find_element(By.ID, "showrecfile")
    _scroll_and_click(driver, show_rec_button)
    time.sleep(0.5)

    receptor_input = driver.find_element(By.ID, "rec")
    receptor_input.send_keys(str(receptor_path))
    logger.debug("Uploaded receptor PDB")

    # Upload ligand PDB
    show_lig_button = driver.find_element(By.ID, "showligfile")
    _scroll_and_click(driver, show_lig_button)
    time.sleep(0.5)

    ligand_input = driver.find_element(By.ID, "lig")
    ligand_input.send_keys(str(ligand_path))
    logger.debug("Uploaded ligand PDB")

    # Check non-commercial agreement (only present for guest users)
    try:
        agree_checkbox = driver.find_element(By.NAME, "noncommercial")
        if not agree_checkbox.is_selected():
            _scroll_and_click(driver, agree_checkbox)
        logger.debug("Checked non-commercial agreement")
    except Exception:
        # Logged-in users don't have this checkbox
        logger.debug("No non-commercial checkbox (logged-in user)")

    # Submit job
    submit_button = driver.find_element(By.NAME, "action")
    _scroll_and_click(driver, submit_button)
    logger.debug("Clicked submit button")


def submit_job(
    job_name: str,
    receptor_pdb: str | Path,
    ligand_pdb: str | Path,
    server: str = "gpu",
    headless: bool = True,
    config: dict | None = None,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> str | None:
    """
    Submit a single docking job to ClusPro.

    Args:
        job_name: Unique name for the job
        receptor_pdb: Path to receptor PDB file
        ligand_pdb: Path to ligand PDB file
        server: Server type ("gpu" or "cpu", default: "gpu")
        headless: Run browser in headless mode
        config: Optional configuration dict
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        Job ID if captured (may be None as ClusPro doesn't always return it)

    Raises:
        FileNotFoundError: If PDB files don't exist
        SubmissionError: If submission fails

    Example:
        >>> submit_job(
        ...     job_name="test-dock-1",
        ...     receptor_pdb="/path/to/receptor.pdb",
        ...     ligand_pdb="/path/to/ligand.pdb"
        ... )
    """
    if config is None:
        config = load_config()

    # Validate input files
    receptor_path = validate_pdb_file(receptor_pdb)
    ligand_path = validate_pdb_file(ligand_pdb)

    urls = config.get("cluspro", {}).get("urls", {})
    timeouts = config.get("timeouts", {})

    home_url = urls.get("home", "https://cluspro.bu.edu/home.php")
    submission_wait = timeouts.get("submission_wait", 10)

    logger.info(f"Submitting job: {job_name}")
    logger.debug(f"  Receptor: {receptor_path}")
    logger.debug(f"  Ligand: {ligand_path}")

    with browser_session(headless=headless, config=config) as driver:
        try:
            # Navigate to ClusPro home page
            driver.get(home_url)
            logger.debug(f"Navigated to: {home_url}")

            # Authenticate (guest or account login)
            authenticate(driver, credentials=credentials, force_guest=force_guest)
            time.sleep(1)

            wait = wait_for_element(driver, timeout=15)

            # Fill and submit form (with automatic retry)
            _fill_and_submit_form(
                driver=driver,
                wait=wait,
                job_name=job_name,
                receptor_path=receptor_path,
                ligand_path=ligand_path,
                server=server,
            )

            # Wait for submission to complete
            time.sleep(submission_wait)

            # Try to capture job ID from resulting page (optional)
            job_id = None
            try:
                # ClusPro may redirect to a confirmation page with job ID
                current_url = driver.current_url
                if "job=" in current_url:
                    job_id = current_url.split("job=")[-1].split("&")[0]
                    logger.info(f"Captured job ID: {job_id}")
            except Exception:
                logger.debug("Could not capture job ID from URL")

            logger.info(f"Job '{job_name}' submitted successfully")
            return job_id

        except Exception as e:
            logger.error(f"Failed to submit job '{job_name}': {e}")
            raise SubmissionError(f"Failed to submit job '{job_name}': {e}") from e


def submit_batch(
    jobs: pd.DataFrame | list[dict],
    headless: bool = True,
    continue_on_error: bool = True,
    config: dict | None = None,
    progress: bool = True,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> pd.DataFrame:
    """
    Submit multiple docking jobs to ClusPro.

    Args:
        jobs: DataFrame or list of dicts with columns:
              - job_name: Unique job identifier
              - receptor_pdb: Path to receptor PDB
              - ligand_pdb: Path to ligand PDB
              - server: (optional) Server type, default "gpu"
        headless: Run browser in headless mode
        continue_on_error: Continue with next job if one fails
        config: Optional configuration dict
        progress: Show progress bar
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        DataFrame with job submission results:
        - job_name: Original job name
        - job_id: Captured job ID (may be None)
        - status: "success" or "error"
        - error: Error message if failed

    Example:
        >>> jobs = pd.DataFrame({
        ...     "job_name": ["job1", "job2"],
        ...     "receptor_pdb": ["/path/to/rec1.pdb", "/path/to/rec2.pdb"],
        ...     "ligand_pdb": ["/path/to/lig1.pdb", "/path/to/lig2.pdb"]
        ... })
        >>> results = submit_batch(jobs)
    """
    if config is None:
        config = load_config()

    timeouts = config.get("timeouts", {})
    between_jobs = timeouts.get("between_jobs", 10)

    # Convert to DataFrame if list
    if isinstance(jobs, list):
        jobs = pd.DataFrame(jobs)

    # Validate required columns
    required_cols = {"job_name", "receptor_pdb", "ligand_pdb"}
    missing = required_cols - set(jobs.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    results = []
    job_iter = jobs.iterrows()

    if progress:
        job_iter = tqdm(list(job_iter), desc="Submitting jobs", unit="job")

    for idx, row in job_iter:
        job_name = row["job_name"]
        receptor_pdb = row["receptor_pdb"]
        ligand_pdb = row["ligand_pdb"]
        server = row.get("server", "gpu")

        result = {
            "job_name": job_name,
            "job_id": None,
            "status": "pending",
            "error": None,
        }

        try:
            job_id = submit_job(
                job_name=job_name,
                receptor_pdb=receptor_pdb,
                ligand_pdb=ligand_pdb,
                server=server,
                headless=headless,
                config=config,
                credentials=credentials,
                force_guest=force_guest,
            )
            result["job_id"] = job_id
            result["status"] = "success"

        except Exception as e:
            logger.error(f"Failed to submit job '{job_name}': {e}")
            result["status"] = "error"
            result["error"] = str(e)

            if not continue_on_error:
                results.append(result)
                raise

        results.append(result)

        # Delay between jobs
        if idx < len(jobs) - 1:
            time.sleep(between_jobs)

    return pd.DataFrame(results)


def submit_from_csv(
    csv_path: str | Path,
    headless: bool = True,
    continue_on_error: bool = True,
    config: dict | None = None,
    credentials: Credentials | None = None,
    force_guest: bool = False,
) -> pd.DataFrame:
    """
    Submit jobs from a CSV file.

    CSV must have columns: job_name, receptor_pdb, ligand_pdb
    Optional column: server

    Args:
        csv_path: Path to CSV file
        headless: Run browser in headless mode
        continue_on_error: Continue with next job if one fails
        config: Optional configuration dict
        credentials: Optional credentials for account login
        force_guest: Force guest mode even if credentials provided

    Returns:
        DataFrame with job submission results

    Example:
        >>> results = submit_from_csv("/path/to/jobs.csv")
    """
    csv_path = Path(csv_path).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    jobs = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(jobs)} jobs from {csv_path}")

    return submit_batch(
        jobs=jobs,
        headless=headless,
        continue_on_error=continue_on_error,
        config=config,
        credentials=credentials,
        force_guest=force_guest,
    )


def dry_run(jobs: pd.DataFrame | list[dict], output: bool = True) -> pd.DataFrame:
    """
    Preview jobs without submitting.

    Validates files and prints job details.

    Args:
        jobs: DataFrame or list of job specifications
        output: Print job details to console

    Returns:
        DataFrame with validation results

    Example:
        >>> jobs = [{"job_name": "test", "receptor_pdb": "r.pdb", "ligand_pdb": "l.pdb"}]
        >>> dry_run(jobs)
    """
    if isinstance(jobs, list):
        jobs = pd.DataFrame(jobs)

    results = []

    for idx, row in jobs.iterrows():
        job_name = row["job_name"]
        receptor_pdb = row["receptor_pdb"]
        ligand_pdb = row["ligand_pdb"]

        result = {
            "job_name": job_name,
            "receptor_pdb": receptor_pdb,
            "ligand_pdb": ligand_pdb,
            "receptor_exists": Path(receptor_pdb).expanduser().exists(),
            "ligand_exists": Path(ligand_pdb).expanduser().exists(),
            "valid": True,
        }

        result["valid"] = result["receptor_exists"] and result["ligand_exists"]

        if output:
            status = "OK" if result["valid"] else "MISSING FILES"
            print(f"[{status}] {job_name}")
            if not result["receptor_exists"]:
                print(f"  ! Receptor not found: {receptor_pdb}")
            if not result["ligand_exists"]:
                print(f"  ! Ligand not found: {ligand_pdb}")

        results.append(result)

    return pd.DataFrame(results)
