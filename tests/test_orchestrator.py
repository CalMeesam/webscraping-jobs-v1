"""Unit tests for Extraction Manager Orchestrator."""

import json
from pathlib import Path
import pytest
import respx
import httpx
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def greenhouse_jobs_json():
    with open(FIXTURES_DIR / "greenhouse_jobs_list.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
@respx.mock
async def test_orchestrator_greenhouse_flow(greenhouse_jobs_json):
    # Mock redirect from company.com/careers -> boards.greenhouse.io/figma
    respx.head("https://company.com/careers").mock(
        return_value=httpx.Response(302, headers={"Location": "https://boards.greenhouse.io/figma"})
    )
    respx.head("https://boards.greenhouse.io/figma").mock(
        return_value=httpx.Response(200)
    )
    respx.get("https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true").mock(
        return_value=httpx.Response(200, json=greenhouse_jobs_json)
    )

    manager = ExtractionManager()
    request = ExtractionRequest(url="https://company.com/careers", max_jobs=1, include_details=True)

    response = await manager.extract_jobs(request)

    assert response.metadata.total_jobs_found == 2
    assert response.metadata.total_jobs_returned == 1
    assert len(response.jobs) == 1
    assert response.jobs[0].title == "Senior Staff Software Engineer"
    assert response.metadata.ats == "greenhouse"
    assert response.metadata.resolved_url == "https://boards.greenhouse.io/figma"


@pytest.mark.asyncio
async def test_orchestrator_unsupported_ats():
    manager = ExtractionManager()
    request = ExtractionRequest(url="https://jobs.lever.co/spotify")

    response = await manager.extract_jobs(request)

    assert len(response.jobs) == 0
    assert "ATS_DETECTED_BUT_UNSUPPORTED" in response.metadata.errors
    assert response.metadata.ats == "lever"
