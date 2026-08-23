"""Workday ATS CXS Extractor."""

import re
from urllib.parse import urlparse
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob
from app.utils.html_utils import strip_html_tags

logger = get_logger(__name__)

WORKDAY_PAGE_SIZE = 20


class WorkdayExtractor(BaseExtractor):
    """Extractor for Workday CXS JSON endpoints with offset-based pagination."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    def parse_workday_url(self, url: str) -> tuple[str, str, str] | None:
        """
        Parses Workday URL into (tenant, host_num, site).
        Example: https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
        -> ('nvidia', 'wd5', 'NVIDIAExternalCareerSite')
        """
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()  # e.g. nvidia.wd5.myworkdayjobs.com

        host_match = re.match(r"^([^.]+)\.([^.]+)\.myworkdayjobs\.com$", hostname)
        if not host_match:
            return None

        tenant, host_num = host_match.group(1), host_match.group(2)

        path_parts = [p for p in parsed.path.split("/") if p]
        if not path_parts:
            return None

        # Filter out locale prefixes like en-US, fr-FR
        site = path_parts[0]
        if re.match(r"^[a-z]{2}-[A-Z]{2}$", site, re.IGNORECASE) and len(path_parts) > 1:
            site = path_parts[1]

        # Ignore if path starts with wday or job
        if site in ("wday", "job", "jobs"):
            return None

        return tenant, host_num, site

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return classification.ats == "workday" or "myworkdayjobs.com" in url.lower()

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        parsed_info = self.parse_workday_url(url)
        if not parsed_info:
            msg = f"Could not parse Workday tenant/site details from URL: {url}"
            logger.warning(msg)
            context.warnings.append(msg)
            return []

        tenant, host_num, site = parsed_info
        cxs_jobs_url = f"https://{tenant}.{host_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
        logger.info(f"Targeting Workday CXS endpoint: {cxs_jobs_url}")

        client = self._client or httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={
                "User-Agent": settings.USER_AGENT,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            follow_redirects=True,
        )
        should_close = self._client is None

        raw_jobs: list[RawJob] = []
        offset = 0
        total_found = 0

        try:
            while True:
                # Stop if max_jobs limit reached (only when preferred_location is NOT active)
                if context.preferred_location is None and context.max_jobs is not None and len(raw_jobs) >= context.max_jobs:
                    logger.info(f"Workday extraction reached max_jobs limit ({context.max_jobs})")
                    break

                payload = {
                    "appliedFacets": {},
                    "limit": WORKDAY_PAGE_SIZE,
                    "offset": offset,
                    "searchText": "",
                }

                try:
                    response = await client.post(cxs_jobs_url, json=payload)
                    if response.status_code != 200:
                        logger.warning(f"Workday CXS API returned HTTP {response.status_code} at offset {offset}")
                        break

                    data = response.json()
                    
                    # Capture true total from offset 0 (Workday includes total count only on offset 0)
                    resp_total = data.get("total", 0)
                    if resp_total > 0:
                        total_found = resp_total
                        context.total_jobs_found_override = resp_total

                    postings = data.get("jobPostings", [])

                    if not postings:
                        break

                    for posting in postings:
                        if context.preferred_location is None and context.max_jobs is not None and len(raw_jobs) >= context.max_jobs:
                            break

                        try:
                            title = posting.get("title")
                            ext_path = posting.get("externalPath", "")

                            # Extract job req ID
                            bullet_fields = posting.get("bulletFields", [])
                            source_id = bullet_fields[0] if bullet_fields else None
                            if not source_id and ext_path:
                                source_id = ext_path.rsplit("_", 1)[-1] if "_" in ext_path else None

                            location_text = posting.get("locationsText")
                            job_url = f"https://{tenant}.{host_num}.myworkdayjobs.com/en-US/{site}{ext_path}"

                            raw_job = RawJob(
                                source_id=source_id,
                                title=title,
                                location=location_text,
                                job_url=job_url,
                                source_url=url,
                                source_type="ats",
                                ats="workday",
                                raw_data=posting,
                            )
                            raw_jobs.append(raw_job)

                        except Exception as parse_err:
                            logger.warning(f"Error parsing Workday job posting: {parse_err}")
                            continue

                    offset += WORKDAY_PAGE_SIZE

                    # Stop if we processed all available total jobs
                    if total_found > 0 and offset >= total_found:
                        break

                except Exception as req_err:
                    logger.warning(f"Error requesting Workday CXS page at offset {offset}: {req_err}")
                    context.warnings.append(f"Workday CXS error at offset {offset}: {req_err}")
                    break

            logger.info(f"Workday extractor fetched {len(raw_jobs)} jobs out of {total_found} total")
            return raw_jobs

        finally:
            if should_close:
                await client.aclose()
