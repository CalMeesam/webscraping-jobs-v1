"""Unit tests for Job Normalizer."""

from app.models.raw_job import RawJob
from app.normalization.job_normalizer import JobNormalizer
from app.normalization.location_normalizer import normalize_location


def test_job_normalizer_cleans_fields():
    raw_jobs = [
        RawJob(
            source_id="123",
            title="  Software Engineer   ",
            location="  San Francisco,   CA  ",
            department="  Engineering  ",
            description_html="<p>Build scalable systems.</p>",
            job_url="https://company.com/jobs/123?utm_source=google",
            source_url="https://company.com/careers",
            ats="greenhouse",
        ),
        RawJob(
            title=None,  # Missing title should be dropped
            location="Remote",
        ),
    ]

    normalizer = JobNormalizer()
    normalized = normalizer.normalize(raw_jobs)

    assert len(normalized) == 1
    job = normalized[0]
    assert job.title == "Software Engineer"
    assert job.location is not None and job.location.raw == "San Francisco, CA"
    assert job.department == "Engineering"
    assert job.description == "Build scalable systems."
    assert "utm_source" not in job.job_url
    assert job.source == "company"
    assert job.ats == "greenhouse"


def test_location_normalizer_workday_vs_multi_location():
    # Workday format: 'Country, City'
    loc_workday = normalize_location("India, Bengaluru")
    assert loc_workday is not None
    assert loc_workday.raw == "India, Bengaluru"
    assert loc_workday.country == "India"
    assert loc_workday.city == "Bengaluru"

    # Multi-location bullet delimited: preserve raw, null structured fields
    loc_multi = normalize_location("San Francisco, CA • New York, NY • United States")
    assert loc_multi is not None
    assert loc_multi.raw == "San Francisco, CA • New York, NY • United States"
    assert loc_multi.city is None
    assert loc_multi.state is None
    assert loc_multi.country is None
