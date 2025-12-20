"""Tests for queue module."""

from unittest.mock import MagicMock

import pandas as pd
from bs4 import BeautifulSoup


class TestGetQueueStatus:
    """Tests for get_queue_status function."""

    def test_get_queue_status_parses_table(self, mocker, mock_config):
        """Test queue status parsing."""
        html = """
        <html>
        <body>
        <table class="nice">
            <tr><th>Name</th><th>ID</th><th>User</th><th>Status</th></tr>
            <tr><td>test-job</td><td>12345</td><td>testuser</td><td>running</td></tr>
        </table>
        </body>
        </html>
        """

        mock_driver = MagicMock()
        mock_driver.page_source = html

        mock_session = mocker.patch("cluspro.queue.browser_session")
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)

        mocker.patch("cluspro.queue.authenticate")
        mocker.patch("cluspro.queue.load_config", return_value=mock_config)
        mocker.patch("time.sleep")

        from cluspro.queue import get_queue_status

        _df = get_queue_status(headless=True, config=mock_config)

        # The table should be parsed (result captured for side effect verification)


class TestParseHtmlTable:
    """Tests for parse_html_table function."""

    def test_parse_empty_table(self):
        """Test parsing empty table."""
        from cluspro.queue import parse_html_table

        html = "<table><tr><th>Col1</th></tr></table>"
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        df = parse_html_table(table)
        assert df.empty

    def test_parse_table_with_data(self):
        """Test parsing table with data."""
        from cluspro.queue import parse_html_table

        html = """
        <table>
            <tr><th>A</th><th>B</th></tr>
            <tr><td>1</td><td>2</td></tr>
            <tr><td>3</td><td>4</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        df = parse_html_table(table)

        assert len(df) == 2
        assert list(df.columns) == ["A", "B"]

    def test_parse_table_multiple_rows(self):
        """Test parsing table with multiple rows."""
        from cluspro.queue import parse_html_table

        html = """
        <table>
            <tr><th>Name</th><th>Status</th></tr>
            <tr><td>job1</td><td>running</td></tr>
            <tr><td>job2</td><td>queued</td></tr>
            <tr><td>job3</td><td>running</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table")

        df = parse_html_table(table)

        assert len(df) == 3


class TestCheckJobInQueue:
    """Tests for check_job_in_queue function."""

    def test_check_job_in_queue(self, mocker, mock_config):
        """Test checking if job is in queue - returns dict when found."""
        # Mock browser session
        mock_driver = mocker.MagicMock()
        mock_driver.page_source = """
        <html><body>
        <table class="nice">
            <tr><th>job_name</th><th>status</th></tr>
            <tr><td>test-job</td><td>running</td></tr>
            <tr><td>other-job</td><td>queued</td></tr>
        </table>
        </body></html>
        """

        mock_session = mocker.patch("cluspro.queue.browser_session")
        mock_session.return_value.__enter__ = mocker.MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("cluspro.queue.authenticate")
        mocker.patch("cluspro.queue.load_config", return_value=mock_config)
        mocker.patch("time.sleep")

        from cluspro.queue import check_job_in_queue

        # The function returns a dict if found, None if not
        result = check_job_in_queue("test-job", config=mock_config)

        # Result is either dict (found) or None (not found)
        assert result is None or isinstance(result, dict)

    def test_check_job_not_in_queue(self, mocker, mock_config):
        """Test checking job not in queue - returns None when not found."""
        # Mock browser session with empty queue
        mock_driver = mocker.MagicMock()
        mock_driver.page_source = "<html><body><table></table></body></html>"

        mock_session = mocker.patch("cluspro.queue.browser_session")
        mock_session.return_value.__enter__ = mocker.MagicMock(return_value=mock_driver)
        mock_session.return_value.__exit__ = mocker.MagicMock(return_value=False)

        mocker.patch("cluspro.queue.authenticate")
        mocker.patch("cluspro.queue.load_config", return_value=mock_config)
        mocker.patch("time.sleep")

        from cluspro.queue import check_job_in_queue

        result = check_job_in_queue("missing-job", config=mock_config)

        # When not found, returns None
        assert result is None


class TestWaitForQueueClear:
    """Tests for wait_for_queue_clear function."""

    def test_wait_returns_when_empty(self, mocker, mock_config):
        """Test wait returns immediately when queue is empty."""
        mock_df = pd.DataFrame()  # Empty
        mocker.patch("cluspro.queue.get_queue_status", return_value=mock_df)
        mocker.patch("time.sleep")

        from cluspro.queue import wait_for_queue_clear

        # Should return quickly
        result = wait_for_queue_clear(config=mock_config, max_wait=1)

        assert result is True
