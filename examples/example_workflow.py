#!/usr/bin/env python3
"""
Example workflow demonstrating the ClusPro automation package.

This script shows how to:
1. Submit docking jobs
2. Monitor queue and results
3. Download completed results
4. Organize output files
"""

import time
from pathlib import Path

import pandas as pd

# Import from the cluspro package
from cluspro import (
    submit_job,
    submit_batch,
    get_queue_status,
    get_finished_jobs,
    download_results,
    download_batch,
    organize_results,
    expand_sequences,
    group_sequences,
)


def example_single_submission():
    """Example: Submit a single docking job."""
    print("\n=== Single Job Submission ===\n")

    # Replace with actual file paths
    receptor_pdb = "/path/to/your/receptor.pdb"
    ligand_pdb = "/path/to/your/ligand.pdb"

    # Check if files exist (skip if not)
    if not Path(receptor_pdb).exists():
        print("Skipping: Example files don't exist")
        print("Replace paths with actual PDB files to run this example")
        return

    job_id = submit_job(
        job_name="example-dock-1",
        receptor_pdb=receptor_pdb,
        ligand_pdb=ligand_pdb,
        server="gpu",
        headless=True,
    )

    print(f"Job submitted! ID: {job_id}")


def example_batch_submission():
    """Example: Submit multiple jobs from DataFrame."""
    print("\n=== Batch Job Submission ===\n")

    # Create a DataFrame with job specifications
    jobs = pd.DataFrame(
        {
            "job_name": ["batch-job-1", "batch-job-2", "batch-job-3"],
            "receptor_pdb": [
                "/path/to/receptor.pdb",
                "/path/to/receptor.pdb",
                "/path/to/receptor.pdb",
            ],
            "ligand_pdb": [
                "/path/to/ligand1.pdb",
                "/path/to/ligand2.pdb",
                "/path/to/ligand3.pdb",
            ],
            "server": ["gpu", "gpu", "gpu"],
        }
    )

    print("Jobs to submit:")
    print(jobs)

    # In dry run mode, just validate
    from cluspro.submit import dry_run

    validation = dry_run(jobs, output=True)
    print(f"\nValid jobs: {validation['valid'].sum()}/{len(validation)}")


def example_check_queue():
    """Example: Check job queue status."""
    print("\n=== Queue Status ===\n")

    df = get_queue_status(filter_pattern="batch-.*", headless=True)

    if df.empty:
        print("No matching jobs in queue")
    else:
        print(f"Found {len(df)} jobs in queue:")
        print(df)


def example_get_results():
    """Example: Get finished job results."""
    print("\n=== Finished Jobs ===\n")

    df = get_finished_jobs(filter_pattern="batch-.*", max_pages=5, headless=True)

    if df.empty:
        print("No finished jobs found")
    else:
        print(f"Found {len(df)} finished jobs:")
        print(df[["job_name", "job_id", "status"]])

        # Get compressed job IDs
        if "job_id" in df.columns:
            job_ids = df["job_id"].dropna().astype(int).tolist()
            compressed = group_sequences(job_ids)
            print(f"\nCompressed job IDs: {compressed}")


def example_download_results():
    """Example: Download job results."""
    print("\n=== Download Results ===\n")

    # Single job download
    job_id = 1154309  # Replace with actual job ID

    print(f"Downloading job {job_id}...")
    print("(This would download if job exists)")

    # Batch download example
    job_ids = "1154309:1154312"
    print(f"\nBatch download: {job_ids}")
    print(f"Expanded: {expand_sequences(job_ids)}")


def example_organize_results():
    """Example: Organize downloaded results."""
    print("\n=== Organize Results ===\n")

    # Create mapping
    mapping = pd.DataFrame(
        {
            "job_name": ["batch-job-1", "batch-job-2", "batch-job-3"],
            "peptide_name": ["peptideA", "peptideB", "peptideC"],
            "receptor_name": ["receptorX", "receptorX", "receptorY"],
        }
    )

    print("Organization mapping:")
    print(mapping)

    print("\nNew directory names would be:")
    for _, row in mapping.iterrows():
        new_name = f"{row['peptide_name']}_v_{row['receptor_name']}"
        print(f"  {row['job_name']} -> {new_name}")


def example_sequence_utilities():
    """Example: Sequence compression/expansion utilities."""
    print("\n=== Sequence Utilities ===\n")

    # Expand compressed notation
    compressed = "1154309:1154312,1154315,1154320:1154322"
    expanded = expand_sequences(compressed)
    print(f"Expand '{compressed}':")
    print(f"  -> {expanded}")

    # Compress list of IDs
    ids = [1154309, 1154310, 1154311, 1154312, 1154315, 1154320, 1154321, 1154322]
    recompressed = group_sequences(ids)
    print(f"\nCompress {ids}:")
    print(f"  -> '{recompressed}'")


def main():
    """Run all examples."""
    print("=" * 60)
    print("ClusPro Automation - Example Workflow")
    print("=" * 60)

    # These examples demonstrate the API without actually connecting
    example_sequence_utilities()
    example_batch_submission()
    example_download_results()
    example_organize_results()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)

    # Uncomment these to run actual operations:
    # example_single_submission()
    # example_check_queue()
    # example_get_results()


if __name__ == "__main__":
    main()
