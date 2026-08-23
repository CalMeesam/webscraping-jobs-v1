"""Greenhouse ATS Extractor."""

import re
from urllib.parse import parse_qs, urlparse
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob
from app.utils.html_utils import strip_html_tags

logger = get_logger(__name__)


class GreenhouseExtractor(BaseExtractor):
    """Extractor for Greenhouse public job board API."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    def extract_board_token(self, url: str) -> str | None:
        """Parses Greenhouse board token from URL."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        query = parse_qs(parsed.query)

        if "for" in query and query["for"]:
            return query["for"][0]

        parts = path.split("/")
        if not parts or not parts[0]:
            return None

        # E.g. /boards/figma/jobs or /figma or /figma/jobs/123
        if parts[0] == "embed" and len(parts) > 1:
            return parts[1]
        if parts[0] in ("v1", "boards") and len(parts) > 1:
            return parts[1]

        return parts[0]

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return classification.ats == "greenhouse" or "greenhouse.io" in url.lower()

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        token = self.extract_board_token(url)
        if not token:
            msg = f"Could not extract Greenhouse board token from URL: {url}"
            logger.warning(msg)
            context.warnings.append(msg)
            return []

        board_api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        logger.info(f"Fetching Greenhouse jobs for board: {token} via API: {board_api_url}")

        client = self._client or httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        should_close = self._client is None

        try:
            r = await client.get(board_api_url)
            if r.status_code != 200:
                msg = f"Greenhouse API returned HTTP {r.status_code} for board '{token}'"
                logger.warning(msg)
                context.warnings.append(msg)
                return []

            data = r.json()
            job_list = data.get("jobs", [])
            logger.info(f"Greenhouse API returned {len(job_list)} jobs for board '{token}'")

            raw_jobs: list[RawJob] = []
            for item in job_list:
                try:
                    job_id = str(item.get("id")) if item.get("id") else None
                    title = item.get("title")

                    location_name = None
                    if item.get("location") and isinstance(item["location"], dict):
                        location_name = item["location"].get("name")

                    dept_name = None
                    if item.get("departments") and isinstance(item["departments"], list) and len(item["departments"]) > 0:
                        dept_name = item["departments"][0].get("name")

                    content_html = item.get("content")
                    content_text = strip_html_tags(content_html) if content_html else None

                    job_url = item.get("absolute_url")
                    app_url = f"{job_url}#app" if job_url else None

                    raw_job = RawJob(
                        source_id=job_id,
                        title=title,
                        location=location_name,
                        department=dept_name,
                        description_html=content_html,
                        description_text=content_text,
                        job_url=job_url,
                        application_url=app_url,
                        source_url=url,
                        source_type="ats",
                        ats="greenhouse",
                        raw_data=item,
                    )
                    raw_jobs.append(raw_job)
                except Exception as e:
                    logger.warning(f"Error parsing Greenhouse job item: {e}")
                    context.warnings.append(f"Failed to parse Greenhouse job item: {e}")
                    continue

            return raw_jobs

        finally:
            if should_close:
                await client.aclose()
