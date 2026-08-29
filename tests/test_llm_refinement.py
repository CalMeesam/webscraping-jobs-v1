"""Unit tests for LLM Output Refinement, bounding, fallback, and structural preservation."""

import pytest
from app.models.normalized_job import NormalizedJob
from app.models.request_models import ExtractionRequest
from app.refinement.llm_refiner import LLMOutputRefiner


@pytest.mark.asyncio
async def test_llm_refiner_fallback_clean():
    """Test deterministic regex fallback cleaning when LLM API client is not present."""
    refiner = LLMOutputRefiner(api_key=None)
    dirty_text = "<div><p>Senior Developer &amp; Lead</p><br>&nbsp;&nbsp;Build&nbsp;&nbsp;awesome   products.</div>"
    
    clean = refiner.fallback_regex_clean(dirty_text)
    assert "<" not in clean
    assert "&amp;" not in clean
    assert "&nbsp;" not in clean
    assert "Senior Developer & Lead" in clean
    assert "Build awesome products." in clean


@pytest.mark.asyncio
async def test_llm_refiner_bounding_cap():
    """Test that refinement is strictly capped at MAX_LLM_REFINE_JOBS."""
    refiner = LLMOutputRefiner(api_key=None)  # Uses regex fallback
    
    jobs = [
        NormalizedJob(
            title=f"Engineer {i}",
            description=f"<div>Job description {i} &amp; details</div>",
            source="manual",
        )
        for i in range(10)
    ]

    refined_jobs, count, failed = await refiner.refine_jobs(jobs)
    
    assert len(refined_jobs) == 10
    # First 5 jobs (default cap MAX_LLM_REFINE_JOBS=5) should have description_refined set
    for i in range(5):
        assert refined_jobs[i].description_refined is not None
        assert "Engineer" in refined_jobs[i].title  # Structural title preserved
    
    # Jobs beyond cap (6-10) must remain unrefined (description_refined is None)
    for i in range(5, 10):
        assert refined_jobs[i].description_refined is None


@pytest.mark.asyncio
async def test_llm_refiner_preserves_structural_fields():
    """Test that refinement never alters non-description fields."""
    refiner = LLMOutputRefiner(api_key=None)
    
    job = NormalizedJob(
        id="job-123",
        external_job_id="ext-456",
        title="Lead DevOps Specialist",
        location="New York, NY",
        department="Engineering",
        description="<div>Deploy microservices with Kubernetes &amp; Helm.</div>",
        responsibilities=["Maintain CI/CD"],
        requirements=["5+ years Docker"],
        job_url="https://company.com/jobs/123",
        source="greenhouse",
        ats="greenhouse",
    )

    refined_jobs, count, failed = await refiner.refine_jobs([job])
    refined = refined_jobs[0]

    # Verify structural identity fields are 100% byte-for-byte preserved
    assert refined.id == "job-123"
    assert refined.external_job_id == "ext-456"
    assert refined.title == "Lead DevOps Specialist"
    assert refined.location == "New York, NY"
    assert refined.department == "Engineering"
    assert refined.responsibilities == ["Maintain CI/CD"]
    assert refined.requirements == ["5+ years Docker"]
    assert refined.job_url == "https://company.com/jobs/123"
    assert refined.source == "greenhouse"
    assert refined.ats == "greenhouse"

    # Original description is untouched
    assert refined.description == "<div>Deploy microservices with Kubernetes &amp; Helm.</div>"
    # Refined description contains cleaned text
    assert refined.description_refined is not None
    assert "&amp;" not in refined.description_refined


def test_extraction_request_refine_flag_default():
    """Test that refine_with_llm defaults to False on ExtractionRequest."""
    req = ExtractionRequest(url="https://careers.example.com")
    assert req.refine_with_llm is False
