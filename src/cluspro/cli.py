"""
Command-line interface for ClusPro automation.

Provides CLI commands for all ClusPro automation operations.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
import pandas as pd

from cluspro.auth import Credentials, get_credentials, has_credentials
from cluspro.utils import (
    expand_sequences,
    format_job_ids,
    group_sequences,
    load_config,
    setup_logging,
)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--guest", is_flag=True, help="Force guest mode (no account login)")
@click.option("--login", is_flag=True, help="Force account login (prompt if needed)")
@click.pass_context
def main(ctx, verbose: bool, quiet: bool, config: Optional[str], guest: bool, login: bool):
    """
    ClusPro Automation CLI - Automate protein docking with ClusPro web server.

    \b
    Authentication:
      By default, uses account login if credentials are available (env vars or config),
      otherwise falls back to guest mode.

      --guest    Force guest mode even if credentials exist
      --login    Force account login (prompts for credentials if not found)

      Set CLUSPRO_USERNAME and CLUSPRO_PASSWORD environment variables,
      or add credentials section to ~/.cluspro/settings.yaml

    \b
    Commands:
      submit      Submit docking jobs
      queue       Check job queue status
      results     Parse completed job results
      download    Download job results
      organize    Organize downloaded files

    \b
    Examples:
      cluspro submit --name test-job -r receptor.pdb -l ligand.pdb
      cluspro --guest queue --pattern "bb-*"
      cluspro --login results --pattern "pad-*" --output job_ids.txt
      cluspro download --ids "1154309:1154320" --pdb
    """
    ctx.ensure_object(dict)

    # Validate mutually exclusive flags
    if guest and login:
        raise click.UsageError("Cannot use both --guest and --login flags")

    # Setup logging
    if quiet:
        level = "ERROR"
    elif verbose:
        level = "DEBUG"
    else:
        level = "INFO"

    setup_logging(level=level)

    # Load config
    cfg = load_config(config)
    ctx.obj["config"] = cfg
    ctx.obj["verbose"] = verbose
    ctx.obj["force_guest"] = guest

    # Handle credentials
    if guest:
        # Guest mode forced, no credentials needed
        ctx.obj["credentials"] = None
    elif login:
        # Account login forced, get credentials (prompt if needed)
        creds = get_credentials(config=cfg, interactive=True)
        if creds is None:
            raise click.ClickException(
                "No credentials available. Set CLUSPRO_USERNAME and CLUSPRO_PASSWORD "
                "environment variables, or add credentials section to config file."
            )
        ctx.obj["credentials"] = creds
    else:
        # Auto mode: try to get credentials without prompting
        ctx.obj["credentials"] = get_credentials(config=cfg, interactive=False)


# ============================================================================
# Submit Commands
# ============================================================================


@main.command()
@click.option("-n", "--name", required=True, help="Job name")
@click.option("-r", "--receptor", required=True, type=click.Path(exists=True), help="Receptor PDB file")
@click.option("-l", "--ligand", required=True, type=click.Path(exists=True), help="Ligand PDB file")
@click.option("-s", "--server", default="gpu", type=click.Choice(["gpu", "cpu"]), help="Server type")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.pass_context
def submit(ctx, name: str, receptor: str, ligand: str, server: str, no_headless: bool):
    """
    Submit a single docking job to ClusPro.

    \b
    Example:
      cluspro submit -n my-job -r receptor.pdb -l ligand.pdb
    """
    from cluspro.submit import submit_job

    try:
        job_id = submit_job(
            job_name=name,
            receptor_pdb=receptor,
            ligand_pdb=ligand,
            server=server,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )
        click.echo(f"Job '{name}' submitted successfully")
        if job_id:
            click.echo(f"Job ID: {job_id}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("submit-batch")
@click.option("-i", "--input", "input_file", required=True, type=click.Path(exists=True), help="CSV file with jobs")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.option("--stop-on-error", is_flag=True, help="Stop on first error")
@click.option("-o", "--output", type=click.Path(), help="Output CSV for results")
@click.pass_context
def submit_batch_cmd(ctx, input_file: str, no_headless: bool, stop_on_error: bool, output: Optional[str]):
    """
    Submit multiple jobs from a CSV file.

    \b
    CSV format: job_name,receptor_pdb,ligand_pdb[,server]

    \b
    Example:
      cluspro submit-batch -i jobs.csv -o results.csv
    """
    from cluspro.submit import submit_from_csv

    try:
        results = submit_from_csv(
            csv_path=input_file,
            headless=not no_headless,
            continue_on_error=not stop_on_error,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )

        success = len(results[results["status"] == "success"])
        failed = len(results) - success

        click.echo(f"Submitted: {success} successful, {failed} failed")

        if output:
            results.to_csv(output, index=False)
            click.echo(f"Results saved to: {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("dry-run")
@click.option("-i", "--input", "input_file", required=True, type=click.Path(exists=True), help="CSV file with jobs")
@click.pass_context
def dry_run_cmd(ctx, input_file: str):
    """
    Validate jobs without submitting.

    \b
    Example:
      cluspro dry-run -i jobs.csv
    """
    from cluspro.submit import dry_run

    try:
        jobs = pd.read_csv(input_file)
        results = dry_run(jobs, output=True)

        valid = len(results[results["valid"]])
        invalid = len(results) - valid

        click.echo(f"\nSummary: {valid} valid, {invalid} invalid")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Queue Commands
# ============================================================================


@main.command()
@click.option("-u", "--user", help="Filter by username")
@click.option("-p", "--pattern", help="Filter by job name pattern (regex)")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.option("-o", "--output", type=click.Path(), help="Output CSV file")
@click.pass_context
def queue(ctx, user: Optional[str], pattern: Optional[str], no_headless: bool, output: Optional[str]):
    """
    Check ClusPro job queue status.

    \b
    Example:
      cluspro queue --user piper --pattern "bb-.*"
    """
    from cluspro.queue import get_queue_status

    try:
        df = get_queue_status(
            filter_user=user,
            filter_pattern=pattern,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )

        if df.empty:
            click.echo("Queue is empty (or no matches found)")
            return

        # Display results
        click.echo(f"\nFound {len(df)} jobs in queue:\n")
        click.echo(df.to_string(index=False))

        if output:
            df.to_csv(output, index=False)
            click.echo(f"\nResults saved to: {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Results Commands
# ============================================================================


@main.command()
@click.option("-p", "--pattern", help="Filter by job name pattern (regex)")
@click.option("--max-pages", default=50, help="Maximum pages to parse")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.option("-o", "--output", type=click.Path(), help="Output file for job IDs")
@click.option("--csv", "output_csv", type=click.Path(), help="Output CSV with full details")
@click.pass_context
def results(
    ctx,
    pattern: Optional[str],
    max_pages: int,
    no_headless: bool,
    output: Optional[str],
    output_csv: Optional[str],
):
    """
    Get completed job results from ClusPro.

    \b
    Example:
      cluspro results --pattern "pad-.*" --output job_ids.txt
    """
    from cluspro.results import get_finished_jobs

    try:
        df = get_finished_jobs(
            filter_pattern=pattern,
            max_pages=max_pages,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )

        if df.empty:
            click.echo("No finished jobs found")
            return

        click.echo(f"\nFound {len(df)} finished jobs:\n")

        # Show summary
        if "job_id" in df.columns:
            job_ids = df["job_id"].dropna().astype(int).tolist()
            compressed = group_sequences(job_ids)
            click.echo(f"Job IDs (compressed): {compressed}\n")

            if output:
                with open(output, "w") as f:
                    f.write(compressed)
                click.echo(f"Job IDs saved to: {output}")

        # Show table
        display_cols = [c for c in ["job_name", "job_id", "status"] if c in df.columns]
        click.echo(df[display_cols].to_string(index=False))

        if output_csv:
            df.to_csv(output_csv, index=False)
            click.echo(f"\nFull results saved to: {output_csv}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("-p", "--pattern", help="Filter by job name pattern (regex)")
@click.option("--max-pages", default=50, help="Maximum pages to parse")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.pass_context
def summary(ctx, pattern: Optional[str], max_pages: int, no_headless: bool):
    """
    Get summary of job results.

    \b
    Example:
      cluspro summary --pattern "bb-.*"
    """
    from cluspro.results import get_results_summary

    try:
        stats = get_results_summary(
            filter_pattern=pattern,
            max_pages=max_pages,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )

        click.echo("\nResults Summary:")
        click.echo(f"  Total jobs:    {stats['total']}")
        click.echo(f"  Finished:      {stats['finished']}")
        click.echo(f"  Running:       {stats['running']}")
        click.echo(f"  Errors:        {stats['error']}")

        if stats["job_ids"]:
            click.echo(f"\nFinished Job IDs: {stats['job_ids']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Download Commands
# ============================================================================


@main.command()
@click.option("--job-id", required=True, type=int, help="ClusPro job ID")
@click.option("-o", "--output-dir", type=click.Path(), help="Output directory")
@click.option("--pdb/--no-pdb", default=True, help="Download PDB files")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.pass_context
def download(ctx, job_id: int, output_dir: Optional[str], pdb: bool, no_headless: bool):
    """
    Download results for a single job.

    \b
    Example:
      cluspro download --job-id 1154309 --pdb
    """
    from cluspro.download import download_results

    try:
        result_path = download_results(
            job_id=job_id,
            output_dir=output_dir,
            download_pdb=pdb,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )
        click.echo(f"Results saved to: {result_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("download-batch")
@click.option("--ids", required=True, help="Job IDs (e.g., '1154309:1154320,1154325')")
@click.option("-o", "--output-dir", type=click.Path(), help="Output directory")
@click.option("--pdb/--no-pdb", default=True, help="Download PDB files")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.option("--stop-on-error", is_flag=True, help="Stop on first error")
@click.pass_context
def download_batch_cmd(
    ctx, ids: str, output_dir: Optional[str], pdb: bool, no_headless: bool, stop_on_error: bool
):
    """
    Download results for multiple jobs.

    \b
    Example:
      cluspro download-batch --ids "1154309:1154320" --pdb
    """
    from cluspro.download import download_batch

    try:
        results = download_batch(
            job_ids=ids,
            output_dir=output_dir,
            download_pdb=pdb,
            continue_on_error=not stop_on_error,
            headless=not no_headless,
            config=ctx.obj["config"],
            credentials=ctx.obj.get("credentials"),
            force_guest=ctx.obj.get("force_guest", False),
        )

        success = sum(1 for r in results.values() if r["status"] == "success")
        failed = len(results) - success

        click.echo(f"\nDownload complete: {success} successful, {failed} failed")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Organize Commands
# ============================================================================


@main.command()
@click.option("-i", "--input", "mapping_file", required=True, type=click.Path(exists=True), help="CSV mapping file")
@click.option("-s", "--source-dir", type=click.Path(exists=True), help="Source directory")
@click.option("-t", "--target-dir", type=click.Path(), help="Target directory")
@click.option("--pdb/--no-pdb", default=True, help="Include PDB files")
@click.pass_context
def organize(
    ctx,
    mapping_file: str,
    source_dir: Optional[str],
    target_dir: Optional[str],
    pdb: bool,
):
    """
    Organize downloaded results using mapping file.

    \b
    CSV format: job_name,peptide_name,receptor_name

    \b
    Example:
      cluspro organize -i mapping.csv --pdb
    """
    from cluspro.organize import organize_from_csv

    try:
        results = organize_from_csv(
            csv_path=mapping_file,
            source_dir=source_dir,
            target_dir=target_dir,
            include_pdb=pdb,
            config=ctx.obj["config"],
        )

        success = sum(1 for r in results.values() if r["status"] == "success")
        failed = len(results) - success

        click.echo(f"\nOrganization complete: {success} successful, {failed} failed")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("list")
@click.option("-d", "--dir", "target_dir", type=click.Path(exists=True), help="Directory to list")
@click.pass_context
def list_organized(ctx, target_dir: Optional[str]):
    """
    List organized result directories.

    \b
    Example:
      cluspro list
    """
    from cluspro.organize import list_organized_results

    try:
        df = list_organized_results(target_dir=target_dir, config=ctx.obj["config"])

        if df.empty:
            click.echo("No organized results found")
            return

        click.echo(f"\nFound {len(df)} result directories:\n")
        display_cols = ["name", "has_pdb", "has_csv", "pdb_count", "csv_count"]
        click.echo(df[display_cols].to_string(index=False))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ============================================================================
# Utility Commands
# ============================================================================


@main.command()
@click.argument("sequence")
def expand(sequence: str):
    """
    Expand compressed job ID sequence.

    \b
    Example:
      cluspro expand "1154309:1154312,1154315"
    """
    try:
        ids = expand_sequences(sequence)
        click.echo(",".join(str(i) for i in ids))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("ids", nargs=-1, type=int)
def compress(ids: tuple[int, ...]):
    """
    Compress job IDs to sequence notation.

    \b
    Example:
      cluspro compress 1154309 1154310 1154311 1154315
    """
    try:
        compressed = group_sequences(list(ids))
        click.echo(compressed)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def config(ctx):
    """
    Show current configuration.
    """
    import yaml

    click.echo(yaml.dump(ctx.obj["config"], default_flow_style=False))


# ============================================================================
# Jobs Commands (Database Operations)
# ============================================================================


@main.group()
@click.pass_context
def jobs(ctx):
    """
    Manage job records and batch operations.

    \b
    Commands:
      list    List job records from database
      resume  Resume interrupted batch submission
      status  Show batch status summary
    """
    pass


@jobs.command("list")
@click.option("--status", type=click.Choice(["pending", "submitted", "queued", "running", "completed", "failed", "cancelled"]), help="Filter by status")
@click.option("--batch", "batch_id", help="Filter by batch ID")
@click.option("--limit", default=50, help="Maximum records to show")
@click.pass_context
def jobs_list(ctx, status: Optional[str], batch_id: Optional[str], limit: int):
    """
    List job records from database.

    \b
    Example:
      cluspro jobs list --status pending
      cluspro jobs list --batch my-batch-001
    """
    from cluspro.database import JobDatabase, JobStatus

    try:
        db = JobDatabase()

        if batch_id:
            jobs_list = db.get_jobs_by_batch(batch_id)
        elif status:
            jobs_list = db.get_all_jobs(status=JobStatus(status), limit=limit)
        else:
            jobs_list = db.get_all_jobs(limit=limit)

        if not jobs_list:
            click.echo("No jobs found")
            return

        click.echo(f"\nFound {len(jobs_list)} jobs:\n")

        # Format as table
        headers = ["ID", "Name", "ClusPro ID", "Status", "Submitted"]
        widths = [6, 25, 12, 12, 20]

        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
        click.echo(header_line)
        click.echo("-" * len(header_line))

        for job in jobs_list:
            submitted = job.submitted_at.strftime("%Y-%m-%d %H:%M") if job.submitted_at else "-"
            row = [
                str(job.id).ljust(6),
                job.job_name[:25].ljust(25),
                str(job.cluspro_job_id or "-").ljust(12),
                job.status.value.ljust(12),
                submitted.ljust(20),
            ]
            click.echo(" | ".join(row))

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command("resume")
@click.option("--batch", "batch_id", required=True, help="Batch ID to resume")
@click.option("--include-failed", is_flag=True, help="Also retry failed jobs")
@click.option("--no-headless", is_flag=True, help="Show browser window")
@click.pass_context
def jobs_resume(ctx, batch_id: str, include_failed: bool, no_headless: bool):
    """
    Resume an interrupted batch submission.

    \b
    Example:
      cluspro jobs resume --batch my-batch-001
      cluspro jobs resume --batch my-batch-001 --include-failed
    """
    from cluspro.database import JobDatabase, JobStatus
    from cluspro.submit import submit_job

    try:
        db = JobDatabase()

        # Get pending jobs
        pending = db.get_pending_jobs(batch_id=batch_id)

        if include_failed:
            failed = db.get_failed_jobs(batch_id=batch_id)
            pending.extend(failed)

        if not pending:
            click.echo(f"No pending jobs found for batch: {batch_id}")
            return

        click.echo(f"Resuming {len(pending)} jobs from batch: {batch_id}")

        success = 0
        for job in pending:
            try:
                cluspro_id = submit_job(
                    job_name=job.job_name,
                    receptor_pdb=job.receptor_pdb,
                    ligand_pdb=job.ligand_pdb,
                    server=job.server,
                    headless=not no_headless,
                    config=ctx.obj["config"],
                    credentials=ctx.obj.get("credentials"),
                    force_guest=ctx.obj.get("force_guest", False),
                )
                db.update_status(job.id, JobStatus.SUBMITTED, cluspro_job_id=int(cluspro_id) if cluspro_id else None)
                success += 1
                click.echo(f"  Submitted: {job.job_name}")
            except Exception as e:
                db.update_status(job.id, JobStatus.FAILED, error_message=str(e))
                click.echo(f"  Failed: {job.job_name} - {e}", err=True)

        click.echo(f"\nCompleted: {success}/{len(pending)} jobs submitted")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@jobs.command("status")
@click.option("--batch", "batch_id", required=True, help="Batch ID")
@click.pass_context
def jobs_status(ctx, batch_id: str):
    """
    Show batch status summary.

    \b
    Example:
      cluspro jobs status --batch my-batch-001
    """
    from cluspro.database import JobDatabase

    try:
        db = JobDatabase()
        summary = db.get_batch_summary(batch_id)

        click.echo(f"\nBatch: {batch_id}")
        click.echo(f"  Total:     {summary['total']}")
        click.echo(f"  Pending:   {summary['pending']}")
        click.echo(f"  Submitted: {summary['submitted']}")
        click.echo(f"  Completed: {summary['completed']}")
        click.echo(f"  Failed:    {summary['failed']}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
