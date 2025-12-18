"""Tests for download module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDownloadResults:
    """Tests for download_results function."""

    def test_download_creates_output_dir(self, mocker, mock_config, tmp_path):
        """Test that download creates output directory."""
        mock_driver = MagicMock()
        mock_driver.page_source = "<html></html>"
        mock_driver.current_url = "https://cluspro.bu.edu/models.php?job=12345"

        mock_element = MagicMock()
        mock_element.text = "Job Details: test-job"
        mock_driver.find_element.return_value = mock_element

        # Update mock_config paths
        mock_config["paths"]["output_dir"] = str(tmp_path)

        mock_session = mocker.patch("cluspro.download.browser_session")
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        mocker.patch("cluspro.download.authenticate")
        mocker.patch("cluspro.download.wait_for_element")
        mocker.patch("cluspro.download._download_pdb_models")
        mocker.patch("cluspro.download._download_scores")
        mocker.patch("cluspro.download.extract_archive")
        mocker.patch("cluspro.download.move_score_file")
        mocker.patch("time.sleep")

        from cluspro.download import download_results

        result_path = download_results(
            job_id=12345,
            output_dir=str(tmp_path),
            download_pdb=True,
            config=mock_config,
        )

        assert result_path.exists()


class TestExtractArchive:
    """Tests for extract_archive function."""

    def test_extract_handles_missing_archive(self, tmp_path, caplog):
        """Test extract handles missing archive gracefully."""
        import logging

        caplog.set_level(logging.WARNING)

        from cluspro.download import extract_archive

        extract_archive(tmp_path, tmp_path / "output")

        assert "No tar.bz2 archive found" in caplog.text

    def test_extract_handles_empty_dir(self, tmp_path, caplog):
        """Test extract handles empty directory."""
        import logging

        caplog.set_level(logging.WARNING)

        from cluspro.download import extract_archive

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        extract_archive(tmp_path, output_dir)

        assert "No tar.bz2 archive found" in caplog.text


class TestMoveScoreFile:
    """Tests for move_score_file function."""

    def test_move_score_file_success(self, tmp_path):
        """Test moving score file."""
        # Create a test CSV file
        csv_file = tmp_path / "scores.csv"
        csv_file.write_text("col1,col2\n1,2\n")

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        from cluspro.download import move_score_file

        move_score_file(tmp_path, output_dir)

        # Check file was moved and renamed
        moved_files = list(output_dir.glob("*.balanced.csv"))
        assert len(moved_files) == 1

    def test_move_score_file_no_csv(self, tmp_path, caplog):
        """Test move_score_file with no CSV present."""
        import logging

        caplog.set_level(logging.WARNING)

        from cluspro.download import move_score_file

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        move_score_file(tmp_path, output_dir)

        assert "No CSV file found" in caplog.text


class TestDownloadBatch:
    """Tests for download_batch function."""

    def test_download_batch_expands_sequence(self, mocker, mock_config):
        """Test batch download expands sequence notation."""
        mock_download = mocker.patch("cluspro.download.download_results")
        mock_download.return_value = Path("/tmp/result")
        mocker.patch("cluspro.download.load_config", return_value=mock_config)
        mocker.patch("time.sleep")

        from cluspro.download import download_batch

        download_batch("1:3", progress=False, config=mock_config)

        assert mock_download.call_count == 3

    def test_download_batch_continues_on_error(self, mocker, mock_config):
        """Test continue_on_error behavior."""
        mocker.patch("cluspro.download.download_results", side_effect=Exception("Error"))
        mocker.patch("cluspro.download.load_config", return_value=mock_config)
        mocker.patch("time.sleep")

        from cluspro.download import download_batch

        results = download_batch(
            [1, 2], continue_on_error=True, progress=False, config=mock_config
        )

        assert len(results) == 2
        assert all(r["status"] == "error" for r in results.values())

    def test_download_batch_empty_ids(self, mocker, mock_config):
        """Test download_batch with empty IDs."""
        mocker.patch("cluspro.download.load_config", return_value=mock_config)

        from cluspro.download import download_batch

        results = download_batch([], config=mock_config)

        assert results == {}


class TestGetJobNameFromPage:
    """Tests for get_job_name_from_page function."""

    def test_get_job_name_success(self, mocker, mock_config):
        """Test getting job name from page."""
        mock_driver = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "Job Details: my-test-job"
        mock_driver.find_element.return_value = mock_element

        mock_session = mocker.patch("cluspro.download.browser_session")
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        mocker.patch("cluspro.download.authenticate")
        mocker.patch("time.sleep")

        from cluspro.download import get_job_name_from_page

        name = get_job_name_from_page(12345, config=mock_config)

        assert name == "my-test-job"

    def test_get_job_name_failure(self, mocker, mock_config):
        """Test getting job name when element not found."""
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = Exception("Not found")

        mock_session = mocker.patch("cluspro.download.browser_session")
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        mocker.patch("cluspro.download.authenticate")
        mocker.patch("time.sleep")

        from cluspro.download import get_job_name_from_page

        name = get_job_name_from_page(12345, config=mock_config)

        assert name is None
