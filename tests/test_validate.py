"""Tests for validate module."""

import json
import tempfile
from unittest.mock import MagicMock

import pytest

# Skip all tests in this module if BioPython/scipy not installed
pytest.importorskip("Bio.PDB")
pytest.importorskip("scipy")


class TestTopology:
    """Tests for Topology dataclass."""

    def test_get_region_type_extracellular(self):
        """Test identifying extracellular region."""
        from cluspro.validate import Topology

        topo = Topology(
            extracellular=[(1, 45), (97, 107)],
            transmembrane=[(46, 66), (76, 96)],
            intracellular=[(67, 75)],
        )

        assert topo.get_region_type(1) == "extracellular"
        assert topo.get_region_type(45) == "extracellular"
        assert topo.get_region_type(100) == "extracellular"

    def test_get_region_type_transmembrane(self):
        """Test identifying transmembrane region."""
        from cluspro.validate import Topology

        topo = Topology(
            extracellular=[(1, 45)],
            transmembrane=[(46, 66), (76, 96)],
            intracellular=[(67, 75)],
        )

        assert topo.get_region_type(46) == "transmembrane"
        assert topo.get_region_type(55) == "transmembrane"
        assert topo.get_region_type(80) == "transmembrane"

    def test_get_region_type_intracellular(self):
        """Test identifying intracellular region."""
        from cluspro.validate import Topology

        topo = Topology(
            extracellular=[(1, 45)],
            transmembrane=[(46, 66)],
            intracellular=[(67, 75), (100, 120)],
        )

        assert topo.get_region_type(67) == "intracellular"
        assert topo.get_region_type(70) == "intracellular"
        assert topo.get_region_type(110) == "intracellular"

    def test_get_region_type_unknown(self):
        """Test unknown region for residues not in any defined region."""
        from cluspro.validate import Topology

        topo = Topology(
            extracellular=[(1, 45)],
            transmembrane=[(50, 60)],
            intracellular=[(70, 80)],
        )

        assert topo.get_region_type(47) == "unknown"
        assert topo.get_region_type(65) == "unknown"
        assert topo.get_region_type(200) == "unknown"

    def test_empty_topology(self):
        """Test topology with no regions defined."""
        from cluspro.validate import Topology

        topo = Topology()

        assert topo.get_region_type(1) == "unknown"
        assert topo.get_region_type(100) == "unknown"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_result(self):
        """Test creating a validation result."""
        from cluspro.validate import ValidationResult

        result = ValidationResult(
            target="pep1_v_rec1",
            model="model.000.01.pdb",
            cluster=1,
            center_score=100.5,
            clashes=5,
            ec_contacts=50,
            tm_contacts=10,
            ic_contacts=5,
            ec_pct=76.9,
            validity_score=71.9,
            alignment_rmsd=1.5,
        )

        assert result.target == "pep1_v_rec1"
        assert result.cluster == 1
        assert result.ec_pct == 76.9

    def test_result_with_error(self):
        """Test result with error."""
        from cluspro.validate import ValidationResult

        result = ValidationResult(
            target="test",
            model="test.pdb",
            cluster=None,
            center_score=None,
            clashes=0,
            ec_contacts=0,
            tm_contacts=0,
            ic_contacts=0,
            ec_pct=0,
            error="File not found",
        )

        assert result.error == "File not found"
        assert result.cluster is None


class TestCalculateValidityScore:
    """Tests for calculate_validity_score function."""

    def test_perfect_score(self):
        """Test perfect score with all EC contacts and no clashes."""
        from cluspro.validate import calculate_validity_score

        score = calculate_validity_score(ec_pct=100.0, clashes=0, tm_contacts=0, ic_contacts=0)
        assert score == 100.0

    def test_score_with_clashes(self):
        """Test score reduced by clashes."""
        from cluspro.validate import calculate_validity_score

        score = calculate_validity_score(ec_pct=100.0, clashes=10, tm_contacts=0, ic_contacts=0)
        assert score == 90.0

    def test_score_clamped_to_zero(self):
        """Test score doesn't go below 0."""
        from cluspro.validate import calculate_validity_score

        score = calculate_validity_score(ec_pct=10.0, clashes=50, tm_contacts=0, ic_contacts=0)
        assert score == 0.0

    def test_score_clamped_to_hundred(self):
        """Test score doesn't go above 100."""
        from cluspro.validate import calculate_validity_score

        # Even if somehow ec_pct > 100, result should be clamped
        score = calculate_validity_score(ec_pct=100.0, clashes=0, tm_contacts=0, ic_contacts=0)
        assert score <= 100.0

    def test_mixed_score(self):
        """Test typical mixed score scenario."""
        from cluspro.validate import calculate_validity_score

        score = calculate_validity_score(ec_pct=75.0, clashes=5, tm_contacts=10, ic_contacts=5)
        assert score == 70.0


