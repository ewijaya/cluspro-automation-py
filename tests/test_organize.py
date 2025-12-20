"""Tests for organize module."""



class TestOrganizeResults:
    """Tests for organize_results function."""

    def test_organize_creates_target_dir(self, mocker, mock_config, tmp_path):
        """Test that organize creates target directory structure."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        job_dir = source_dir / "test-job"
        job_dir.mkdir(parents=True)
        (job_dir / "model.pdb").write_text("PDB content")

        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import organize_results

        mapping = [
            {
                "job_name": "test-job",
                "peptide_name": "peptide1",
                "receptor_name": "receptor1",
            }
        ]

        results = organize_results(
            mapping,
            source_dir=source_dir,
            target_dir=target_dir,
            config=mock_config,
        )

        assert "peptide1_v_receptor1" in results
        assert (target_dir / "peptide1_v_receptor1").exists()

    def test_organize_copies_pdb_files(self, mocker, mock_config, tmp_path):
        """Test that organize copies PDB files."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        job_dir = source_dir / "test-job"
        job_dir.mkdir(parents=True)

        # Create sample PDB files
        (job_dir / "model1.pdb").write_text("PDB content 1")
        (job_dir / "model2.pdb").write_text("PDB content 2")

        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import organize_results

        mapping = [
            {
                "job_name": "test-job",
                "peptide_name": "pep1",
                "receptor_name": "rec1",
            }
        ]

        organize_results(
            mapping,
            source_dir=source_dir,
            target_dir=target_dir,
            include_pdb=True,
            config=mock_config,
        )

        result_dir = target_dir / "pep1_v_rec1"
        pdb_files = list(result_dir.glob("*.pdb"))
        assert len(pdb_files) == 2

    def test_organize_skips_missing_source(self, mocker, mock_config, tmp_path):
        """Test organize handles missing source directories."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import organize_results

        mapping = [
            {
                "job_name": "nonexistent-job",
                "peptide_name": "pep1",
                "receptor_name": "rec1",
            }
        ]

        results = organize_results(
            mapping,
            source_dir=source_dir,
            target_dir=target_dir,
            config=mock_config,
        )

        assert results["pep1_v_rec1"]["status"] == "error"


class TestApplyReceptorSubstitutions:
    """Tests for apply_receptor_substitutions function."""

    def test_substitutions(self):
        """Test receptor name substitutions."""
        from cluspro.organize import apply_receptor_substitutions

        assert apply_receptor_substitutions("mMrgprx2") == "rMrgprx2"
        assert apply_receptor_substitutions("mEndg") == "mEndg_dimer"
        assert apply_receptor_substitutions("other") == "other"

    def test_no_substitution(self):
        """Test when no substitution matches."""
        from cluspro.organize import apply_receptor_substitutions

        result = apply_receptor_substitutions("someOtherReceptor")
        assert result == "someOtherReceptor"


class TestListOrganizedResults:
    """Tests for list_organized_results function."""

    def test_list_empty_directory(self, mocker, mock_config, tmp_path):
        """Test listing empty directory."""
        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import list_organized_results

        df = list_organized_results(target_dir=tmp_path, config=mock_config)

        assert df.empty

    def test_list_with_results(self, mocker, mock_config, tmp_path):
        """Test listing directory with results."""
        # Create sample result directories
        result1 = tmp_path / "pep1_v_rec1"
        result1.mkdir()
        (result1 / "model.pdb").write_text("PDB")
        (result1 / "scores.csv").write_text("scores")

        result2 = tmp_path / "pep2_v_rec2"
        result2.mkdir()
        (result2 / "model.pdb").write_text("PDB")

        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import list_organized_results

        df = list_organized_results(target_dir=tmp_path, config=mock_config)

        assert len(df) == 2
        assert "pep1_v_rec1" in df["name"].values
        assert "pep2_v_rec2" in df["name"].values


class TestOrganizeFromCsv:
    """Tests for organize_from_csv function."""

    def test_organize_from_csv(self, mocker, mock_config, tmp_path, sample_mapping_csv):
        """Test organizing from CSV file."""
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"

        # Create source directories
        (source_dir / "test-job-1").mkdir(parents=True)
        (source_dir / "test-job-1" / "model.pdb").write_text("PDB")

        (source_dir / "test-job-2").mkdir(parents=True)
        (source_dir / "test-job-2" / "model.pdb").write_text("PDB")

        mocker.patch("cluspro.organize.load_config", return_value=mock_config)

        from cluspro.organize import organize_from_csv

        results = organize_from_csv(
            csv_path=sample_mapping_csv,
            source_dir=source_dir,
            target_dir=target_dir,
            config=mock_config,
        )

        assert "peptide1_v_receptor1" in results
        assert "peptide2_v_receptor2" in results


class TestCleanupEmptyDirs:
    """Tests for cleanup_empty_dirs function."""

    def test_cleanup_removes_empty_dirs(self, tmp_path):
        """Test that cleanup removes empty directories."""
        # Create empty directories
        empty1 = tmp_path / "empty1"
        empty1.mkdir()

        empty2 = tmp_path / "empty2"
        empty2.mkdir()

        # Create non-empty directory
        nonempty = tmp_path / "nonempty"
        nonempty.mkdir()
        (nonempty / "file.txt").write_text("content")

        from cluspro.organize import cleanup_empty_dirs

        # With dry_run=False to actually delete
        result = cleanup_empty_dirs(tmp_path, dry_run=False)

        assert not empty1.exists()
        assert not empty2.exists()
        assert nonempty.exists()
        # Result should list the deleted directories
        assert len(result) == 2

    def test_cleanup_dry_run(self, tmp_path):
        """Test cleanup with dry_run=True (default)."""
        empty1 = tmp_path / "empty1"
        empty1.mkdir()

        from cluspro.organize import cleanup_empty_dirs

        # Dry run should not delete anything
        result = cleanup_empty_dirs(tmp_path, dry_run=True)

        assert empty1.exists()  # Still exists
        assert len(result) == 1  # But was reported
