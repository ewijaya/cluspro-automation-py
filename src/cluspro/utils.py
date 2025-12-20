"""
Utility functions for ClusPro automation.

Includes configuration loading, sequence compression, and file path helpers.
"""

import logging
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger(__name__)

# Default config locations (in order of precedence)
CONFIG_LOCATIONS = [
    Path.home() / ".cluspro" / "settings.yaml",
    Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml",
]


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Searches for config in:
    1. Provided path
    2. ~/.cluspro/settings.yaml
    3. Package config/settings.yaml

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Configuration dictionary

    Example:
        >>> config = load_config()
        >>> config["cluspro"]["urls"]["home"]
        'https://cluspro.bu.edu/home.php'
    """
    if config_path:
        paths = [Path(config_path)]
    else:
        paths = CONFIG_LOCATIONS

    for path in paths:
        if path.exists():
            logger.debug(f"Loading config from: {path}")
            with open(path) as f:
                return cast(dict[str, Any], yaml.safe_load(f))

    logger.warning("No config file found, using defaults")
    return get_default_config()


def get_default_config() -> dict[str, Any]:
    """Return default configuration values."""
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
            "output_dir": "~/Desktop/ClusPro_results",
            "organized_dir": "~/Desktop/ClusPro_results/full_names",
        },
        "timeouts": {
            "submission_wait": 10,
            "page_load_wait": 3,
            "download_wait": 10,
            "between_jobs": 10,
        },
        "batch": {
            "max_pages_to_parse": 50,
            "jobs_per_chunk": 45,
        },
    }


def expand_sequences(s: str) -> list[int]:
    """
    Expand compressed sequence notation to list of integers.

    Handles:
    - Single numbers: "5" -> [5]
    - Ranges with colon: "1:5" -> [1, 2, 3, 4, 5]
    - Comma-separated: "1,3,5" -> [1, 3, 5]
    - Mixed: "1:3,5,7:9" -> [1, 2, 3, 5, 7, 8, 9]

    Args:
        s: Compressed sequence string

    Returns:
        List of integers

    Example:
        >>> expand_sequences("958743:958745,958747:958748,958750")
        [958743, 958744, 958745, 958747, 958748, 958750]
    """
    if not s or not s.strip():
        return []

    result: list[int] = []
    parts = s.strip().split(",")

    for part in parts:
        part = part.strip()
        if not part:
            continue

        if ":" in part:
            # Range notation
            try:
                start, end = part.split(":")
                result.extend(range(int(start), int(end) + 1))
            except ValueError as e:
                logger.warning(f"Invalid range '{part}': {e}")
        else:
            # Single number
            try:
                result.append(int(part))
            except ValueError as e:
                logger.warning(f"Invalid number '{part}': {e}")

    return result


def group_sequences(ids: list[int]) -> str:
    """
    Compress list of integers to sequence notation.

    Inverse of expand_sequences. Groups consecutive numbers into ranges.

    Args:
        ids: List of integers (need not be sorted)

    Returns:
        Compressed string notation

    Example:
        >>> group_sequences([958743, 958744, 958745, 958747, 958748, 958750])
        '958743:958745,958747:958748,958750'
    """
    if not ids:
        return ""

    # Sort and deduplicate
    sorted_ids = sorted(set(ids))

    if len(sorted_ids) == 1:
        return str(sorted_ids[0])

    result = []
    range_start = sorted_ids[0]
    range_end = sorted_ids[0]

    for i in range(1, len(sorted_ids)):
        if sorted_ids[i] == range_end + 1:
            # Continue current range
            range_end = sorted_ids[i]
        else:
            # End current range, start new one
            if range_start == range_end:
                result.append(str(range_start))
            else:
                result.append(f"{range_start}:{range_end}")
            range_start = sorted_ids[i]
            range_end = sorted_ids[i]

    # Add final range
    if range_start == range_end:
        result.append(str(range_start))
    else:
        result.append(f"{range_start}:{range_end}")

    return ",".join(result)


def format_job_ids(job_ids: str, items_per_line: int = 5) -> str:
    """
    Format job ID string with line breaks for readability.

    Args:
        job_ids: Comma-separated job ID string
        items_per_line: Number of items per line

    Returns:
        Formatted string with newlines

    Example:
        >>> format_job_ids("1,2,3,4,5,6,7,8", items_per_line=3)
        '1,2,3,\\n4,5,6,\\n7,8'
    """
    parts = job_ids.split(",")
    lines = []

    for i in range(0, len(parts), items_per_line):
        chunk = parts[i : i + items_per_line]
        lines.append(",".join(chunk))

    return ",\n".join(lines)


def resolve_path(path: str | Path) -> Path:
    """
    Resolve path with home directory expansion.

    Args:
        path: Path string or Path object

    Returns:
        Resolved absolute Path

    Example:
        >>> resolve_path("~/Desktop")
        PosixPath('/Users/username/Desktop')
    """
    return Path(path).expanduser().resolve()


def ensure_dir(path: str | Path) -> Path:
    """
    Ensure directory exists, creating if necessary.

    Args:
        path: Directory path

    Returns:
        Path object for the directory

    Example:
        >>> ensure_dir("~/Desktop/output")
        PosixPath('/Users/username/Desktop/output')
    """
    dir_path = resolve_path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """
    Configure logging for the package.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for log output

    Example:
        >>> setup_logging(level="DEBUG", log_file="~/.cluspro/cluspro.log")
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        log_path = resolve_path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)


def validate_pdb_file(file_path: str | Path) -> Path:
    """
    Validate that a PDB file exists and has correct extension.

    Args:
        file_path: Path to PDB file

    Returns:
        Resolved Path object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file doesn't have .pdb extension

    Example:
        >>> validate_pdb_file("/path/to/protein.pdb")
        PosixPath('/path/to/protein.pdb')
    """
    path = resolve_path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDB file not found: {path}")

    if path.suffix.lower() != ".pdb":
        raise ValueError(f"File must have .pdb extension: {path}")

    return path
