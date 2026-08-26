"""Tests for Lever ATS extractor."""

import pytest
from app.extractors.ats.lever import LeverExtractor
from app.models.extraction_models import ExtractionContext


class TestLeverExtractor:
    """Test Lever extractor."""

    def test_extract_company_slug(self):
        """Test extraction of company slug from various Lever URLs."""
        extractor = LeverExtractor()

        # jobs.lever.co format
        assert extractor.extract_company_slug("https://jobs.lever.co/spotify") == "spotify"
        assert extractor.extract_company_slug("https://jobs.lever.co/spotify/") == "spotify"
        assert extractor.extract_company_slug("https://jobs.lever.co/spotify/abc-123") == "spotify"

        # API format
        assert extractor.extract_company_slug("https://api.lever.co/v0/postings/spotify") == "spotify"
        assert extractor.extract_company_slug("https://api.lever.co/v0/postings/spotify?mode=json") == "spotify"

        # Invalid URLs
        assert extractor.extract_company_slug("https://lever.co") is None
        assert extractor.extract_company_slug("https://example.com") is None

    @pytest.mark.asyncio
    async def test_lever_extractor_success(self):
        """Test Lever extractor against real Spotify board."""
        extractor = LeverExtractor()
        url = "https://jobs.lever.co/spotify"
        context = ExtractionContext(input_url=url, max_jobs=5)

        jobs = await extractor.extract(url=url, context=context)

        # Should get jobs (Spotify usually has many openings)
        assert len(jobs) > 0, "Should extract jobs from Spotify Lever board"
        assert len(jobs) <= 5, "Should respect max_jobs limit"

        # Verify first job structure
        job = jobs[0]
        assert job.source_id, "Job should have source_id"
        assert job.title, "Job should have title"
        assert job.ats == "lever"
        assert job.source_url == "spotify"
        assert job.job_url, "Job should have URL"
        assert job.application_url, "Job should have application URL"

        # Verify description fields
        assert job.description_text or job.description_html, "Job should have description"

        print(f"\n✅ Extracted {len(jobs)} jobs from Spotify Lever board")
        print(f"Sample job: {job.title}")
        print(f"  Location: {job.location}")
        print(f"  Department: {job.department}")
        print(f"  URL: {job.job_url}")

    @pytest.mark.asyncio
    async def test_lever_extractor_invalid_company(self):
        """Test Lever extractor with non-existent company."""
        extractor = LeverExtractor()
        url = "https://jobs.lever.co/nonexistentcompany12345"
        context = ExtractionContext(input_url=url)

        jobs = await extractor.extract(url=url, context=context)

        # Should return empty list for 404
        assert len(jobs) == 0
        assert len(context.warnings) > 0
        assert "404" in context.warnings[0] or "not found" in context.warnings[0].lower()
