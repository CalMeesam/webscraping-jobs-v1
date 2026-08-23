"""Unit tests for Generic Static HTML Extractor."""

from pathlib import Path
import pytest
from app.extractors.generic.html_extractor import HTMLExtractor
from app.models.extraction_models import ExtractionContext

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def static_html_content():
    with open(FIXTURES_DIR / "static_career_page.html", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
async def test_html_extractor_json_ld(static_html_content):
    extractor = HTMLExtractor()
    context = ExtractionContext(input_url="https://acme.com/careers")

    jobs = await extractor.extract(
        url="https://acme.com/careers",
        context=context,
        html_content=static_html_content,
    )

    assert len(jobs) >= 1
    ld_job = jobs[0]
    assert ld_job.title == "Lead Backend Engineer"
    assert ld_job.location == "Austin, US"
    assert ld_job.source_id == "ACME-101"
    assert ld_job.employment_type == "FULL_TIME"
    assert ld_job.job_url == "https://acme.com/jobs/lead-backend-engineer"


@pytest.mark.asyncio
async def test_html_extractor_rejects_footer_social_links():
    footer_html = """
    <!DOCTYPE html>
    <html>
    <body>
      <div class="footer">
        <a href="https://www.facebook.com/ExlService/">Facebook</a>
        <a href="https://www.linkedin.com/company/exl-service">LinkedIn</a>
        <a href="https://twitter.com/exl_service">Twitter</a>
        <a href="https://www.youtube.com/user/EXL">YouTube</a>
        <a href="https://www.exlservice.com/">Home</a>
        <a href="https://www.exlservice.com/about-exl">About Us</a>
        <a href="https://example.com/privacy-policy">Privacy Policy</a>
      </div>
    </body>
    </html>
    """
    extractor = HTMLExtractor()
    context = ExtractionContext(input_url="https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs")

    jobs = await extractor.extract(
        url="https://fa-ewjt-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_2/jobs",
        context=context,
        html_content=footer_html,
    )

    assert len(jobs) == 0
