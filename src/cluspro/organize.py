"""
File organization module for ClusPro automation.

Organizes downloaded results into meaningful directory structures.
"""

import logging
import shutil
from pathlib import Path

import pandas as pd

from cluspro.utils import ensure_dir, load_config, resolve_path

logger = logging.getLogger(__name__)


def organize_results(
    job_mapping: pd.DataFrame | dict | list[dict],
    source_dir: str | Path | None = None,
    target_dir: str | Path | None = None,
    include_pdb: bool = True,
    config: dict | None = None,
) -> dict:
    """
    Organize downloaded results into meaningful directory structure.

    Renames directories from job IDs to peptide_v_receptor format.

    Args:
        job_mapping: Mapping of job info. DataFrame or list of dicts with:
            - my_jobname or job_name: Original job identifier (used in source dir)
            - peptide_name: Name of the peptide/ligand
            - receptor_name: Name of the receptor
        source_dir: Directory containing downloaded results (default from config)
        target_dir: Directory for organized results (default from config)
        include_pdb: Whether to copy PDB files (True) or only CSV (False)
        config: Optional configuration dict

    Returns:
        Dict mapping new directory names to their paths

    Example:
        >>> mapping = [
        ...     {"job_name": "bb-1", "peptide_name": "hmgb1.144", "receptor_name": "mLrp1"},
        ...     {"job_name": "bb-2", "peptide_name": "hmgb1.144", "receptor_name": "hLrp1"},
        ... ]
        >>> results = organize_results(mapping, include_pdb=True)
    """
    if config is None:
        config = load_config()

    paths = config.get("paths", {})

    if source_dir is None:
        source_dir = paths.get("output_dir", "~/Desktop/ClusPro_results")
    if target_dir is None:
        target_dir = paths.get("organized_dir", "~/Desktop/ClusPro_results/full_names")

    source_path = resolve_path(source_dir)
    target_path = ensure_dir(target_dir)

    # Convert to DataFrame if needed
    if isinstance(job_mapping, dict):
        job_mapping = [job_mapping]
    if isinstance(job_mapping, list):
        job_mapping = pd.DataFrame(job_mapping)

    # Validate required columns
    required_cols = {"peptide_name", "receptor_name"}
    job_col = None
    for col in ["my_jobname", "job_name", "jobname"]:
        if col in job_mapping.columns:
            job_col = col
            break

    if job_col is None:
        raise ValueError("Missing job name column (my_jobname, job_name, or jobname)")

    missing = required_cols - set(job_mapping.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    results = {}

    for idx, row in job_mapping.iterrows():
        job_name = row[job_col]
        peptide_name = row["peptide_name"]
        receptor_name = row["receptor_name"]

        # Apply receptor name substitutions (matching R behavior)
        receptor_name = apply_receptor_substitutions(receptor_name)

        # Create new directory name
        new_dir_name = f"{peptide_name}_v_{receptor_name}"
        new_dir_path = target_path / new_dir_name

        # Find source directory
        source_job_dir = source_path / job_name

        if not source_job_dir.exists():
            logger.warning(f"Source directory not found: {source_job_dir}")
            results[new_dir_name] = {"status": "error", "error": "Source not found"}
            continue

        try:
            # Create target directory
            new_dir_path.mkdir(parents=True, exist_ok=True)

            if include_pdb:
                # Copy all files
                for item in source_job_dir.iterdir():
                    dest = new_dir_path / item.name
                    if item.is_file():
                        shutil.copy2(str(item), str(dest))
                    elif item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(str(item), str(dest))
                logger.debug(f"Copied all files from {job_name} to {new_dir_name}")
            else:
                # Copy only CSV files
                csv_files = list(source_job_dir.glob("*.csv"))
                for csv_file in csv_files:
                    dest = new_dir_path / csv_file.name
                    shutil.copy2(str(csv_file), str(dest))
                logger.debug(f"Copied CSV files from {job_name} to {new_dir_name}")

            results[new_dir_name] = {"status": "success", "path": str(new_dir_path)}

        except Exception as e:
            logger.error(f"Failed to organize {job_name}: {e}")
            results[new_dir_name] = {"status": "error", "error": str(e)}

    # Summary
    success = sum(1 for r in results.values() if r["status"] == "success")
    failed = len(results) - success
    logger.info(f"Organization complete: {success} successful, {failed} failed")

    return results


def apply_receptor_substitutions(receptor_name: str) -> str:
    """
    Apply standard receptor name substitutions.

    Matches the R code behavior for consistent naming.

    Args:
        receptor_name: Original receptor name

    Returns:
        Substituted receptor name
    """
    substitutions = {
        "mMrgprx2": "rMrgprx2",
        "mEndg": "mEndg_dimer",
    }

    for old, new in substitutions.items():
        receptor_name = receptor_name.replace(old, new)

    return receptor_name


def organize_from_csv(
    csv_path: str | Path,
    source_dir: str | Path | None = None,
    target_dir: str | Path | None = None,
    include_pdb: bool = True,
    config: dict | None = None,
) -> dict:
    """
    Organize results using mapping from CSV file.

    CSV must have columns: job_name (or my_jobname), peptide_name, receptor_name

    Args:
        csv_path: Path to CSV mapping file
        source_dir: Directory containing downloaded results
        target_dir: Directory for organized results
        include_pdb: Whether to include PDB files
        config: Optional configuration dict

    Returns:
        Dict mapping new directory names to their paths

    Example:
        >>> results = organize_from_csv("/path/to/mapping.csv")
    """
    csv_path = resolve_path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    mapping = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(mapping)} entries from {csv_path}")

    return organize_results(
        job_mapping=mapping,
        source_dir=source_dir,
        target_dir=target_dir,
        include_pdb=include_pdb,
        config=config,
    )


