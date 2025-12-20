"""Tests for database module."""

from datetime import datetime

from cluspro.database import Job, JobStatus


class TestJobDatabase:
    """Tests for JobDatabase class."""

    def test_create_job(self, test_db):
        """Test creating a job record."""
        job = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        assert job.id is not None
        assert job.job_name == "test-job"
        assert job.status == JobStatus.PENDING
        assert job.receptor_pdb == "/path/to/receptor.pdb"
        assert job.ligand_pdb == "/path/to/ligand.pdb"

    def test_create_job_with_batch_id(self, test_db):
        """Test creating a job with batch ID."""
        job = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
            batch_id="batch-001",
        )

        assert job.batch_id == "batch-001"

    def test_get_job(self, test_db):
        """Test retrieving a job by ID."""
        created = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        retrieved = test_db.get_job(created.id)

        assert retrieved is not None
        assert retrieved.job_name == "test-job"

    def test_get_job_by_name(self, test_db):
        """Test retrieving a job by name."""
        test_db.create_job(
            job_name="unique-job-name",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        retrieved = test_db.get_job_by_name("unique-job-name")

        assert retrieved is not None
        assert retrieved.job_name == "unique-job-name"

    def test_get_job_not_found(self, test_db):
        """Test retrieving non-existent job."""
        result = test_db.get_job(99999)
        assert result is None

    def test_update_status_submitted(self, test_db):
        """Test updating job status to submitted."""
        job = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        test_db.update_status(job.id, JobStatus.SUBMITTED, cluspro_job_id=12345)

        updated = test_db.get_job(job.id)
        assert updated.status == JobStatus.SUBMITTED
        assert updated.cluspro_job_id == 12345
        assert updated.submitted_at is not None

    def test_update_status_completed(self, test_db):
        """Test updating job status to completed."""
        job = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        test_db.update_status(job.id, JobStatus.COMPLETED)

        updated = test_db.get_job(job.id)
        assert updated.status == JobStatus.COMPLETED
        assert updated.completed_at is not None

    def test_update_status_failed(self, test_db):
        """Test updating job status to failed with error message."""
        job = test_db.create_job(
            job_name="test-job",
            receptor_pdb="/path/to/receptor.pdb",
            ligand_pdb="/path/to/ligand.pdb",
        )

        test_db.update_status(job.id, JobStatus.FAILED, error_message="Test error")

        updated = test_db.get_job(job.id)
        assert updated.status == JobStatus.FAILED
        assert updated.error_message == "Test error"

    def test_get_pending_jobs(self, test_db):
        """Test getting pending jobs."""
        test_db.create_job("job1", "/r.pdb", "/l.pdb", batch_id="batch1")
        test_db.create_job("job2", "/r.pdb", "/l.pdb", batch_id="batch1")

        pending = test_db.get_pending_jobs(batch_id="batch1")

        assert len(pending) == 2

    def test_get_pending_jobs_all(self, test_db):
        """Test getting all pending jobs without batch filter."""
        test_db.create_job("job1", "/r.pdb", "/l.pdb")
        test_db.create_job("job2", "/r.pdb", "/l.pdb")

        pending = test_db.get_pending_jobs()

        assert len(pending) == 2

    def test_get_failed_jobs(self, test_db):
        """Test getting failed jobs."""
        job = test_db.create_job("job1", "/r.pdb", "/l.pdb", batch_id="batch1")
        test_db.update_status(job.id, JobStatus.FAILED)

        failed = test_db.get_failed_jobs(batch_id="batch1")

        assert len(failed) == 1

    def test_get_jobs_by_batch(self, test_db):
        """Test getting jobs by batch ID."""
        test_db.create_job("job1", "/r.pdb", "/l.pdb", batch_id="batch1")
        test_db.create_job("job2", "/r.pdb", "/l.pdb", batch_id="batch1")
        test_db.create_job("job3", "/r.pdb", "/l.pdb", batch_id="batch2")

        batch1_jobs = test_db.get_jobs_by_batch("batch1")

        assert len(batch1_jobs) == 2

    def test_get_all_jobs(self, test_db):
        """Test getting all jobs."""
        test_db.create_job("job1", "/r.pdb", "/l.pdb")
        test_db.create_job("job2", "/r.pdb", "/l.pdb")
        test_db.create_job("job3", "/r.pdb", "/l.pdb")

        all_jobs = test_db.get_all_jobs()

        assert len(all_jobs) == 3

    def test_get_all_jobs_with_status_filter(self, test_db):
        """Test getting jobs with status filter."""
        job1 = test_db.create_job("job1", "/r.pdb", "/l.pdb")
        test_db.create_job("job2", "/r.pdb", "/l.pdb")  # Creates pending job
        test_db.update_status(job1.id, JobStatus.COMPLETED)

        completed = test_db.get_all_jobs(status=JobStatus.COMPLETED)
        pending = test_db.get_all_jobs(status=JobStatus.PENDING)

        assert len(completed) == 1
        assert len(pending) == 1

    def test_get_batch_summary(self, test_db):
        """Test batch summary."""
        job1 = test_db.create_job("job1", "/r.pdb", "/l.pdb", batch_id="batch1")
        test_db.create_job("job2", "/r.pdb", "/l.pdb", batch_id="batch1")  # Creates pending job

        test_db.update_status(job1.id, JobStatus.COMPLETED)

        summary = test_db.get_batch_summary("batch1")

        assert summary["total"] == 2
        assert summary["pending"] == 1
        assert summary["completed"] == 1

    def test_delete_job(self, test_db):
        """Test deleting a job."""
        job = test_db.create_job("job1", "/r.pdb", "/l.pdb")

        result = test_db.delete_job(job.id)
        assert result is True

        deleted = test_db.get_job(job.id)
        assert deleted is None

    def test_delete_nonexistent_job(self, test_db):
        """Test deleting non-existent job."""
        result = test_db.delete_job(99999)
        assert result is False


class TestJob:
    """Tests for Job dataclass."""

    def test_to_dict(self):
        """Test Job.to_dict() method."""
        job = Job(
            id=1,
            job_name="test",
            cluspro_job_id=12345,
            status=JobStatus.COMPLETED,
            receptor_pdb="/r.pdb",
            ligand_pdb="/l.pdb",
            server="gpu",
            submitted_at=datetime(2024, 1, 1, 12, 0),
            completed_at=datetime(2024, 1, 1, 13, 0),
            error_message=None,
            batch_id="batch1",
        )

        d = job.to_dict()

        assert d["job_name"] == "test"
        assert d["status"] == "completed"
        assert d["submitted_at"] == "2024-01-01T12:00:00"
        assert d["completed_at"] == "2024-01-01T13:00:00"

    def test_to_dict_with_none_dates(self):
        """Test Job.to_dict() with None dates."""
        job = Job(
            id=1,
            job_name="test",
            cluspro_job_id=None,
            status=JobStatus.PENDING,
            receptor_pdb="/r.pdb",
            ligand_pdb="/l.pdb",
            server="gpu",
            submitted_at=None,
            completed_at=None,
            error_message=None,
            batch_id=None,
        )

        d = job.to_dict()

        assert d["submitted_at"] is None
        assert d["completed_at"] is None


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.SUBMITTED.value == "submitted"
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"