class TestLoadTopologyFromJson:
    """Tests for load_topology_from_json function."""

    def test_load_simple_format(self):
        """Test loading simple JSON format."""
        from cluspro.validate import load_topology_from_json

        data = {
            "extracellular": [[1, 45], [97, 107]],
            "transmembrane": [[46, 66], [76, 96]],
            "intracellular": [[67, 75]],
            "alignment_residues": [97, 107],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            topo = load_topology_from_json(f.name)

        assert len(topo.extracellular) == 2
        assert len(topo.transmembrane) == 2
        assert len(topo.intracellular) == 1
        assert topo.alignment_residues == (97, 107)

    def test_load_uniprot_format(self):
        """Test loading UniProt JSON format."""
        from cluspro.validate import load_topology_from_json

        data = {
            "features": [
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 1}, "end": {"value": 45}},
                    "description": "Extracellular",
                },
                {
                    "type": "Transmembrane",
                    "location": {"start": {"value": 46}, "end": {"value": 66}},
                    "description": "Helical",
                },
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 67}, "end": {"value": 75}},
                    "description": "Cytoplasmic",
                },
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            topo = load_topology_from_json(f.name)

        assert len(topo.extracellular) == 1
        assert len(topo.transmembrane) == 1
        assert len(topo.intracellular) == 1

    def test_load_empty_topology(self):
        """Test loading empty topology file."""
        from cluspro.validate import load_topology_from_json

        data = {}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()

            topo = load_topology_from_json(f.name)

        assert len(topo.extracellular) == 0
        assert len(topo.transmembrane) == 0
        assert len(topo.intracellular) == 0


class TestParseUniprotTopology:
    """Tests for _parse_uniprot_topology function."""

    def test_parse_complete_topology(self):
        """Test parsing complete UniProt topology."""
        from cluspro.validate import _parse_uniprot_topology

        data = {
            "features": [
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 1}, "end": {"value": 45}},
                    "description": "Extracellular",
                },
                {
                    "type": "Transmembrane",
                    "location": {"start": {"value": 46}, "end": {"value": 66}},
                    "description": "Helical; Name=1",
                },
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 67}, "end": {"value": 75}},
                    "description": "Cytoplasmic",
                },
                {
                    "type": "Transmembrane",
                    "location": {"start": {"value": 76}, "end": {"value": 96}},
                    "description": "Helical; Name=2",
                },
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 97}, "end": {"value": 107}},
                    "description": "Extracellular",
                },
            ]
        }

        topo = _parse_uniprot_topology(data)

        assert len(topo.extracellular) == 2
        assert len(topo.transmembrane) == 2
        assert len(topo.intracellular) == 1
        assert topo.alignment_residues == (1, 45)  # First EC region

    def test_parse_missing_locations(self):
        """Test parsing with missing location data."""
        from cluspro.validate import _parse_uniprot_topology

        data = {
            "features": [
                {
                    "type": "Topological domain",
                    "location": {"start": {}, "end": {"value": 45}},  # Missing start value
                    "description": "Extracellular",
                },
                {
                    "type": "Transmembrane",
                    "location": {"start": {"value": 46}, "end": {"value": 66}},
                    "description": "Helical",
                },
            ]
        }

        topo = _parse_uniprot_topology(data)

        assert len(topo.extracellular) == 0  # Skipped due to missing start
        assert len(topo.transmembrane) == 1

    def test_parse_intracellular_variations(self):
        """Test parsing different intracellular descriptions."""
        from cluspro.validate import _parse_uniprot_topology

        data = {
            "features": [
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 1}, "end": {"value": 10}},
                    "description": "Intracellular",
                },
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 20}, "end": {"value": 30}},
                    "description": "cytoplasmic domain",
                },
            ]
        }

        topo = _parse_uniprot_topology(data)

        assert len(topo.intracellular) == 2


