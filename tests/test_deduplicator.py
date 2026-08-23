"""Unit tests for Deduplicator."""

from app.models.normalized_job import NormalizedJob
from app.processing.deduplicator import Deduplicator


def test_deduplication_priority_rules():
    jobs = [
        # Match by ID
        NormalizedJob(id="101", title="Backend Engineer", job_url="https://a.com/1", source="a"),
        NormalizedJob(id="101", title="Backend Engineer (Duplicate)", job_url="https://a.com/2", source="a"),
        # Match by Job URL
        NormalizedJob(id="102", title="Frontend Engineer", job_url="https://a.com/frontend/", source="a"),
        NormalizedJob(id="103", title="Frontend Engineer", job_url="https://a.com/frontend", source="a"),
        # Match by Composite Fingerprint (no ID, no URL)
        NormalizedJob(title="DevOps Engineer", location="Remote", department="Infra", source="a"),
        NormalizedJob(title="DevOps Engineer", location="Remote", department="Infra", source="a"),
        # Distinct Job
        NormalizedJob(id="104", title="QA Lead", job_url="https://a.com/qa", source="a"),
    ]

    deduplicator = Deduplicator()
    result = deduplicator.remove_duplicates(jobs)

    assert len(result) == 4
    titles = [j.title for j in result]
    assert "Backend Engineer" in titles
    assert "Frontend Engineer" in titles
    assert "DevOps Engineer" in titles
    assert "QA Lead" in titles


def test_composite_fingerprint_fallback_specifically():
    """
    Specifically tests the composite fingerprint fallback path:
    - Jobs with NO source_id, NO job_url, and NO application_url must merge
      if title, location, and department match.
    - Jobs with distinct source_ids sharing title, location, and department
      must NOT be merged by composite fingerprint.
    """
    deduplicator = Deduplicator()

    # Case 1: Pure composite fingerprint match (no IDs, no URLs)
    job_a = NormalizedJob(
        id=None,
        title="  Senior   Backend Engineer ",
        location=" San Francisco, CA ",
        department=" Core Systems ",
        job_url=None,
        application_url=None,
        source="acme",
    )
    job_b = NormalizedJob(
        id=None,
        title="Senior Backend Engineer",
        location="San Francisco, CA",
        department="Core Systems",
        job_url=None,
        application_url=None,
        source="acme",
    )

    res_no_ids = deduplicator.remove_duplicates([job_a, job_b])
    assert len(res_no_ids) == 1
    assert res_no_ids[0].title == "  Senior   Backend Engineer "

    # Case 2: Distinct source_ids must NOT be merged by composite fingerprint
    job_c1 = NormalizedJob(
        id="REQ-001",
        title="Software Engineer",
        location="Remote",
        department="Engineering",
        source="acme",
    )
    job_c2 = NormalizedJob(
        id="REQ-002",
        title="Software Engineer",
        location="Remote",
        department="Engineering",
        source="acme",
    )

    res_with_ids = deduplicator.remove_duplicates([job_c1, job_c2])
    assert len(res_with_ids) == 2
    assert {j.id for j in res_with_ids} == {"REQ-001", "REQ-002"}
