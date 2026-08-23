"""Unit tests for Career Discovery Engine."""

import pytest
import respx
import httpx
from app.discovery.career_discovery import CareerDiscovery


def test_career_link_scoring():
    discovery = CareerDiscovery()

    score_ats = discovery.score_candidate_url("https://company.com", "https://boards.greenhouse.io/company")
    assert score_ats == 100

    score_path = discovery.score_candidate_url("https://company.com", "https://company.com/careers")
    assert score_path >= 95

    score_jobs = discovery.score_candidate_url("https://company.com", "https://company.com/jobs")
    assert score_jobs >= 95


@pytest.mark.asyncio
@respx.mock
async def test_discover_career_urls_from_html():
    html_content = """
    <html>
        <body>
            <a href="/about">About Us</a>
            <a href="/careers" id="career-link">Careers</a>
            <a href="https://boards.greenhouse.io/acme">View Open Positions</a>
        </body>
    </html>
    """
    respx.get("https://company.com").mock(return_value=httpx.Response(200, text=html_content))

    discovery = CareerDiscovery()
    urls = await discovery.discover_career_urls("https://company.com", html_content=html_content)

    assert len(urls) >= 2
    assert "https://boards.greenhouse.io/acme" in urls
    assert "https://company.com/careers" in urls
