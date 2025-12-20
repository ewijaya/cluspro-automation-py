"""Tests for CLI module."""


class TestMainCommand:
    """Tests for main CLI command."""

    def test_main_help(self, cli_runner):
        """Test main command shows help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "ClusPro Automation CLI" in result.output

    def test_verbose_flag(self, cli_runner, mocker):
        """Test verbose flag sets debug logging."""
        mocker.patch("cluspro.cli.setup_logging")
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["-v", "--help"])

        assert result.exit_code == 0

    def test_quiet_flag(self, cli_runner, mocker):
        """Test quiet flag sets error logging."""
        mocker.patch("cluspro.cli.setup_logging")
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["-q", "--help"])

        assert result.exit_code == 0


class TestSubmitCommand:
    """Tests for submit CLI command."""

    def test_submit_requires_options(self, cli_runner, mocker):
        """Test submit requires all options."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["submit"])

        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_submit_help(self, cli_runner):
        """Test submit command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["submit", "--help"])

        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--receptor" in result.output
        assert "--ligand" in result.output


class TestQueueCommand:
    """Tests for queue CLI command."""

    def test_queue_help(self, cli_runner):
        """Test queue command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["queue", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output
        assert "--user" in result.output


class TestDownloadCommand:
    """Tests for download CLI command."""

    def test_download_requires_job_id(self, cli_runner, mocker):
        """Test download requires job ID."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["download"])

        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_download_help(self, cli_runner):
        """Test download command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["download", "--help"])

        assert result.exit_code == 0
        assert "--job-id" in result.output


class TestExpandCommand:
    """Tests for expand utility command."""

    def test_expand_sequence(self, cli_runner):
        """Test expand command."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["expand", "1:3,5"])

        assert result.exit_code == 0
        assert "1,2,3,5" in result.output

    def test_expand_single_number(self, cli_runner):
        """Test expand with single number."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["expand", "42"])

        assert result.exit_code == 0
        assert "42" in result.output


class TestCompressCommand:
    """Tests for compress utility command."""

    def test_compress_ids(self, cli_runner):
        """Test compress command."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["compress", "1", "2", "3", "5"])

        assert result.exit_code == 0
        assert "1:3,5" in result.output

    def test_compress_single_id(self, cli_runner):
        """Test compress with single ID."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["compress", "42"])

        assert result.exit_code == 0
        assert "42" in result.output


class TestConfigCommand:
    """Tests for config command."""

    def test_config_shows_yaml(self, cli_runner, mocker):
        """Test config command shows configuration."""
        mocker.patch("cluspro.cli.load_config", return_value={"test": "value"})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["config"])

        assert result.exit_code == 0
        assert "test" in result.output


class TestJobsCommand:
    """Tests for jobs command group."""

    def test_jobs_help(self, cli_runner):
        """Test jobs command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["jobs", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "resume" in result.output
        assert "status" in result.output

    def test_jobs_list_help(self, cli_runner):
        """Test jobs list command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["jobs", "list", "--help"])

        assert result.exit_code == 0
        assert "--status" in result.output
        assert "--batch" in result.output

    def test_jobs_list_empty(self, cli_runner, mocker, tmp_path):
        """Test jobs list with empty database."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        # Mock the database at the import location inside cli.py
        mock_db_class = mocker.patch("cluspro.database.JobDatabase")
        mock_db_class.return_value.get_all_jobs.return_value = []

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["jobs", "list"])

        assert result.exit_code == 0
        assert "No jobs found" in result.output

    def test_jobs_status_requires_batch(self, cli_runner, mocker):
        """Test jobs status requires batch ID."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["jobs", "status"])

        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_jobs_resume_requires_batch(self, cli_runner, mocker):
        """Test jobs resume requires batch ID."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["jobs", "resume"])

        assert result.exit_code != 0
        assert "Missing option" in result.output
