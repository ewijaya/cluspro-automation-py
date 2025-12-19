"""
ClusPro Automation - Python tool for automating ClusPro protein docking web server.

This package provides:
- Job submission automation
- Queue monitoring
- Results parsing
- Download and extraction of docking results
- File organization utilities
- Docking validation (optional, requires biopython and scipy)
- Authentication (guest or account login)

Example usage:
    from cluspro import submit_job, get_finished_jobs, download_batch

    # Guest mode (default)
    submit_job("my-job", "receptor.pdb", "ligand.pdb")

    # With account credentials
    from cluspro import get_credentials, Credentials
    creds = get_credentials()  # From env vars or config
    submit_job("my-job", "receptor.pdb", "ligand.pdb", credentials=creds)

    # Validation (requires: pip install cluspro-automation-py[validate])
    from cluspro.validate import validate_docking, load_topology_from_json
"""

__version__ = "0.4.0"
__author__ = "E Wijaya"

from cluspro.auth import (
    AuthenticationError,
    Credentials,
    CredentialSource,
    get_credentials,
    has_credentials,
)
from cluspro.browser import authenticate, create_browser
from cluspro.database import Job, JobDatabase, JobStatus
from cluspro.download import download_batch, download_results
from cluspro.organize import organize_results
from cluspro.queue import get_queue_status
from cluspro.results import get_finished_jobs
from cluspro.retry import retry_browser, retry_download, with_retry
from cluspro.submit import submit_batch, submit_job
from cluspro.utils import expand_sequences, group_sequences

__all__ = [
    # Authentication
    "AuthenticationError",
    "Credentials",
    "CredentialSource",
    "get_credentials",
    "has_credentials",
    # Browser
    "create_browser",
    "authenticate",
    # Submission
    "submit_job",
    "submit_batch",
    # Queue
    "get_queue_status",
    # Results
    "get_finished_jobs",
    "expand_sequences",
    "group_sequences",
    # Download
    "download_results",
    "download_batch",
    # Organization
    "organize_results",
    # Database
    "JobDatabase",
    "JobStatus",
    "Job",
    # Retry
    "retry_browser",
    "retry_download",
    "with_retry",
]

# Optional: Validation module (requires biopython, scipy)
# Import separately: from cluspro.validate import validate_docking, load_topology_from_json
