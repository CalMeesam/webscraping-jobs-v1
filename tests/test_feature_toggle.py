"""Unit tests for the LLM Refinement feature flag toggle and stub error boundary."""

from pathlib import Path
import pytest
from app.core.features import is_feature_enabled, load_feature_flags
from app.models.extraction_models import ExtractionContext
from app.models.normalized_job import NormalizedJob
from app.models.raw_job import RawJob
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager
from app.refinement.llm_refiner import LLMOutputRefinerStub


def test_feature_flag_disabled_by_default(tmp_path: Path):
    """Test that llm_refinement is disabled by default in features.yaml."""
    config_file = tmp_path / "features.yaml"
    config_file.write_text("llm_refinement:\n  enabled: false\n", encoding="utf-8")
    
    assert is_feature_enabled("llm_refinement", config_path=config_file) is False


def test_feature_flag_enabled(tmp_path: Path):
    """Test that llm_refinement enabled: true is correctly read."""
    config_file = tmp_path / "features.yaml"
    config_file.write_text("llm_refinement:\n  enabled: true\n", encoding="utf-8")
    
    assert is_feature_enabled("llm_refinement", config_path=config_file) is True


@pytest.mark.asyncio
async def test_pipeline_disabled_toggle_never_invokes_refinement(monkeypatch, tmp_path: Path):
    """
    When enabled: false, the refinement function MUST NOT be invoked at all
    (refiner.invoked must remain False).
    """
    config_file = tmp_path / "features.yaml"
    config_file.write_text("llm_refinement:\n  enabled: false\n", encoding="utf-8")

    # Mock features path
    monkeypatch.setattr("app.orchestrator.extraction_manager.is_feature_enabled", lambda feat: False)

    stub_refiner = LLMOutputRefinerStub()
    manager = ExtractionManager(refiner=stub_refiner)

    # Mock discovery & extractor to return a sample raw job
    async def mock_process_url(*args, **kwargs):
        return [RawJob(title="Software Engineer", job_url="https://example.com/jobs/1", description_text="Backend APIs", source="test")]

    manager.process_discovered_url = mock_process_url

    req = ExtractionRequest(url="https://example.com/careers", include_details=False, refine_with_llm=False)
    response = await manager.extract_jobs(req)

    assert len(response.jobs) == 1
    # Stub must NEVER have been invoked
    assert stub_refiner.invoked is False
    assert response.metadata.jobs_llm_refined == 0
    assert response.metadata.jobs_llm_refinement_failed == 0


@pytest.mark.asyncio
async def test_pipeline_enabled_toggle_invokes_refinement(monkeypatch):
    """
    When enabled: true, the refinement function MUST be invoked.
    """
    monkeypatch.setattr("app.orchestrator.extraction_manager.is_feature_enabled", lambda feat: True)

    stub_refiner = LLMOutputRefinerStub()
    manager = ExtractionManager(refiner=stub_refiner)

    async def mock_process_url(*args, **kwargs):
        return [RawJob(title="Software Engineer", job_url="https://example.com/jobs/1", description_text="Backend APIs", source="test")]

    manager.process_discovered_url = mock_process_url

    req = ExtractionRequest(url="https://example.com/careers", include_details=False)
    response = await manager.extract_jobs(req)

    assert len(response.jobs) == 1
    # Stub MUST have been invoked
    assert stub_refiner.invoked is True
    assert response.metadata.jobs_llm_refined == 1
    assert response.metadata.jobs_llm_refinement_failed == 0


@pytest.mark.asyncio
async def test_pipeline_enabled_toggle_fallback_on_forced_failure(monkeypatch):
    """
    When enabled: true and refinement throws/fails, the pipeline must catch the error,
    fall back to original unrefined output, preserve all jobs, and never fail the request.
    """
    monkeypatch.setattr("app.orchestrator.extraction_manager.is_feature_enabled", lambda feat: True)

    # Instantiate stub configured to force a failure
    stub_refiner = LLMOutputRefinerStub(force_failure=True)
    manager = ExtractionManager(refiner=stub_refiner)

    async def mock_process_url(*args, **kwargs):
        return [
            RawJob(title="Staff Security Engineer", job_url="https://example.com/jobs/2", description_text="Original raw description text", source="test")
        ]

    manager.process_discovered_url = mock_process_url

    req = ExtractionRequest(url="https://example.com/careers", include_details=False)
    response = await manager.extract_jobs(req)

    # Verify request did NOT fail and job was NOT lost
    assert len(response.jobs) == 1
    job = response.jobs[0]
    assert job.title == "Staff Security Engineer"
    assert job.description == "Original raw description text"
    assert job.description_refined is None
    # Metrics show graceful failure count
    assert response.metadata.jobs_llm_refinement_failed == 1
