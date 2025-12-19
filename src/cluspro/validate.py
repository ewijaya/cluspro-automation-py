"""
Docking validation module for ClusPro results.

Validates docked peptide poses by analyzing contacts with receptor regions
(extracellular, transmembrane, intracellular) based on UniProt topology.

Example usage:
    from cluspro.validate import validate_docking, load_topology_from_json

    topology = load_topology_from_json("topology.json")
    results = validate_docking(
        receptor_pdb="receptor.pdb",
        results_dir="./cluspro_results",
        topology=topology
    )

    # Or fetch directly from UniProt:
    from cluspro.validate import fetch_topology_from_uniprot

    topology = fetch_topology_from_uniprot("Q3UG50")
"""

import csv
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from Bio.PDB import PDBParser, Superimposer
except ImportError:
    raise ImportError(
        "BioPython is required for docking validation. "
        "Install with: pip install biopython"
    )

try:
    from scipy.spatial import cKDTree
except ImportError:
    raise ImportError(
        "SciPy is required for docking validation. " "Install with: pip install scipy"
    )

logger = logging.getLogger(__name__)

# Default distance thresholds (Angstroms)
DEFAULT_CONTACT_THRESHOLD = 4.5
DEFAULT_CLASH_THRESHOLD = 2.0


@dataclass
class Topology:
    """Receptor topology defining region boundaries."""

    extracellular: list = field(default_factory=list)  # [(start, end), ...]
    transmembrane: list = field(default_factory=list)
    intracellular: list = field(default_factory=list)
    alignment_residues: tuple = (None, None)  # (start, end) for superposition

    def get_region_type(self, residue_num: int) -> str:
        """Determine which region type a residue belongs to."""
        for start, end in self.extracellular:
            if start <= residue_num <= end:
                return "extracellular"
        for start, end in self.transmembrane:
            if start <= residue_num <= end:
                return "transmembrane"
        for start, end in self.intracellular:
            if start <= residue_num <= end:
                return "intracellular"
        return "unknown"


@dataclass
class ValidationResult:
    """Result of validating a single docking pose."""

    target: str
    model: str
    cluster: Optional[int]
    center_score: Optional[float]
    clashes: int
    ec_contacts: int
    tm_contacts: int
    ic_contacts: int
    ec_pct: float
    validity_score: float = 0.0
    alignment_rmsd: Optional[float] = None
    error: Optional[str] = None


def calculate_validity_score(ec_pct: float, clashes: int, tm_contacts: int, ic_contacts: int) -> float:
    """
    Calculate composite validity score (0-100).

    Higher score = more valid (more EC contacts, fewer clashes)

    Formula:
        score = ec_pct - clashes
        clamped to 0-100

    Note: TM/IC contacts are already reflected in lower ec_pct, so we don't
    double-penalize them. Only clashes get an additional penalty.
    """
    clash_penalty = clashes

    score = ec_pct - clash_penalty

    # Clamp to 0-100
    return max(0.0, min(100.0, round(score, 1)))