def list_organized_results(
    target_dir: str | Path | None = None,
    config: dict | None = None,
) -> pd.DataFrame:
    """
    List all organized result directories.

    Args:
        target_dir: Directory containing organized results
        config: Optional configuration dict

    Returns:
        DataFrame with directory info:
        - name: Directory name
        - path: Full path
        - peptide: Extracted peptide name
        - receptor: Extracted receptor name
        - has_pdb: Whether directory contains PDB files
        - has_csv: Whether directory contains CSV files

    Example:
        >>> df = list_organized_results()
        >>> print(df[["name", "has_pdb", "has_csv"]])
    """
    if config is None:
        config = load_config()

    paths = config.get("paths", {})

    if target_dir is None:
        target_dir = paths.get("organized_dir", "~/Desktop/ClusPro_results/full_names")

    target_path = resolve_path(target_dir)

    if not target_path.exists():
        logger.warning(f"Target directory does not exist: {target_path}")
        return pd.DataFrame()

    results = []

    for item in sorted(target_path.iterdir()):
        if not item.is_dir():
            continue

        name = item.name

        # Parse peptide and receptor from name
        peptide, receptor = None, None
        if "_v_" in name:
            parts = name.split("_v_")
            peptide = parts[0]
            receptor = parts[1] if len(parts) > 1 else None

        # Check for file types
        pdb_files = list(item.glob("*.pdb"))
        csv_files = list(item.glob("*.csv"))

        results.append(
            {
                "name": name,
                "path": str(item),
                "peptide": peptide,
                "receptor": receptor,
                "has_pdb": len(pdb_files) > 0,
                "has_csv": len(csv_files) > 0,
                "pdb_count": len(pdb_files),
                "csv_count": len(csv_files),
            }
        )

    return pd.DataFrame(results)


def cleanup_empty_dirs(
    target_dir: str | Path | None = None,
    config: dict | None = None,
    dry_run: bool = True,
) -> list[str]:
    """
    Remove empty directories from organized results.

    Args:
        target_dir: Directory containing organized results
        config: Optional configuration dict
        dry_run: If True, only report what would be deleted

    Returns:
        List of removed (or would-be-removed) directory paths

    Example:
        >>> # Preview what would be deleted
        >>> cleanup_empty_dirs(dry_run=True)
        >>> # Actually delete
        >>> cleanup_empty_dirs(dry_run=False)
    """
    if config is None:
        config = load_config()

    paths = config.get("paths", {})

    if target_dir is None:
        target_dir = paths.get("organized_dir", "~/Desktop/ClusPro_results/full_names")

    target_path = resolve_path(target_dir)

    if not target_path.exists():
        return []

    removed = []

    for item in target_path.iterdir():
        if not item.is_dir():
            continue

        # Check if directory is empty
        contents = list(item.iterdir())
        if not contents:
            if dry_run:
                logger.info(f"Would remove empty directory: {item}")
            else:
                item.rmdir()
                logger.info(f"Removed empty directory: {item}")
            removed.append(str(item))

    if dry_run and removed:
        logger.info(f"Dry run: {len(removed)} directories would be removed")
    elif removed:
        logger.info(f"Removed {len(removed)} empty directories")

    return removed
