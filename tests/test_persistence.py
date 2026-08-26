"""Unit tests for extraction persistence and diff calculations."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.models.normalized_job import NormalizedJob
from app.db.database import get_db_session, init_db
from app.db.models import ExtractionRun, JobSnapshot
from app.db.repository import (
    compute_customer_diff,
    get_customer_history,
    save_extraction_run,
)


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Fixture providing a temporary SQLite database file path."""
    db_file = tmp_path / "test_extraction_history.db"
    init_db(db_file)
    return db_file


def test_db_initialization(test_db_path: Path):
    """Confirm database tables are created correctly on first run."""
    assert test_db_path.exists()

    with get_db_session(test_db_path) as session:
        runs = session.query(ExtractionRun).all()
        assert len(runs) == 0

        snapshots = session.query(JobSnapshot).all()
        assert len(snapshots) == 0


def test_first_run_baseline(test_db_path: Path):
    """Confirm first-run baseline case returns has_previous_run = False."""
    customer_id = "test-corp"

    # Before any run
    diff_empty = compute_customer_diff(customer_id, db_path=test_db_path)
    assert diff_empty["has_previous_run"] is False
    assert diff_empty["previous_run_id"] is None

    # First run
    job1 = NormalizedJob(
        id="JOB-101",
        title="Software Engineer",
        location="San Francisco, CA",
        job_url="https://testcorp.com/jobs/101",
        source="testcorp",
    )
    save_extraction_run(
        customer_id=customer_id,
        career_link_url="https://testcorp.com/careers",
        status="success",
        strategy_used="test_api",
        jobs_found_count=1,
        jobs_returned_count=1,
        jobs=[job1],
        db_path=test_db_path,
    )

    diff_after_first = compute_customer_diff(customer_id, db_path=test_db_path)
    assert diff_after_first["has_previous_run"] is False
    assert diff_after_first["message"] == "Baseline run, no comparison available"


def test_diff_normal_new_removed_unchanged(test_db_path: Path):
    """Test normal diff with new, removed, and unchanged jobs present."""
    customer_id = "acme-corp"
    url = "https://acme.com/careers"

    # Run 1: Jobs 1, 2, 3
    job1 = NormalizedJob(id="J1", title="Backend Engineer", job_url="https://acme.com/j1", source="acme")
    job2 = NormalizedJob(id="J2", title="Frontend Engineer", job_url="https://acme.com/j2", source="acme")
    job3 = NormalizedJob(id="J3", title="Product Manager", job_url="https://acme.com/j3", source="acme")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="acme_api",
        jobs_found_count=3,
        jobs_returned_count=3,
        jobs=[job1, job2, job3],
        db_path=test_db_path,
    )

    # Run 2: Jobs 2, 3 (unchanged), Job 4 (new). Job 1 removed!
    job4 = NormalizedJob(id="J4", title="Data Scientist", job_url="https://acme.com/j4", source="acme")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="acme_api",
        jobs_found_count=3,
        jobs_returned_count=3,
        jobs=[job2, job3, job4],
        db_path=test_db_path,
    )

    diff = compute_customer_diff(customer_id, db_path=test_db_path)

    assert diff["has_previous_run"] is True
    assert diff["new_jobs_count"] == 1
    assert diff["removed_jobs_count"] == 1
    assert diff["unchanged_jobs_count"] == 2

    assert diff["new_job_keys"] == ["id:J4"]
    assert diff["removed_job_keys"] == ["id:J1"]
    assert sorted(diff["unchanged_job_keys"]) == ["id:J2", "id:J3"]


def test_diff_no_changes(test_db_path: Path):
    """Test diff calculation when nothing changes between two runs."""
    customer_id = "stable-corp"
    url = "https://stable.com/careers"

    job1 = NormalizedJob(id="ST-1", title="DevOps Engineer", job_url="https://stable.com/1", source="stable")
    job2 = NormalizedJob(id="ST-2", title="QA Engineer", job_url="https://stable.com/2", source="stable")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="stable_api",
        jobs_found_count=2,
        jobs_returned_count=2,
        jobs=[job1, job2],
        db_path=test_db_path,
    )

    # Run 2 identical
    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="stable_api",
        jobs_found_count=2,
        jobs_returned_count=2,
        jobs=[job1, job2],
        db_path=test_db_path,
    )

    diff = compute_customer_diff(customer_id, db_path=test_db_path)

    assert diff["has_previous_run"] is True
    assert diff["new_jobs_count"] == 0
    assert diff["removed_jobs_count"] == 0
    assert diff["unchanged_jobs_count"] == 2


def test_diff_all_changed(test_db_path: Path):
    """Test diff calculation when all jobs are completely replaced."""
    customer_id = "dynamic-corp"
    url = "https://dynamic.com/careers"

    # Run 1: Jobs A, B
    jobA = NormalizedJob(id="A", title="Role A", job_url="https://dynamic.com/a", source="dynamic")
    jobB = NormalizedJob(id="B", title="Role B", job_url="https://dynamic.com/b", source="dynamic")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="dynamic_api",
        jobs_found_count=2,
        jobs_returned_count=2,
        jobs=[jobA, jobB],
        db_path=test_db_path,
    )

    # Run 2: Jobs C, D
    jobC = NormalizedJob(id="C", title="Role C", job_url="https://dynamic.com/c", source="dynamic")
    jobD = NormalizedJob(id="D", title="Role D", job_url="https://dynamic.com/d", source="dynamic")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url=url,
        status="success",
        strategy_used="dynamic_api",
        jobs_found_count=2,
        jobs_returned_count=2,
        jobs=[jobC, jobD],
        db_path=test_db_path,
    )

    diff = compute_customer_diff(customer_id, db_path=test_db_path)

    assert diff["has_previous_run"] is True
    assert diff["new_jobs_count"] == 2
    assert diff["removed_jobs_count"] == 2
    assert diff["unchanged_jobs_count"] == 0
    assert sorted(diff["new_job_keys"]) == ["id:C", "id:D"]
    assert sorted(diff["removed_job_keys"]) == ["id:A", "id:B"]


def test_customer_history_api(test_db_path: Path, monkeypatch):
    """Test GET /customers/{customer_id}/history API endpoint."""
    monkeypatch.setattr("app.db.repository.get_db_session", lambda db_path=None: get_db_session(test_db_path))
    monkeypatch.setattr("app.db.repository.init_db", lambda db_path=None: init_db(test_db_path))

    client = TestClient(app)

    customer_id = "cisco"
    job = NormalizedJob(id="2015955", title="Consulting Engineer", job_url="https://careers.cisco.com/job/2015955", source="cisco")

    save_extraction_run(
        customer_id=customer_id,
        career_link_url="https://careers.cisco.com/global/en/search-results",
        status="success",
        strategy_used="static_html",
        jobs_found_count=1,
        jobs_returned_count=1,
        jobs=[job],
        db_path=test_db_path,
    )

    response = client.get(f"/customers/{customer_id}/history")
    assert response.status_code == 200

    data = response.json()
    assert data["customer_id"] == customer_id
    assert data["total_runs"] == 1
    assert len(data["runs"]) == 1
    assert data["diff_summary"]["has_previous_run"] is False