class TestFetchTopologyFromUniprot:
    """Tests for fetch_topology_from_uniprot function."""

    def test_fetch_success(self, mocker):
        """Test successful fetch from UniProt."""
        from cluspro.validate import fetch_topology_from_uniprot

        mock_data = {
            "features": [
                {
                    "type": "Topological domain",
                    "location": {"start": {"value": 1}, "end": {"value": 45}},
                    "description": "Extracellular",
                },
                {
                    "type": "Transmembrane",
                    "location": {"start": {"value": 46}, "end": {"value": 66}},
                    "description": "Helical",
                },
            ],
            "proteinDescription": {"recommendedName": {"fullName": {"value": "Test Receptor"}}},
        }

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        topo = fetch_topology_from_uniprot("Q3UG50")

        assert len(topo.extracellular) == 1
        assert len(topo.transmembrane) == 1

    def test_fetch_not_found(self, mocker):
        """Test handling 404 error."""
        import urllib.error

        from cluspro.validate import fetch_topology_from_uniprot

        mock_error = urllib.error.HTTPError(
            url="https://rest.uniprot.org/uniprotkb/INVALID.json",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        mocker.patch("urllib.request.urlopen", side_effect=mock_error)

        with pytest.raises(ValueError, match="UniProt accession not found"):
            fetch_topology_from_uniprot("INVALID")

    def test_fetch_no_topology_data(self, mocker):
        """Test handling response with no topology features."""
        from cluspro.validate import fetch_topology_from_uniprot

        mock_data = {"features": []}  # No topology features

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mocker.patch("urllib.request.urlopen", return_value=mock_response)

        with pytest.raises(ValueError, match="No topology annotations found"):
            fetch_topology_from_uniprot("Q12345")


class TestGetClusproScores:
    """Tests for get_cluspro_scores function."""

    def test_read_scores_from_csv(self, tmp_path):
        """Test reading scores from CSV file."""
        from cluspro.validate import get_cluspro_scores

        csv_content = """Cluster,Representative,Weighted Score
0,Center,-850.5
0,Member,-800.0
1,Center,-750.2
1,Member,-700.0
"""
        csv_file = tmp_path / "cluspro_scores.12345.000.balanced.csv"
        csv_file.write_text(csv_content)

        scores, coefficient = get_cluspro_scores(str(tmp_path))

        assert coefficient == "000"
        assert 0 in scores
        assert 1 in scores
        assert scores[0] == -850.5
        assert scores[1] == -750.2

    def test_no_score_files(self, tmp_path):
        """Test handling missing score files."""
        from cluspro.validate import get_cluspro_scores

        scores, coefficient = get_cluspro_scores(str(tmp_path))

        assert scores == {}
        assert coefficient is None


class TestDockingValidator:
    """Tests for DockingValidator class."""

    @pytest.fixture
    def sample_pdb(self, tmp_path):
        """Create a minimal PDB file for testing."""
        pdb_content = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.251   2.390   0.000  1.00  0.00           O
ATOM      5  N   GLY A   2       3.326   1.540   0.000  1.00  0.00           N
ATOM      6  CA  GLY A   2       3.970   2.840   0.000  1.00  0.00           C
ATOM      7  C   GLY A   2       5.490   2.720   0.000  1.00  0.00           C
ATOM      8  O   GLY A   2       6.030   1.610   0.000  1.00  0.00           O
END
"""
        pdb_file = tmp_path / "receptor.pdb"
        pdb_file.write_text(pdb_content)
        return str(pdb_file)

    @pytest.fixture
    def sample_topology(self):
        """Create a sample topology."""
        from cluspro.validate import Topology

        return Topology(
            extracellular=[(1, 10)],
            transmembrane=[(11, 20)],
            intracellular=[(21, 30)],
        )

    def test_init_validator(self, sample_pdb, sample_topology):
        """Test initializing validator."""
        from cluspro.validate import DockingValidator

        validator = DockingValidator(
            receptor_pdb=sample_pdb,
            topology=sample_topology,
        )

        assert validator.topology == sample_topology
        assert len(validator.receptor_atoms) > 0

    def test_get_all_atoms(self, sample_pdb, sample_topology):
        """Test getting all atoms from structure."""
        from cluspro.validate import DockingValidator

        validator = DockingValidator(
            receptor_pdb=sample_pdb,
            topology=sample_topology,
        )

        assert len(validator.receptor_atoms) == 8  # 8 atoms in sample PDB

    def test_validate_model_file_not_found(self, sample_pdb, sample_topology):
        """Test validation with non-existent model file."""
        from cluspro.validate import DockingValidator

        validator = DockingValidator(
            receptor_pdb=sample_pdb,
            topology=sample_topology,
        )

        result = validator.validate_model("/nonexistent/model.pdb")

        assert result.error is not None


class TestValidateDocking:
    """Tests for validate_docking function."""

    def test_validate_empty_directory(self, tmp_path):
        """Test validation with empty results directory."""
        from cluspro.validate import Topology, validate_docking

        # Create minimal receptor PDB
        pdb_content = """ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00  0.00           C
END
"""
        receptor = tmp_path / "receptor.pdb"
        receptor.write_text(pdb_content)

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        topology = Topology(extracellular=[(1, 10)])

        results = validate_docking(
            receptor_pdb=str(receptor),
            results_dir=str(results_dir),
            topology=topology,
        )

        assert len(results) == 0
