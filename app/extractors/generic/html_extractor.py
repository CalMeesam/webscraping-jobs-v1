"""Generic Static HTML Extractor."""

import json
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob
from app.utils.html_utils import strip_html_tags
from app.utils.url_utils import make_absolute_url
from app.validation.candidate_validator import is_valid_job_candidate

logger = get_logger(__name__)

JOB_HREF_PATTERN = re.compile(
    r"/(job|jobs|position|positions|opening|openings|career|careers|req)/[a-zA-Z0-9\-_%?&=]+",
    re.IGNORECASE,
)


class HTMLExtractor(BaseExtractor):
    """Generic Static HTML extractor using BeautifulSoup4 / lxml."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return True  # Fallback extractor handles any URL

    def _extract_location_from_element(self, a_tag, parent_tag, title: str) -> str | None:
        """Extracts location string from dedicated elements, parent text, or title patterns."""
        if parent_tag:
            # 1. Dedicated location elements or classes
            loc_el = parent_tag.select_one(
                ".location, .job-location, [data-ph-at-id='job-location-text'], .city, .country, span.city, span.location"
            )
            if loc_el:
                loc_str = loc_el.get_text(strip=True)
                if loc_str and len(loc_str) >= 2:
                    return loc_str

            # Check Oracle HCM DOM pattern "Locations<LocationText>"
            p_text = parent_tag.get_text(strip=True)
            if "Locations" in p_text:
                m_locs = re.search(r"Locations\s*([A-Za-z\s,]+?)(?:\(|\d|Trending|Be the First|$)", p_text)
                if m_locs:
                    return m_locs.group(1).strip()

        # 2. Extract location pattern from title text (e.g. "... | Pune)" or "... - Pune")
        m_pipe = re.search(r"\|\s*([A-Za-z\s,]+)\s*\)?$", title)
        if m_pipe:
            loc = m_pipe.group(1).strip()
            if len(loc) >= 2 and not any(x in loc.lower() for x in ["year", "years", "month", "full time", "part time"]):
                return loc

        m_dash = re.search(r"\-\s*([A-Za-z\s,]+)\s*$", title)
        if m_dash:
            loc = m_dash.group(1).strip()
            if len(loc) >= 2 and not any(x in loc.lower() for x in ["year", "years", "month", "full time", "part time", "leader", "engineer"]):
                return loc

        # 3. Search parent text for common location patterns
        if parent_tag:
            parent_text = parent_tag.get_text(separator=" ", strip=True)
            m_loc = re.search(
                r"\b(Pune|Bengaluru|Bangalore|San Jose|Research Triangle Park|RTP|London|Singapore|Sydney|Berlin|Tokyo|Toronto|New York|San Francisco|Gurugram|Noida|Chennai)\b",
                parent_text,
                re.IGNORECASE,
            )
            if m_loc:
                return m_loc.group(1).title()

        return None

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
        html_content: str | None = None,
    ) -> list[RawJob]:
        if not html_content:
            client = self._client or httpx.AsyncClient(
                timeout=settings.HTTP_TIMEOUT_SECONDS,
                headers={"User-Agent": settings.USER_AGENT},
                follow_redirects=True,
            )
            should_close = self._client is None
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    context.warnings.append(f"Static HTML fetch returned status {r.status_code}")
                    return []
                html_content = r.text
            except Exception as e:
                logger.warning(f"Error fetching HTML for {url}: {e}")
                context.warnings.append(f"Failed to fetch static HTML for {url}: {e}")
                return []
            finally:
                if should_close:
                    await client.aclose()

        soup = BeautifulSoup(html_content, "lxml")
        raw_jobs: list[RawJob] = []

        # Strategy 1: JSON-LD JobPosting schema.org blocks (Highest confidence)
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
                postings = data if isinstance(data, list) else [data]
                for item in postings:
                    if isinstance(item, dict) and item.get("@type") == "JobPosting":
                        title = item.get("title")
                        desc = item.get("description")
                        loc = item.get("jobLocation")
                        loc_str = None
                        if isinstance(loc, dict):
                            address = loc.get("address")
                            if isinstance(address, dict):
                                loc_str = f"{address.get('addressLocality', '')}, {address.get('addressCountry', '')}".strip(", ")
                        elif isinstance(loc, str):
                            loc_str = loc

                        job_url = item.get("url") or url
                        job_url = make_absolute_url(url, job_url)

                        if not is_valid_job_candidate(title, job_url, url):
                            continue

                        raw_jobs.append(
                            RawJob(
                                source_id=str(item.get("identifier", {}).get("value") or ""),
                                title=title,
                                location=loc_str,
                                description_html=desc,
                                description_text=strip_html_tags(desc) if desc else None,
                                employment_type=item.get("employmentType"),
                                job_url=job_url,
                                source_url=url,
                                source_type="static_html",
                                raw_data=item,
                            )
                        )
            except Exception as e:
                logger.warning(f"Failed to parse JSON-LD block: {e}")
                continue

        if raw_jobs:
            logger.info(f"HTMLExtractor extracted {len(raw_jobs)} jobs via JSON-LD schema")
            return raw_jobs

        # Strategy 2: Repeated DOM elements with job anchor patterns
        anchors = soup.find_all("a", href=JOB_HREF_PATTERN)
        seen_urls: set[str] = set()

        for a in anchors:
            href = a.get("href")
            job_url = make_absolute_url(url, href)
            if not job_url or job_url in seen_urls:
                continue

            title = a.get_text(strip=True)
            parent = a.find_parent(["div", "li", "tr", "article"])

            if not title or len(title) < 3:
                if parent:
                    parent_text = parent.get_text(strip=True)
                    if len(parent_text) > len(title):
                        title = parent_text.split("\n")[0].strip()

            if title:
                # Clean concatenated title metadata (e.g. Oracle HCM DOM anchor text)
                if "Posting Date" in title:
                    title = title.split("Posting Date")[0].strip()

            if title and is_valid_job_candidate(title, job_url, url):
                seen_urls.add(job_url)
                loc_str = self._extract_location_from_element(a, parent, title)

                raw_jobs.append(
                    RawJob(
                        title=title,
                        location=loc_str,
                        job_url=job_url,
                        source_url=url,
                        source_type="static_html",
                    )
                )

        logger.info(f"HTMLExtractor extracted {len(raw_jobs)} jobs via repeated DOM heuristics")
        return raw_jobs
