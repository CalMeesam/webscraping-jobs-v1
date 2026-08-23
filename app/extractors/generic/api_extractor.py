"""Generic Discovered API Extractor."""

from typing import Any
from urllib.parse import urlparse
from app.core.logging import get_logger
from app.discovery.api_discovery import APIDiscovery
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob
from app.utils.html_utils import strip_html_tags
from app.validation.candidate_validator import is_valid_job_candidate

logger = get_logger(__name__)


class APIExtractor(BaseExtractor):
    """Extractor for discovered JSON APIs passing schema validation."""

    def __init__(self):
        self.api_validator = APIDiscovery()

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return classification.source_type == "api"

    def find_job_items(self, data: Any, depth: int = 0) -> list[dict]:
        """Recursively finds dictionaries representing job postings within nested JSON structures."""
        if depth > 5 or not data:
            return []

        found_items: list[dict] = []

        if isinstance(data, dict):
            # Check Oracle HCM requisitionList structure
            if "requisitionList" in data and isinstance(data["requisitionList"], list):
                return [i for i in data["requisitionList"] if isinstance(i, dict)]

            for key, val in data.items():
                if key == "requisitionList" and isinstance(val, list):
                    return [i for i in val if isinstance(i, dict)]
                elif isinstance(val, list) and val and isinstance(val[0], dict):
                    # Handle containers that embed requisitionList (e.g. Oracle HCM search container)
                    if "requisitionList" in val[0]:
                        for item in val:
                            if "requisitionList" in item and isinstance(item["requisitionList"], list):
                                found_items.extend([i for i in item["requisitionList"] if isinstance(i, dict)])
                        return found_items

                    # Require explicit job fields in array items, NOT just generic 'name'
                    if any(k in val[0] for k in ("Title", "title", "jobTitle", "position_title", "jobReqId")):
                        found_items.extend([i for i in val if isinstance(i, dict)])
                    else:
                        found_items.extend(self.find_job_items(val, depth + 1))
                elif isinstance(val, (dict, list)):
                    found_items.extend(self.find_job_items(val, depth + 1))

        elif isinstance(data, list):
            for item in data:
                found_items.extend(self.find_job_items(item, depth + 1))

        return found_items

    def _build_oracle_hcm_job_url(self, source_url: str, req_id: str) -> str:
        """Constructs canonical job posting URL for Oracle HCM platform."""
        parsed = urlparse(source_url)
        path = parsed.path
        if "/sites/" in path:
            base_site = path.split("/jobs")[0].rstrip("/")
            return f"{parsed.scheme}://{parsed.netloc}{base_site}/job/{req_id}"
        return f"{parsed.scheme}://{parsed.netloc}/hcmUI/CandidateExperience/en/sites/careers/job/{req_id}"

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
        json_data: Any | None = None,
    ) -> list[RawJob]:
        if not json_data:
            return []

        items = self.find_job_items(json_data)
        if not items:
            return []

        raw_jobs: list[RawJob] = []
        seen_titles: set[str] = set()

        for item in items:
            try:
                title = (
                    item.get("Title")
                    or item.get("title")
                    or item.get("jobTitle")
                    or item.get("position_title")
                    or item.get("name")
                )
                if not title or not isinstance(title, str):
                    continue

                title_clean = title.strip()
                if not title_clean or title_clean in seen_titles:
                    continue

                location = (
                    item.get("PrimaryLocation")
                    or item.get("location")
                    or item.get("cityState")
                    or item.get("location_name")
                    or item.get("city")
                    or item.get("country")
                )
                if isinstance(location, dict):
                    location = location.get("name") or location.get("location") or location.get("city")
                elif isinstance(location, list) and location:
                    first_loc = location[0]
                    location = first_loc.get("location") if isinstance(first_loc, dict) else str(first_loc)

                department = (
                    item.get("department")
                    or item.get("category")
                    or item.get("team")
                    or item.get("OrganizationName")
                )
                if isinstance(department, dict):
                    department = department.get("name")

                desc = item.get("description") or item.get("descriptionTeaser") or item.get("content") or item.get("details") or item.get("ShortDescription")
                req_id = (
                    item.get("Id")
                    or item.get("RequisitionId")
                    or item.get("reqId")
                    or item.get("jobId")
                    or item.get("jobSeqNo")
                    or item.get("id")
                )

                job_url = (
                    item.get("applyUrl")
                    or item.get("url")
                    or item.get("job_url")
                    or item.get("absolute_url")
                )

                if not job_url and req_id and "oraclecloud" in url.lower():
                    job_url = self._build_oracle_hcm_job_url(url, str(req_id))

                if not job_url:
                    job_url = url

                # Systemic candidate validation check
                if not is_valid_job_candidate(title_clean, str(job_url), url):
                    logger.debug(f"APIExtractor filtered out non-job item: title={title_clean!r}, url={job_url!r}")
                    continue

                seen_titles.add(title_clean)

                raw_jobs.append(
                    RawJob(
                        source_id=str(req_id) if req_id else None,
                        title=title_clean,
                        location=str(location) if location else None,
                        department=str(department) if department else None,
                        description_html=str(desc) if desc else None,
                        description_text=strip_html_tags(desc) if desc else None,
                        employment_type=item.get("type") or item.get("WorkplaceType"),
                        job_url=str(job_url) if job_url else None,
                        source_url=url,
                        source_type="api",
                        raw_data=item,
                    )
                )
            except Exception as parse_err:
                logger.warning(f"Error parsing job item from API data: {parse_err}")
                continue

        logger.info(f"APIExtractor extracted {len(raw_jobs)} validated jobs directly from API JSON payload")
        return raw_jobs
