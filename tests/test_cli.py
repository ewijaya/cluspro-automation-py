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


class TestResultsCommand:
    """Tests for results CLI command."""

    def test_results_help(self, cli_runner):
        """Test results command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["results", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output
        assert "--max-pages" in result.output


class TestSummaryCommand:
    """Tests for summary CLI command."""

    def test_summary_help(self, cli_runner):
        """Test summary command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["summary", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output


class TestOrganizeCommand:
    """Tests for organize CLI command."""

    def test_organize_help(self, cli_runner):
        """Test organize command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["organize", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--source-dir" in result.output
        assert "--target-dir" in result.output

    def test_organize_requires_input(self, cli_runner, mocker):
        """Test organize requires input file."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["organize"])

        assert result.exit_code != 0
        assert "Missing option" in result.output


class TestListCommand:
    """Tests for list CLI command."""

    def test_list_help(self, cli_runner):
        """Test list command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["list", "--help"])

        assert result.exit_code == 0


class TestValidateCommand:
    """Tests for validate CLI command."""

    def test_validate_help(self, cli_runner):
        """Test validate command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--receptor" in result.output
        assert "--results-dir" in result.output
        assert "--topology" in result.output
        assert "--uniprot" in result.output

    def test_validate_requires_receptor(self, cli_runner, mocker):
        """Test validate requires receptor option."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["validate"])

        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_validate_requires_topology_or_uniprot(self, cli_runner, mocker, tmp_path):
        """Test validate requires either topology or uniprot."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        # Create temp receptor file
        receptor = tmp_path / "receptor.pdb"
        receptor.write_text("ATOM  1  CA  ALA A   1   0.0  0.0  0.0  1.0  0.0")

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        from cluspro.cli import main

        result = cli_runner.invoke(
            main,
            ["validate", "--receptor", str(receptor), "--results-dir", str(results_dir)],
        )

        assert result.exit_code != 0
        assert "Either --topology or --uniprot is required" in result.output


class TestMutuallyExclusiveFlags:
    """Tests for mutually exclusive CLI flags."""

    def test_guest_and_login_mutually_exclusive(self, cli_runner, mocker):
        """Test --guest and --login cannot be used together."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        # Need to invoke a subcommand (not --help) to trigger validation
        result = cli_runner.invoke(main, ["--guest", "--login", "config"])

        assert result.exit_code != 0
        assert "Cannot use both --guest and --login" in result.output


class TestSubmitBatchCommand:
    """Tests for submit-batch CLI command."""

    def test_submit_batch_help(self, cli_runner):
        """Test submit-batch command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["submit-batch", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output

    def test_submit_batch_requires_input(self, cli_runner, mocker):
        """Test submit-batch requires input file."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["submit-batch"])

        assert result.exit_code != 0
        assert "Missing option" in result.output


class TestDryRunCommand:
    """Tests for dry-run CLI command."""

    def test_dry_run_help(self, cli_runner):
        """Test dry-run command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["dry-run", "--help"])

        assert result.exit_code == 0
        assert "--input" in result.output


class TestDownloadBatchCommand:
    """Tests for download-batch CLI command."""

    def test_download_batch_help(self, cli_runner):
        """Test download-batch command help."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["download-batch", "--help"])

        assert result.exit_code == 0
        assert "--ids" in result.output

    def test_download_batch_requires_ids(self, cli_runner, mocker):
        """Test download-batch requires job IDs."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["download-batch"])

        assert result.exit_code != 0
        assert "Missing option" in result.output


class TestDryRunExecution:
    """Tests for dry-run command execution."""

    def test_dry_run_with_valid_csv(self, cli_runner, mocker, tmp_path):
        """Test dry-run with valid CSV file."""

        mocker.patch("cluspro.cli.load_config", return_value={})

        # Create test receptor and ligand files
        receptor = tmp_path / "receptor.pdb"
        ligand = tmp_path / "ligand.pdb"
        receptor.write_text("ATOM  1  CA  ALA A   1   0.0  0.0  0.0  1.0  0.0")
        ligand.write_text("ATOM  1  CA  ALA A   1   1.0  1.0  1.0  1.0  0.0")

        # Create CSV file
        csv_file = tmp_path / "jobs.csv"
        csv_content = f"job_name,receptor_pdb,ligand_pdb\ntest-job,{receptor},{ligand}\n"
        csv_file.write_text(csv_content)

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["dry-run", "-i", str(csv_file)])

        assert result.exit_code == 0
        assert "1 valid" in result.output


class TestSubmitExecution:
    """Tests for submit command execution."""

    def test_submit_success(self, cli_runner, mocker, tmp_path):
        """Test submit command success."""
        mocker.patch("cluspro.cli.load_config", return_value={})
        # Patch at the location where it's imported
        mocker.patch("cluspro.submit.submit_job", return_value="12345")

        # Create test files
        receptor = tmp_path / "receptor.pdb"
        ligand = tmp_path / "ligand.pdb"
        receptor.write_text("ATOM  1  CA  ALA A   1   0.0  0.0  0.0  1.0  0.0")
        ligand.write_text("ATOM  1  CA  ALA A   1   1.0  1.0  1.0  1.0  0.0")

        from cluspro.cli import main

        result = cli_runner.invoke(
            main, ["submit", "-n", "test-job", "-r", str(receptor), "-l", str(ligand)]
        )

        assert result.exit_code == 0
        assert "submitted successfully" in result.output

    def test_submit_error(self, cli_runner, mocker, tmp_path):
        """Test submit command with error."""
        mocker.patch("cluspro.cli.load_config", return_value={})
        # Patch at the location where it's imported
        mocker.patch("cluspro.submit.submit_job", side_effect=Exception("Connection failed"))

        # Create test files
        receptor = tmp_path / "receptor.pdb"
        ligand = tmp_path / "ligand.pdb"
        receptor.write_text("ATOM  1  CA  ALA A   1   0.0  0.0  0.0  1.0  0.0")
        ligand.write_text("ATOM  1  CA  ALA A   1   1.0  1.0  1.0  1.0  0.0")

        from cluspro.cli import main

        result = cli_runner.invoke(
            main, ["submit", "-n", "test-job", "-r", str(receptor), "-l", str(ligand)]
        )

        assert result.exit_code != 0
        assert "Error" in result.output


class TestConfigExecution:
    """Tests for config command execution."""

    def test_config_shows_empty(self, cli_runner, mocker):
        """Test config shows empty config."""
        mocker.patch("cluspro.cli.load_config", return_value={})

        from cluspro.cli import main

        result = cli_runner.invoke(main, ["config"])

        assert result.exit_code == 0


class TestExpandCompressExecution:
    """Tests for expand and compress commands execution."""

    def test_expand_multiple_ranges(self, cli_runner):
        """Test expand with multiple ranges."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["expand", "1:3,10:12"])

        assert result.exit_code == 0
        assert "1" in result.output
        assert "10" in result.output

    def test_compress_non_sequential(self, cli_runner):
        """Test compress with non-sequential IDs."""
        from cluspro.cli import main

        result = cli_runner.invoke(main, ["compress", "1", "3", "5", "7"])

        assert result.exit_code == 0
