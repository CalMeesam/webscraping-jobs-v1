"""Unit tests for Greenhouse Extractor."""

import json
from pathlib import Path
import pytest
import respx
import httpx
from app.extractors.ats.greenhouse import GreenhouseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def greenhouse_jobs_json():
    with open(FIXTURES_DIR / "greenhouse_jobs_list.json", encoding="utf-8") as f:
        return json.load(f)


def test_greenhouse_token_extraction():
    extractor = GreenhouseExtractor()

    assert extractor.extract_board_token("https://boards.greenhouse.io/figma") == "figma"
    assert extractor.extract_board_token("https://boards.greenhouse.io/figma/jobs/12345") == "figma"
    assert extractor.extract_board_token("https://boards.greenhouse.io/embed/job_board?for=figma") == "figma"


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_extractor_success(greenhouse_jobs_json):
    respx.get("https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true").mock(
        return_value=httpx.Response(200, json=greenhouse_jobs_json)
    )

    extractor = GreenhouseExtractor()
    context = ExtractionContext(input_url="https://boards.greenhouse.io/figma")
    classification = SourceClassification(source_type="ats", ats="greenhouse", confidence=1.0)

    assert await extractor.can_handle("https://boards.greenhouse.io/figma", classification)

    jobs = await extractor.extract("https://boards.greenhouse.io/figma", context)

    assert len(jobs) == 2
    assert jobs[0].title == "Senior Staff Software Engineer"
    assert jobs[0].source_id == "4012345"
    assert jobs[0].location == "San Francisco, CA"
    assert jobs[0].department == "Engineering"
    assert jobs[0].description_html is not None
    assert jobs[0].description_text == "We are seeking a Senior Staff Software Engineer to build scalable real-time systems."
    assert jobs[0].ats == "greenhouse"
