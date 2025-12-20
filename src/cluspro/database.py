"""
Job state persistence module for ClusPro automation.

Provides SQLite-based storage for tracking job submissions,
status changes, and enabling batch operation resumption.
"""

import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterator

from cluspro.utils import resolve_path

logger = logging.getLogger(__name__)

# Default database location
DEFAULT_DB_PATH = Path.home() / ".cluspro" / "jobs.db"


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    """Job record dataclass."""

    id: int | None
    job_name: str
    cluspro_job_id: int | None
    status: JobStatus
    receptor_pdb: str
    ligand_pdb: str
    server: str
    submitted_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    batch_id: str | None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "job_name": self.job_name,
            "cluspro_job_id": self.cluspro_job_id,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "receptor_pdb": self.receptor_pdb,
            "ligand_pdb": self.ligand_pdb,
            "server": self.server,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "batch_id": self.batch_id,
        }


class JobDatabase:
    """
    SQLite database for job state persistence.

    Provides methods for creating, updating, and querying job records.
    Enables resumption of interrupted batch operations.

    Example:
        >>> db = JobDatabase()
        >>> job = db.create_job("test-job", "receptor.pdb", "ligand.pdb")
        >>> db.update_status(job.id, JobStatus.SUBMITTED, cluspro_job_id=12345)
        >>> pending = db.get_pending_jobs()
    """

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default: ~/.cluspro/jobs.db)
        """
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        self.db_path = resolve_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    cluspro_job_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'pending',
                    receptor_pdb TEXT NOT NULL,
                    ligand_pdb TEXT NOT NULL,
                    server TEXT DEFAULT 'gpu',
                    submitted_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    batch_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_batch_id ON jobs(batch_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_cluspro_id ON jobs(cluspro_job_id)
            """)

            logger.debug(f"Database initialized at: {self.db_path}")

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager for database connections."""
        conn = sqlite3.connect(
            self.db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_job(
        self,
        job_name: str,
        receptor_pdb: str,
        ligand_pdb: str,
        server: str = "gpu",
        batch_id: str | None = None,
    ) -> Job:
        """
        Create a new job record.

        Args:
            job_name: Unique job identifier
            receptor_pdb: Path to receptor PDB file
            ligand_pdb: Path to ligand PDB file
            server: Server type (gpu/cpu)
            batch_id: Optional batch identifier for grouping jobs

        Returns:
            Created Job record
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO jobs (job_name, receptor_pdb, ligand_pdb, server, batch_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_name, receptor_pdb, ligand_pdb, server, batch_id),
            )
            job_id = cursor.lastrowid
            assert job_id is not None, "Failed to get lastrowid after INSERT"

        logger.debug(f"Created job record: {job_name} (id={job_id})")
        job = self.get_job(job_id)
        assert job is not None, f"Failed to retrieve job after creation: {job_id}"
        return job

    def get_job(self, job_id: int) -> Job | None:
        """Get job by ID."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

        return self._row_to_job(row) if row else None

    def get_job_by_name(self, job_name: str) -> Job | None:
        """Get job by name."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_name = ?", (job_name,)).fetchone()

        return self._row_to_job(row) if row else None

    def get_job_by_cluspro_id(self, cluspro_job_id: int) -> Job | None:
        """Get job by ClusPro job ID."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE cluspro_job_id = ?", (cluspro_job_id,)
            ).fetchone()

        return self._row_to_job(row) if row else None

    def update_status(
        self,
        job_id: int,
        status: JobStatus,
        cluspro_job_id: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Update job status.

        Args:
            job_id: Database job ID
            status: New status
            cluspro_job_id: ClusPro job ID (if captured)
            error_message: Error message (if failed)
        """
        now = datetime.now()

        with self._connection() as conn:
            if status == JobStatus.SUBMITTED:
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, cluspro_job_id = ?, submitted_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status.value, cluspro_job_id, now, now, job_id),
                )
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                conn.execute(
                    """
                    UPDATE jobs
                    SET status = ?, completed_at = ?, error_message = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status.value, now, error_message, now, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?
                    """,
                    (status.value, now, job_id),
                )

        logger.debug(f"Updated job {job_id} status to: {status.value}")

    def get_pending_jobs(self, batch_id: str | None = None) -> list[Job]:
        """Get all pending jobs, optionally filtered by batch."""
        with self._connection() as conn:
            if batch_id:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = 'pending' AND batch_id = ?",
                    (batch_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs WHERE status = 'pending'").fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_failed_jobs(self, batch_id: str | None = None) -> list[Job]:
        """Get all failed jobs for retry."""
        with self._connection() as conn:
            if batch_id:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = 'failed' AND batch_id = ?",
                    (batch_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs WHERE status = 'failed'").fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_jobs_by_batch(self, batch_id: str) -> list[Job]:
        """Get all jobs in a batch."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE batch_id = ? ORDER BY id",
                (batch_id,),
            ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_all_jobs(
        self,
        status: JobStatus | None = None,
        limit: int = 100,
    ) -> list[Job]:
        """Get all jobs with optional status filter."""
        with self._connection() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY id DESC LIMIT ?",
                    (status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def get_batch_summary(self, batch_id: str) -> dict:
        """Get summary statistics for a batch."""
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'submitted' THEN 1 ELSE 0 END) as submitted,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM jobs WHERE batch_id = ?
                """,
                (batch_id,),
            ).fetchone()

        return dict(row)

    def delete_job(self, job_id: int) -> bool:
        """Delete a job record."""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            return cursor.rowcount > 0

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert database row to Job object."""
        return Job(
            id=row["id"],
            job_name=row["job_name"],
            cluspro_job_id=row["cluspro_job_id"],
            status=JobStatus(row["status"]),
            receptor_pdb=row["receptor_pdb"],
            ligand_pdb=row["ligand_pdb"],
            server=row["server"],
            submitted_at=row["submitted_at"],
            completed_at=row["completed_at"],
            error_message=row["error_message"],
            batch_id=row["batch_id"],
        )


__all__ = [
    "JobDatabase",
    "JobStatus",
    "Job",
    "DEFAULT_DB_PATH",
]
