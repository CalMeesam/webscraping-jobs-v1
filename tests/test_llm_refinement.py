"""Unit tests for LLM refinement stub scaffolding, bounding, and structural preservation."""

import pytest
from app.models.normalized_job import NormalizedJob
from app.models.request_models import ExtractionRequest
from app.refinement.llm_refiner import LLMOutputRefinerStub


@pytest.mark.asyncio
async def test_llm_refiner_stub_execution():
    """Test placeholder stub execution on normalized jobs."""
    refiner = LLMOutputRefinerStub()
    jobs = [
        NormalizedJob(
            title="Senior Developer",
            description="Build cloud services",
            source="test",
        )
    ]
    refined_jobs, count, failed = await refiner.refine_jobs(jobs)
    assert count == 1
    assert failed == 0
    assert refined_jobs[0].description_refined == "Build cloud services"
    assert refined_jobs[0].title == "Senior Developer"


@pytest.mark.asyncio
async def test_llm_refiner_stub_fallback_on_error():
    """Test placeholder stub fallback when forced to fail."""
    refiner = LLMOutputRefinerStub(force_failure=True)
    jobs = [
        NormalizedJob(
            title="Staff Developer",
            description="Original description text",
            source="test",
        )
    ]
    refined_jobs, count, failed = await refiner.refine_jobs(jobs)
    assert count == 0
    assert failed == 1
    assert refined_jobs[0].description == "Original description text"
    assert refined_jobs[0].description_refined is None


def test_extraction_request_refine_flag_default():
    """Test that refine_with_llm defaults to False on ExtractionRequest."""
    req = ExtractionRequest(url="https://careers.example.com")
    assert req.refine_with_llm is False
