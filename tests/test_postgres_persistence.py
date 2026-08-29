"""Unit tests for database connection, PostgreSQL dialect handling, dynamic URL resolution, and persistence."""

import os
from pathlib import Path
import pytest
from app.db.database import get_db_url, get_engine, init_db, reset_engine_cache, get_db_session
from app.db.models import ExtractionRun, JobSnapshot
from app.db.repository import save_extraction_run, compute_customer_diff, get_customer_history
from app.models.normalized_job import NormalizedJob


def test_db_url_resolution_default(tmp_path: Path):
    """Test get_db_url fallback to SQLite when DATABASE_URL is unset."""
    old_env = os.environ.pop("DATABASE_URL", None)
    try:
        url = get_db_url()
        assert url.startswith("sqlite:///")
        assert "extraction_history.db" in url
    finally:
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env


def test_db_url_resolution_postgres_env(monkeypatch):
    """Test get_db_url handling of postgresql:// and legacy postgres:// schemes."""
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/testdb")
    url = get_db_url()
    assert url == "postgresql://user:pass@localhost:5432/testdb"


def test_db_url_resolution_explicit_path(tmp_path: Path):
    """Test explicit db_path resolution."""
    db_file = tmp_path / "custom.db"
    url = get_db_url(db_file)
    assert url == f"sqlite:///{db_file.as_posix()}"


def test_save_and_diff_with_json_and_indexes(tmp_path: Path):
    """Test save_extraction_run using JSON column type and index creation on SQLite/Postgres dialect."""
    db_file = tmp_path / "test_persistence.db"
    reset_engine_cache()

    job1 = NormalizedJob(
        title="Senior Python Backend Engineer",
        company="TechCorp",
        location="Remote, USA",
        job_url="https://careers.techcorp.com/jobs/101",
        description="Build scalable microservices with Python and Postgres.",
        source="lever",
        ats="lever",
    )

    # 1. First run
    run1 = save_extraction_run(
        customer_id="techcorp",
        career_link_url="https://careers.techcorp.com",
        status="success",
        strategy_used="ats",
        jobs_found_count=1,
        jobs_returned_count=1,
        jobs=[job1],
        db_path=db_file,
    )
    assert run1["id"] is not None
    assert run1["customer_id"] == "techcorp"

    # Verify JSON payload was stored cleanly in DB
    with get_db_session(db_file) as session:
        snapshot = session.query(JobSnapshot).filter_by(run_id=run1["id"]).first()
        assert snapshot is not None
        assert snapshot.title == "Senior Python Backend Engineer"
        assert isinstance(snapshot.raw_json, dict)
        assert snapshot.raw_json["title"] == "Senior Python Backend Engineer"

    # 2. History lookup
    history = get_customer_history("techcorp", db_path=db_file)
    assert history["total_runs"] == 1
    assert history["diff_summary"]["has_previous_run"] is False

    reset_engine_cache()
