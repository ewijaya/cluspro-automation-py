"""Tests for submit module."""

from unittest.mock import MagicMock

import pandas as pd
import pytest


class TestSubmitJob:
    """Tests for submit_job function."""

    def test_submit_job_validates_files(self, mocker, mock_config, temp_pdb_files):
        """Test that submit_job validates PDB files exist."""
        mocker.patch("cluspro.submit.load_config", return_value=mock_config)

        from cluspro.submit import submit_job

        # Mock browser session
        mock_driver = MagicMock()
        mock_driver.current_url = "https://cluspro.bu.edu/models.php?job=12345"

        mock_session = mocker.patch("cluspro.submit.browser_session")
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock wait and click_guest_login
        mock_wait = MagicMock()
        mock_element = MagicMock()
        mock_wait.until = MagicMock(return_value=mock_element)
        mocker.patch("cluspro.submit.wait_for_element", return_value=mock_wait)
        mocker.patch("cluspro.submit.authenticate")
        mocker.patch("cluspro.submit._fill_and_submit_form")
        mocker.patch("time.sleep")

        # Should not raise since files exist
        _job_id = submit_job(
            job_name="test",
            receptor_pdb=str(temp_pdb_files["receptor"]),
            ligand_pdb=str(temp_pdb_files["ligand"]),
            config=mock_config,
        )

    def test_submit_job_file_not_found(self, mocker, mock_config):
        """Test that submit_job raises error for missing files."""
        mocker.patch("cluspro.submit.load_config", return_value=mock_config)

        from cluspro.submit import submit_job

        with pytest.raises(FileNotFoundError):
            submit_job(
                job_name="test",
                receptor_pdb="/nonexistent/receptor.pdb",
                ligand_pdb="/nonexistent/ligand.pdb",
                config=mock_config,
            )


class TestSubmitBatch:
    """Tests for submit_batch function."""

    def test_submit_batch_validates_columns(self, mocker, mock_config):
        """Test that submit_batch validates required columns."""
        mocker.patch("cluspro.submit.load_config", return_value=mock_config)

        from cluspro.submit import submit_batch

        df = pd.DataFrame({"job_name": ["test"]})  # Missing receptor/ligand

        with pytest.raises(ValueError, match="Missing required columns"):
            submit_batch(df, config=mock_config)

    def test_submit_batch_continues_on_error(self, mocker, mock_config, temp_pdb_files):
        """Test continue_on_error behavior."""
        mocker.patch("cluspro.submit.load_config", return_value=mock_config)
        mocker.patch("cluspro.submit.submit_job", side_effect=Exception("Test error"))
        mocker.patch("time.sleep")

        from cluspro.submit import submit_batch

        jobs = pd.DataFrame(
            {
                "job_name": ["job1", "job2"],
                "receptor_pdb": [str(temp_pdb_files["receptor"])] * 2,
                "ligand_pdb": [str(temp_pdb_files["ligand"])] * 2,
            }
        )

        results = submit_batch(jobs, continue_on_error=True, progress=False, config=mock_config)

        assert len(results) == 2
        assert all(r == "error" for r in results["status"])


class TestDryRun:
    """Tests for dry_run function."""

    def test_dry_run_validates_files(self, temp_pdb_files):
        """Test dry_run validates file existence."""
        from cluspro.submit import dry_run

        jobs = [
            {
                "job_name": "test",
                "receptor_pdb": str(temp_pdb_files["receptor"]),
                "ligand_pdb": str(temp_pdb_files["ligand"]),
            }
        ]

        results = dry_run(jobs, output=False)

        assert len(results) == 1
        assert results.iloc[0]["valid"]  # truthy check for numpy bool

    def test_dry_run_detects_missing_files(self):
        """Test dry_run detects missing files."""
        from cluspro.submit import dry_run

        jobs = [
            {
                "job_name": "test",
                "receptor_pdb": "/nonexistent/receptor.pdb",
                "ligand_pdb": "/nonexistent/ligand.pdb",
            }
        ]

        results = dry_run(jobs, output=False)

        assert not results.iloc[0]["valid"]  # falsy check for numpy bool
        assert not results.iloc[0]["receptor_exists"]
        assert not results.iloc[0]["ligand_exists"]
