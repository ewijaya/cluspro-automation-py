"""
ClusPro Automation - Python tool for automating ClusPro protein docking web server.

This package provides:
- Job submission automation
- Queue monitoring
- Results parsing
- Download and extraction of docking results
- File organization utilities

Example usage:
    from cluspro import ClusProClient

    client = ClusProClient()
    client.submit_job("my-job", "receptor.pdb", "ligand.pdb")
    client.download_job(job_id=123456, download_pdb=True)
"""

__version__ = "0.1.0"
__author__ = "E Wijaya"

from cluspro.browser import create_browser
from cluspro.submit import submit_job, submit_batch
from cluspro.queue import get_queue_status
from cluspro.results import get_finished_jobs, expand_sequences, group_sequences
from cluspro.download import download_results, download_batch
from cluspro.organize import organize_results
from cluspro.database import JobDatabase, JobStatus, Job
from cluspro.retry import retry_browser, retry_download, with_retry

__all__ = [
    # Browser
    "create_browser",
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
