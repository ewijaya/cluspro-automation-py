"""Shared pytest fixtures for ClusPro tests."""

from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Standard test configuration."""
    return {
        "credentials": {
            "default_mode": "auto",
        },
        "cluspro": {
            "urls": {
                "home": "https://cluspro.bu.edu/home.php",
                "queue": "https://cluspro.org/queue.php",
                "results": "https://cluspro.org/results.php",
                "models": "https://cluspro.bu.edu/models.php",
            }
        },
        "browser": {
            "type": "firefox",
            "headless": True,
            "implicit_wait": 10,
            "page_load_timeout": 30,
        },
        "paths": {
            "output_dir": "/tmp/cluspro_test",
            "organized_dir": "/tmp/cluspro_test/full_names",
        },
        "timeouts": {
            "submission_wait": 1,
            "page_load_wait": 1,
            "download_wait": 1,
            "between_jobs": 1,
        },
        "batch": {
            "max_pages_to_parse": 5,
            "jobs_per_chunk": 10,
        },
        "retry": {
            "max_attempts": 2,
            "min_wait": 0.1,
            "max_wait": 1,
            "multiplier": 1,
        },
    }


@pytest.fixture
def mock_credentials():
    """Mock credentials for testing."""
    from cluspro.auth import Credentials, CredentialSource

    return Credentials(
        username="testuser",
        password="testpass",
        source=CredentialSource.ENVIRONMENT,
    )


@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver."""
    driver = MagicMock()
    driver.page_source = "<html><body></body></html>"
    driver.current_url = "https://cluspro.bu.edu"
    driver.get = MagicMock()
    driver.quit = MagicMock()
    driver.find_element = MagicMock()
    driver.find_elements = MagicMock(return_value=[])
    driver.implicitly_wait = MagicMock()
    driver.set_page_load_timeout = MagicMock()
    return driver


@pytest.fixture
def mock_browser_session(mocker, mock_driver):
    """Mock browser_session context manager."""
    from contextlib import contextmanager

    @contextmanager
    def _mock_session(*args, **kwargs):
        yield mock_driver

    return mocker.patch("cluspro.browser.browser_session", _mock_session)


@pytest.fixture
def temp_pdb_files(tmp_path):
    """Create temporary PDB files for testing."""
    receptor = tmp_path / "receptor.pdb"
    ligand = tmp_path / "ligand.pdb"

    receptor.write_text(
        "ATOM      1  N   ALA A   1      0.000   0.000   0.000  1.00  0.00           N\n"
    )
    ligand.write_text(
        "ATOM      1  N   GLY B   1      1.000   1.000   1.000  1.00  0.00           N\n"
    )

    return {"receptor": receptor, "ligand": ligand}


@pytest.fixture
def sample_jobs_csv(tmp_path, temp_pdb_files):
    """Create sample jobs CSV file."""
    csv_path = tmp_path / "jobs.csv"
    csv_path.write_text(
        f"job_name,receptor_pdb,ligand_pdb,server\n"
        f"test-job-1,{temp_pdb_files['receptor']},{temp_pdb_files['ligand']},gpu\n"
        f"test-job-2,{temp_pdb_files['receptor']},{temp_pdb_files['ligand']},cpu\n"
    )
    return csv_path


@pytest.fixture
def sample_mapping_csv(tmp_path):
    """Create sample mapping CSV file."""
    csv_path = tmp_path / "mapping.csv"
    csv_path.write_text(
        "job_name,peptide_name,receptor_name\n"
        "test-job-1,peptide1,receptor1\n"
        "test-job-2,peptide2,receptor2\n"
    )
    return csv_path


@pytest.fixture
def test_db(tmp_path):
    """Create test database."""
    from cluspro.database import JobDatabase

    db_path = tmp_path / "test_jobs.db"
    return JobDatabase(db_path=db_path)


@pytest.fixture
def mock_wait():
    """Mock WebDriverWait."""
    wait = MagicMock()
    wait.until = MagicMock(return_value=MagicMock())
    return wait


@pytest.fixture
def mock_element():
    """Mock Selenium WebElement."""
    element = MagicMock()
    element.text = "Test Element"
    element.click = MagicMock()
    element.send_keys = MagicMock()
    element.clear = MagicMock()
    element.is_selected = MagicMock(return_value=False)
    return element
