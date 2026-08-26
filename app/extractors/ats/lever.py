"""Lever ATS extractor.

Lever exposes a public, unauthenticated JSON API:
https://api.lever.co/v0/postings/{company}?mode=json

Returns all postings in one call, no pagination required for typical board sizes.

Verified against: Spotify (93 jobs)
API Structure documented in: lever_spotify_response.json
"""

from typing import List, Optional
from urllib.parse import urlparse
import httpx

from app.models.raw_job import RawJob
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.extractors.base_extractor import BaseExtractor
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class LeverExtractor(BaseExtractor):
    """Extract jobs from Lever ATS boards."""
    
    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.name = "lever"
    
    def extract_company_slug(self, url: str) -> str | None:
        """Extract company slug from Lever URL.
        
        Examples:
            https://jobs.lever.co/spotify -> spotify
            https://jobs.lever.co/spotify/abc-123 -> spotify
            https://api.lever.co/v0/postings/spotify -> spotify
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")
        
        if not parts or not parts[0]:
            return None
        
        # For jobs.lever.co/COMPANY or api.lever.co/v0/postings/COMPANY
        if "jobs.lever.co" in parsed.netloc:
            return parts[0] if parts else None
        elif "api.lever.co" in parsed.netloc and len(parts) >= 3:
            # api.lever.co/v0/postings/COMPANY
            return parts[2] if parts[0] == "v0" and parts[1] == "postings" else None
        
        return None
    
    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return classification.ats == "lever" or "lever.co" in url.lower()
    
    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> List[RawJob]:
        """Extract jobs from Lever board URL."""
        company = self.extract_company_slug(url)
        if not company:
            msg = f"Could not extract Lever company slug from URL: {url}"
            logger.warning(msg)
            context.warnings.append(msg)
            return []
        
        api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        
        logger.info(f"Fetching Lever jobs for company: {company}")
        logger.debug(f"API URL: {api_url}")
        
        client = self._client or httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        should_close = self._client is None
        
        try:
            r = await client.get(api_url)
            
            if r.status_code == 404:
                msg = f"Company '{company}' not found on Lever (404)"
                logger.warning(msg)
                context.warnings.append(msg)
                return []
            
            if r.status_code != 200:
                msg = f"Lever API returned HTTP {r.status_code} for company '{company}'"
                logger.warning(msg)
                context.warnings.append(msg)
                return []
            
            data = r.json()
            
            if not isinstance(data, list):
                msg = f"Unexpected Lever response type: {type(data)}"
                logger.error(msg)
                context.warnings.append(msg)
                return []
            
            logger.info(f"Retrieved {len(data)} jobs from Lever API")
            
            jobs = []
            max_jobs = context.max_jobs
            
            for job_data in data:
                try:
                    raw_job = self._parse_job(job_data, company)
                    jobs.append(raw_job)
                    
                    if max_jobs and len(jobs) >= max_jobs:
                        logger.info(f"Reached max_jobs limit: {max_jobs}")
                        break
                
                except Exception as e:
                    logger.warning(f"Failed to parse job {job_data.get('id')}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(jobs)} jobs")
            return jobs
        
        finally:
            if should_close:
                await client.aclose()
    
    def _parse_job(self, job_data: dict, company: str) -> RawJob:
        """Parse a single Lever job from API response."""
        
        # Extract location from categories
        categories = job_data.get("categories", {})
        location = categories.get("location", "")
        
        # Extract department and team
        department = categories.get("department") or categories.get("team")
        
        # Extract employment type (commitment in Lever)
        employment_type = categories.get("commitment", "")
        
        # Extract workplace type
        workplace_type = job_data.get("workplaceType", "")
        
        # Build description from multiple fields
        # Lever provides: description, descriptionBody, opening, lists, additional
        description_parts = []
        
        if job_data.get("opening"):
            description_parts.append(job_data["opening"])
        
        if job_data.get("descriptionBody"):
            description_parts.append(job_data["descriptionBody"])
        elif job_data.get("description"):
            description_parts.append(job_data["description"])
        
        # Add structured lists (What You'll Do, Who You Are, etc.)
        for list_item in job_data.get("lists", []):
            section_title = list_item.get("text", "")
            section_content = list_item.get("content", "")
            if section_title and section_content:
                description_parts.append(f"<h3>{section_title}</h3>{section_content}")
        
        if job_data.get("additional"):
            description_parts.append(job_data["additional"])
        
        description_html = "\n".join(description_parts)
        
        # Build plain text description
        description_plain_parts = []
        if job_data.get("openingPlain"):
            description_plain_parts.append(job_data["openingPlain"])
        if job_data.get("descriptionBodyPlain"):
            description_plain_parts.append(job_data["descriptionBodyPlain"])
        elif job_data.get("descriptionPlain"):
            description_plain_parts.append(job_data["descriptionPlain"])
        
        description_text = "\n\n".join(description_plain_parts)
        
        return RawJob(
            source_id=job_data.get("id", ""),
            title=job_data.get("text", ""),
            location=location,
            department=department,
            employment_type=employment_type,
            workplace_type=workplace_type,
            description_text=description_text,
            description_html=description_html,
            job_url=job_data.get("hostedUrl", ""),
            application_url=job_data.get("applyUrl", ""),
            posted_at=self._parse_timestamp(job_data.get("createdAt")),
            source_url=company,
            ats="lever",
            raw_data=job_data
        )
    
    def _parse_timestamp(self, timestamp_ms: Optional[int]) -> Optional[str]:
        """Convert Lever timestamp (milliseconds) to ISO date string."""
        if not timestamp_ms:
            return None
        
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
