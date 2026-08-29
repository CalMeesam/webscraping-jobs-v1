"""Unit tests for run comparison, field-level diff calculation, and comparison CSV export."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.db.database import get_db_session, init_db
from app.db.models import ExtractionRun, JobSnapshot
from app.db.repository import (
    compare_runs,
    compute_field_diffs,
    export_comparison_to_csv,
    save_extraction_run,
)
from app.main import app
from app.models.normalized_job import NormalizedJob, JobLocation
from app.models.response_models import ExtractionResponse, ExtractionMetadata


@pytest.fixture
def temp_db(tmp_path: Path):
    """Fixture providing a clean SQLite test database path."""
    db_file = tmp_path / "test_comparison.db"
    init_db(db_file)
    return db_file


def save_mock_run(customer_id: str, jobs: list[NormalizedJob], db_path: Path) -> dict:
    return save_extraction_run(
        customer_id=customer_id,
        career_link_url="https://example.com/careers",
        status="success",
        strategy_used="ATS API",
        jobs_found_count=len(jobs),
        jobs_returned_count=len(jobs),
        jobs=jobs,
        db_path=db_path,
    )


def test_field_diffs_calculation():
    """Test scalar and list field delta detection."""
    base_job = {
        "title": "Software Engineer",
        "location": "San Francisco, CA",
        "department": "Engineering",
        "skills": ["Python", "SQL"],
        "description": "Base description",
    }
    target_job = {
        "title": "Senior Software Engineer",
        "location": "Remote, US",
        "department": "Engineering",
        "skills": ["Python", "SQL", "FastAPI"],
        "description": "Updated description",
    }

    diffs = compute_field_diffs(base_job, target_job)
    diff_fields = {d["field"]: (d["old_value"], d["new_value"]) for d in diffs}

    assert "title" in diff_fields
    assert diff_fields["title"] == ("Software Engineer", "Senior Software Engineer")
    
    assert "location" in diff_fields
    assert diff_fields["location"] == ("San Francisco, CA", "Remote, US")

    assert "department" not in diff_fields

    assert "skills" in diff_fields
    assert diff_fields["skills"] == ("Python, SQL", "Python, SQL, FastAPI")

    assert "description" in diff_fields
    assert diff_fields["description"] == ("Base description", "Updated description")


def test_compare_runs_added_removed_changed_unchanged(temp_db: Path):
    """Test comprehensive run comparison classifying added, removed, changed, and unchanged jobs."""
    # Run 1: 3 jobs
    # - Job 1: id:101 (will be unchanged)
    # - Job 2: id:102 (will be changed in Run 2)
    # - Job 3: id:103 (will be removed in Run 2)
    job1_r1 = NormalizedJob(id="101", title="DevOps Engineer", location=JobLocation(raw="Austin, TX"), job_url="https://jobs/101", source="ats", ats="greenhouse")
    job2_r1 = NormalizedJob(id="102", title="Backend Developer", location=JobLocation(raw="New York, NY"), skills=["Python"], job_url="https://jobs/102", source="ats", ats="greenhouse")
    job3_r1 = NormalizedJob(id="103", title="QA Lead", location=JobLocation(raw="Chicago, IL"), job_url="https://jobs/103", source="ats", ats="greenhouse")

    run1 = save_mock_run("client-alpha", [job1_r1, job2_r1, job3_r1], db_path=temp_db)

    # Run 2: 3 jobs
    # - Job 1: id:101 (identical)
    # - Job 2: id:102 (title changed to Senior Backend Developer, skills added)
    # - Job 4: id:104 (newly added)
    job1_r2 = NormalizedJob(id="101", title="DevOps Engineer", location=JobLocation(raw="Austin, TX"), job_url="https://jobs/101", source="ats", ats="greenhouse")
    job2_r2 = NormalizedJob(id="102", title="Senior Backend Developer", location=JobLocation(raw="New York, NY"), skills=["Python", "Docker"], job_url="https://jobs/102", source="ats", ats="greenhouse")
    job4_r2 = NormalizedJob(id="104", title="Data Scientist", location=JobLocation(raw="Remote"), job_url="https://jobs/104", source="ats", ats="greenhouse")

    run2 = save_mock_run("client-alpha", [job1_r2, job2_r2, job4_r2], db_path=temp_db)

    comparison = compare_runs(base_run_id=run1["id"], target_run_id=run2["id"], db_path=temp_db)

    summary = comparison["summary"]
    assert summary["added_count"] == 1
    assert summary["removed_count"] == 1
    assert summary["changed_count"] == 1
    assert summary["unchanged_count"] == 1

    # Check Added Job
    assert len(comparison["added_jobs"]) == 1
    assert comparison["added_jobs"][0]["job_identity_key"] == "id:104"
    assert comparison["added_jobs"][0]["title"] == "Data Scientist"

    # Check Removed Job
    assert len(comparison["removed_jobs"]) == 1
    assert comparison["removed_jobs"][0]["job_identity_key"] == "id:103"
    assert comparison["removed_jobs"][0]["title"] == "QA Lead"

    # Check Changed Job
    assert len(comparison["changed_jobs"]) == 1
    changed_job = comparison["changed_jobs"][0]
    assert changed_job["job_identity_key"] == "id:102"
    
    field_keys = {f["field"] for f in changed_job["field_changes"]}
    assert "title" in field_keys
    assert "skills" in field_keys

    # Check Unchanged Job
    assert len(comparison["unchanged_jobs"]) == 1
    assert comparison["unchanged_jobs"][0]["job_identity_key"] == "id:101"


def test_export_comparison_to_csv(temp_db: Path):
    """Test CSV generation from comparison structure."""
    job1 = NormalizedJob(id="101", title="Frontend Engineer", location="Remote", job_url="https://jobs/101", source="ats", ats="greenhouse")
    job2 = NormalizedJob(id="102", title="Designer", location="SF", job_url="https://jobs/102", source="ats", ats="greenhouse")

    run1 = save_mock_run("client-beta", [job1], db_path=temp_db)
    run2 = save_mock_run("client-beta", [job2], db_path=temp_db)

    comparison = compare_runs(base_run_id=run1["id"], target_run_id=run2["id"], db_path=temp_db)
    csv_str = export_comparison_to_csv(comparison)

    assert "Change Type,Job Identity Key,Job Title,Location" in csv_str
    assert "Added,id:102,Designer" in csv_str
    assert "Removed,id:101,Frontend Engineer" in csv_str


def test_comparison_api_endpoints(temp_db: Path, monkeypatch):
    """Test FastAPI GET /runs/{target_id}/compare/{base_id} endpoints."""
    # Ensure routes use test DB
    import app.api.routes as routes
    monkeypatch.setattr(routes, "compare_runs", lambda base_run_id, target_run_id: compare_runs(base_run_id, target_run_id, db_path=temp_db))

    job1 = NormalizedJob(id="A", title="Role A", location="NY", job_url="https://jobs/a", source="ats", ats="greenhouse")
    run1 = save_mock_run("client-gamma", [job1], db_path=temp_db)

    job2 = NormalizedJob(id="B", title="Role B", location="NY", job_url="https://jobs/b", source="ats", ats="greenhouse")
    run2 = save_mock_run("client-gamma", [job2], db_path=temp_db)

    client = TestClient(app)

    # 1. JSON Endpoint
    res = client.get(f"/runs/{run2['id']}/compare/{run1['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["added_count"] == 1
    assert data["summary"]["removed_count"] == 1

    # 2. CSV Endpoint
    csv_res = client.get(f"/runs/{run2['id']}/compare/{run1['id']}/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "Change Type,Job Identity Key" in csv_res.text
    assert f'filename="comparison_run_{run1["id"]}_vs_{run2["id"]}.csv"' in csv_res.headers["content-disposition"]

