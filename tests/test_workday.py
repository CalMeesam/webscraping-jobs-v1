"""Unit tests for Workday Extractor."""

import json
from pathlib import Path
import pytest
import respx
import httpx
from app.extractors.ats.workday import WorkdayExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def workday_jobs_json():
    with open(FIXTURES_DIR / "workday_jobs_list.json", encoding="utf-8") as f:
        return json.load(f)


def test_workday_url_parser():
    extractor = WorkdayExtractor()

    parsed = extractor.parse_workday_url("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
    assert parsed == ("nvidia", "wd5", "NVIDIAExternalCareerSite")

    parsed_locale = extractor.parse_workday_url("https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced")
    assert parsed_locale == ("adobe", "wd5", "external_experienced")


@pytest.mark.asyncio
@respx.mock
async def test_workday_extractor_success(workday_jobs_json):
    cxs_url = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
    respx.post(cxs_url).mock(return_value=httpx.Response(200, json=workday_jobs_json))

    extractor = WorkdayExtractor()
    context = ExtractionContext(input_url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite")
    classification = SourceClassification(source_type="ats", ats="workday", confidence=1.0)

    assert await extractor.can_handle("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", classification)

    jobs = await extractor.extract("https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", context)

    assert len(jobs) == 2
    assert jobs[0].title == "Principal Architect, AI Infrastructure"
    assert jobs[0].source_id == "JR190001"
    assert jobs[0].location == "Santa Clara, CA"
    assert jobs[0].ats == "workday"