def load_topology_from_json(json_path: str) -> Topology:
    """
    Load receptor topology from JSON file.

    Expected format (UniProt features export or custom):
    {
        "extracellular": [[1, 45], [97, 107], ...],
        "transmembrane": [[46, 66], [76, 96], ...],
        "intracellular": [[67, 75], [129, 155], ...],
        "alignment_residues": [97, 107]
    }

    Or UniProt format:
    {
        "features": [
            {"type": "Topological domain", "location": {"start": {"value": 1}, "end": {"value": 45}}, "description": "Extracellular"},
            ...
        ]
    }
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    # Check if UniProt format
    if "features" in data:
        return _parse_uniprot_topology(data)

    # Simple format
    return Topology(
        extracellular=[tuple(r) for r in data.get("extracellular", [])],
        transmembrane=[tuple(r) for r in data.get("transmembrane", [])],
        intracellular=[tuple(r) for r in data.get("intracellular", [])],
        alignment_residues=tuple(data.get("alignment_residues", [None, None])),
    )


def _parse_uniprot_topology(data: dict) -> Topology:
    """Parse UniProt JSON features into Topology."""
    extracellular = []
    transmembrane = []
    intracellular = []

    for feature in data.get("features", []):
        feat_type = feature.get("type", "")
        desc = feature.get("description", "").lower()
        loc = feature.get("location", {})
        start = loc.get("start", {}).get("value")
        end = loc.get("end", {}).get("value")

        if start is None or end is None:
            continue

        region = (start, end)

        if feat_type == "Topological domain":
            if "extracellular" in desc:
                extracellular.append(region)
            elif "cytoplasmic" in desc or "intracellular" in desc:
                intracellular.append(region)
        elif feat_type == "Transmembrane":
            transmembrane.append(region)

    # Use first extracellular region for alignment by default
    alignment = extracellular[0] if extracellular else (None, None)

    return Topology(
        extracellular=extracellular,
        transmembrane=transmembrane,
        intracellular=intracellular,
        alignment_residues=alignment,
    )


def fetch_topology_from_uniprot(accession: str, alignment_region: str = "ECL1") -> Topology:
    """
    Fetch receptor topology directly from UniProt REST API.

    Args:
        accession: UniProt accession ID (e.g., "Q3UG50")
        alignment_region: Which extracellular region to use for alignment.
                         Options: "ECL1", "ECL2", "ECL3", "N_term", or "first" (default first EC region)

    Returns:
        Topology object with extracellular, transmembrane, and intracellular regions

    Raises:
        ValueError: If accession not found or no topology data available

    Example:
        topology = fetch_topology_from_uniprot("Q3UG50")
        topology = fetch_topology_from_uniprot("P25025", alignment_region="ECL2")
    """
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"

    logger.info(f"Fetching topology from UniProt: {accession}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"UniProt accession not found: {accession}")
        raise ValueError(f"Failed to fetch from UniProt: {e}")
    except urllib.error.URLError as e:
        raise ValueError(f"Network error fetching UniProt data: {e}")

    # Extract topology features
    extracellular = []
    transmembrane = []
    intracellular = []
    ec_regions = {}  # Track named EC regions for alignment selection

    features = data.get("features", [])
    topology_features = [
        f for f in features if f.get("type") in ("Topological domain", "Transmembrane")
    ]

    if not topology_features:
        raise ValueError(f"No topology annotations found for {accession}")

    ec_index = 0
    for feature in topology_features:
        feat_type = feature.get("type", "")
        desc = feature.get("description", "").lower()
        loc = feature.get("location", {})
        start = loc.get("start", {}).get("value")
        end = loc.get("end", {}).get("value")

        if start is None or end is None:
            continue

        region = (start, end)

        if feat_type == "Topological domain":
            if "extracellular" in desc:
                extracellular.append(region)
                # Track region names for alignment selection
                if ec_index == 0 and start < 50:  # Likely N-terminus
                    ec_regions["N_term"] = region
                else:
                    ec_regions[f"ECL{ec_index}"] = region
                ec_index += 1
            elif "cytoplasmic" in desc or "intracellular" in desc:
                intracellular.append(region)
        elif feat_type == "Transmembrane":
            transmembrane.append(region)

    if not extracellular and not transmembrane:
        raise ValueError(f"No extracellular or transmembrane regions found for {accession}")

    # Select alignment region
    if alignment_region == "first":
        alignment = extracellular[0] if extracellular else (None, None)
    elif alignment_region in ec_regions:
        alignment = ec_regions[alignment_region]
    else:
        # Default to first actual ECL (skip N-terminus if present)
        if "ECL1" in ec_regions:
            alignment = ec_regions["ECL1"]
        elif extracellular:
            alignment = extracellular[0]
        else:
            alignment = (None, None)

    # Get protein name for logging
    protein_name = data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", accession)
    logger.info(f"Loaded topology for {protein_name}: {len(extracellular)} EC, {len(transmembrane)} TM, {len(intracellular)} IC regions")

    return Topology(
        extracellular=extracellular,
        transmembrane=transmembrane,
        intracellular=intracellular,
        alignment_residues=alignment,
    )


class DockingValidator:
    """Validates ClusPro docking results against receptor topology."""

    def __init__(
        self,
        receptor_pdb: str,
        topology: Topology,
        contact_threshold: float = DEFAULT_CONTACT_THRESHOLD,
        clash_threshold: float = DEFAULT_CLASH_THRESHOLD,
    ):
        self.topology = topology
        self.contact_threshold = contact_threshold
        self.clash_threshold = clash_threshold
        self.parser = PDBParser(QUIET=True)

        logger.info(f"Loading receptor: {receptor_pdb}")
        self.receptor = self.parser.get_structure("receptor", receptor_pdb)
        self.receptor_atoms = self._get_all_atoms(self.receptor)

    def _get_all_atoms(self, structure):
        """Get all atoms from structure."""
        atoms = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    for atom in residue:
                        atoms.append(atom)
        return atoms

    def _get_ca_atoms_in_range(self, structure, start_res: int, end_res: int):
        """Get CA atoms in residue range for alignment."""
        ca_atoms = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    res_num = residue.id[1]
                    if start_res <= res_num <= end_res and "CA" in residue:
                        ca_atoms.append(residue["CA"])
        return ca_atoms

    def _parse_docked_complex(self, pdb_path: str):
        """Parse ClusPro docked complex, separate receptor fragment and peptide."""
        structure = self.parser.get_structure("docked", pdb_path)
        receptor_atoms = []
        peptide_atoms = []

        # Receptor fragment residue ranges (ECL regions only, exclude N-terminus)
        # N-terminus is typically residues < 50, ECL regions start at higher numbers
        # This prevents misclassifying peptide residues as receptor
        receptor_ranges = [(s, e) for s, e in self.topology.extracellular if s > 50]

        for model in structure:
            for chain in model:
                for residue in chain:
                    res_num = residue.id[1]
                    is_receptor = any(
                        start <= res_num <= end for start, end in receptor_ranges
                    )
                    for atom in residue:
                        if is_receptor:
                            receptor_atoms.append(atom)
                        else:
                            peptide_atoms.append(atom)

        return structure, receptor_atoms, peptide_atoms

    def _calculate_contacts(self, peptide_atoms):
        """Calculate contacts between peptide and full receptor."""
        if not self.receptor_atoms or not peptide_atoms:
            return [], 0

        receptor_coords = np.array([atom.coord for atom in self.receptor_atoms])
        tree = cKDTree(receptor_coords)

        contacts = []
        clashes = 0

        for pep_atom in peptide_atoms:
            # Check for clashes
            clash_indices = tree.query_ball_point(pep_atom.coord, self.clash_threshold)
            clashes += len(clash_indices)

            # Check for contacts
            contact_indices = tree.query_ball_point(
                pep_atom.coord, self.contact_threshold
            )
            for idx in contact_indices:
                rec_atom = self.receptor_atoms[idx]
                res_num = rec_atom.get_parent().id[1]
                region_type = self.topology.get_region_type(res_num)
                contacts.append(region_type)

        return contacts, clashes

    def validate_model(self, pdb_path: str) -> ValidationResult:
        """Validate a single docked model."""
        model_name = Path(pdb_path).name
        target = Path(pdb_path).parent.name

        # Extract cluster from filename (model.006.13.pdb -> cluster 13)
        # ClusPro naming: model.{coefficient}.{cluster}.pdb
        cluster = None
        parts = model_name.replace(".pdb", "").split(".")
        if len(parts) >= 3:  # Need 3 parts: model, coefficient, cluster
            try:
                cluster = int(parts[2])  # Third part is cluster
            except ValueError:
                pass

        try:
            docked_structure, rec_atoms, pep_atoms = self._parse_docked_complex(
                pdb_path
            )

            if not pep_atoms:
                return ValidationResult(
                    target=target,
                    model=model_name,
                    cluster=cluster,
                    center_score=None,
                    clashes=0,
                    ec_contacts=0,
                    tm_contacts=0,
                    ic_contacts=0,
                    ec_pct=0,
                    error="No peptide atoms found",
                )

            # Get CA atoms for alignment
            align_start, align_end = self.topology.alignment_residues
            if align_start and align_end:
                docked_ca = self._get_ca_atoms_in_range(
                    docked_structure, align_start, align_end
                )
                full_ca = self._get_ca_atoms_in_range(
                    self.receptor, align_start, align_end
                )

                if len(docked_ca) >= 3 and len(full_ca) >= 3:
                    min_atoms = min(len(docked_ca), len(full_ca))
                    sup = Superimposer()
                    sup.set_atoms(full_ca[:min_atoms], docked_ca[:min_atoms])
                    sup.apply(pep_atoms)
                    rmsd = sup.rms
                else:
                    rmsd = None
            else:
                rmsd = None

            # Calculate contacts
            contacts, clashes = self._calculate_contacts(pep_atoms)

            ec_contacts = contacts.count("extracellular")
            tm_contacts = contacts.count("transmembrane")
            ic_contacts = contacts.count("intracellular")
            total = ec_contacts + tm_contacts + ic_contacts
            ec_pct = (ec_contacts / total * 100) if total > 0 else 0

            # Calculate validity score
            validity = calculate_validity_score(ec_pct, clashes, tm_contacts, ic_contacts)

            return ValidationResult(
                target=target,
                model=model_name,
                cluster=cluster,
                center_score=None,  # Will be filled from ClusPro scores
                clashes=clashes,
                ec_contacts=ec_contacts,
                tm_contacts=tm_contacts,
                ic_contacts=ic_contacts,
                ec_pct=round(ec_pct, 1),
                validity_score=validity,
                alignment_rmsd=round(rmsd, 2) if rmsd else None,
            )

        except Exception as e:
            logger.error(f"Error validating {pdb_path}: {e}")
            return ValidationResult(
                target=target,
                model=model_name,
                cluster=cluster,
                center_score=None,
                clashes=0,
                ec_contacts=0,
                tm_contacts=0,
                ic_contacts=0,
                ec_pct=0,
                error=str(e),
            )


def get_cluspro_scores(target_dir: str) -> tuple:
    """Read ClusPro scores from CSV file.

    Supports all ClusPro scoring functions:
    - cluspro_scores.{job_id}.000.balanced.csv
    - cluspro_scores.{job_id}.002.Electrostatic_favored.csv
    - cluspro_scores.{job_id}.004.Hydrophobic_favored.csv
    - cluspro_scores.{job_id}.006.Van_der_Waals_plus_Electrostatics.csv

    Returns:
        Tuple of (scores_dict, coefficient_str) where coefficient is e.g. "000"
    """
    scores = {}
    coefficient = None
    score_files = list(Path(target_dir).glob("cluspro_scores.*.csv"))

    if not score_files:
        return scores, coefficient

    # Extract coefficient from filename: cluspro_scores.{job_id}.{coefficient}.{name}.csv
    csv_name = score_files[0].name
    parts = csv_name.replace(".csv", "").split(".")
    if len(parts) >= 3:
        coefficient = parts[2]  # e.g., "000", "002", "004", "006"

    with open(score_files[0], "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Representative") == "Center":
                cluster = int(row["Cluster"])
                center_score = float(row["Weighted Score"])
                scores[cluster] = center_score

    return scores, coefficient


def validate_docking(
    receptor_pdb: str,
    results_dir: str,
    topology: Topology,
    output_dir: Optional[str] = None,
    contact_threshold: float = DEFAULT_CONTACT_THRESHOLD,
    clash_threshold: float = DEFAULT_CLASH_THRESHOLD,
    find_min_clash: bool = True,
) -> list:
    """
    Validate ClusPro docking results.

    Args:
        receptor_pdb: Path to full receptor PDB file
        results_dir: Directory containing ClusPro result folders
        topology: Receptor topology definition
        output_dir: Optional output directory for results
        contact_threshold: Distance threshold for contacts (Angstroms)
        clash_threshold: Distance threshold for clashes (Angstroms)
        find_min_clash: If True, find model with minimum clashes per target

    Returns:
        List of ValidationResult objects
    """
    validator = DockingValidator(
        receptor_pdb=receptor_pdb,
        topology=topology,
        contact_threshold=contact_threshold,
        clash_threshold=clash_threshold,
    )

    results_path = Path(results_dir)

    # Scan all directories for targets
    targets = [
        d.name for d in results_path.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]

    results = []

    for i, target in enumerate(targets):
        target_dir = results_path / target
        if not target_dir.exists():
            logger.warning(f"Target directory not found: {target_dir}")
            continue

        cluspro_scores, coefficient = get_cluspro_scores(str(target_dir))

        # Only process PDB files matching the coefficient from the CSV
        # e.g., if CSV is cluspro_scores.*.000.balanced.csv, only use model.000.*.pdb
        if coefficient:
            model_files = sorted(target_dir.glob(f"model.{coefficient}.*.pdb"))
        else:
            # Fallback to balanced (000) if no CSV found
            model_files = sorted(target_dir.glob("model.000.*.pdb"))

        if not model_files:
            logger.warning(f"No model files found in {target_dir}")
            continue

        logger.info(f"[{i+1}/{len(targets)}] Validating {target}: {len(model_files)} models")

        if find_min_clash:
            # Find model with minimum clashes
            best_result = None
            min_clashes = float("inf")

            for model_path in model_files:
                result = validator.validate_model(str(model_path))
                if result.error is None and result.clashes < min_clashes:
                    min_clashes = result.clashes
                    best_result = result

            if best_result:
                # Add ClusPro score
                if best_result.cluster is not None:
                    best_result.center_score = cluspro_scores.get(best_result.cluster)
                results.append(best_result)
                logger.info(
                    f"  Best: {best_result.model} (Cluster {best_result.cluster}, "
                    f"Clashes: {best_result.clashes}, EC: {best_result.ec_pct}%)"
                )
        else:
            # Validate all models
            for model_path in model_files:
                result = validator.validate_model(str(model_path))
                if result.cluster is not None:
                    result.center_score = cluspro_scores.get(result.cluster)
                results.append(result)

    # Sort by clashes
    results.sort(key=lambda x: (x.error is not None, x.clashes))

    # Write output if specified
    if output_dir:
        _write_results(results, topology, output_dir)

    return results


def _write_results(results: list, topology: Topology, output_dir: str):
    """Write validation results to CSV with methodology header."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    csv_path = output_path / "docking_validation.csv"

    with open(csv_path, "w", newline="") as f:
        # Write methodology header
        f.write("# =============================================================================\n")
        f.write("# ClusPro Docking Validation Results\n")
        f.write("# =============================================================================\n")
        f.write("#\n")
        f.write("# METHODOLOGY:\n")
        f.write("# Validates peptide-GPCR docking poses by analyzing contacts with receptor regions.\n")
        f.write("#\n")
        f.write("# TOPOLOGY:\n")
        f.write(f"#   Extracellular: {topology.extracellular}\n")
        f.write(f"#   Transmembrane: {topology.transmembrane}\n")
        f.write(f"#   Intracellular: {topology.intracellular}\n")
        f.write(f"#   Alignment residues: {topology.alignment_residues}\n")
        f.write("#\n")
        f.write("# CALCULATION:\n")
        f.write("#   Contact threshold: 4.5 Angstroms\n")
        f.write("#   Clash threshold: 2.0 Angstroms (atom pairs closer than this)\n")
        f.write("#   For each target, model with minimum clashes selected\n")
        f.write("#\n")
        f.write("# COLUMNS:\n")
        f.write("#   rank: Ranking by minimum clashes\n")
        f.write("#   target: Peptide/ligand identifier\n")
        f.write("#   model: ClusPro model filename\n")
        f.write("#   cluster: ClusPro cluster number\n")
        f.write("#   center_score: ClusPro weighted score (kcal/mol)\n")
        f.write("#   clashes: Atom pairs < 2.0 Angstroms\n")
        f.write("#   ec_contacts: Extracellular contacts\n")
        f.write("#   tm_contacts: Transmembrane contacts\n")
        f.write("#   ic_contacts: Intracellular contacts\n")
        f.write("#   ec_pct: Percentage extracellular contacts\n")
        f.write("#   validity_score: Composite score (0-100), higher = more valid\n")
        f.write("#                   Formula: ec_pct - (clashes*5) - (tm*2) - (ic*3)\n")
        f.write("#\n")
        f.write("# =============================================================================\n")

        # Write CSV data
        writer = csv.writer(f)
        writer.writerow([
            "rank", "target", "model", "cluster", "center_score",
            "clashes", "ec_contacts", "tm_contacts", "ic_contacts", "ec_pct", "validity_score"
        ])

        for i, r in enumerate(results, 1):
            if r.error is None:
                writer.writerow([
                    i, r.target, r.model, r.cluster or "N/A",
                    r.center_score or "N/A", r.clashes,
                    r.ec_contacts, r.tm_contacts, r.ic_contacts, r.ec_pct, r.validity_score
                ])

    logger.info(f"Results written to: {csv_path}")
