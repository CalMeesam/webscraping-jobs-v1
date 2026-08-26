"""Oracle Fusion HCM Candidate Experience Extractor."""

import re
from typing import Any
from urllib.parse import parse_qs, urlparse
import httpx
from app.core.config import settings
from app.core.constants import ERROR_EXTRACTION_FAILED
from app.core.logging import get_logger
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob
from app.utils.html_utils import strip_html_tags

logger = get_logger(__name__)


class OracleHCMExtractor(BaseExtractor):
    """Native ATS Extractor for Oracle Fusion HCM Candidate Experience sites."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    def parse_oracle_hcm_url(self, url: str) -> tuple[str, str, str] | None:
        """
        Parses Oracle HCM URL to extract (host, lang, siteNumber).
        Pattern: https://{host}/hcmUI/CandidateExperience/{lang}/sites/{siteNumber}/...
        """
        parsed = urlparse(url)
        netloc = parsed.netloc
        path = parsed.path

        m = re.search(r"/hcmUI/CandidateExperience/([^/]+)/sites/([^/]+)", path, re.IGNORECASE)
        if m:
            lang = m.group(1)
            site_number = m.group(2)
            return netloc, lang, site_number

        if "/hcmUI/CandidateExperience" in path:
            return netloc, "en", "careers"

        return None

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return classification.ats == "oracle_hcm" or "hcmUI/CandidateExperience" in url

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        context.ats = "oracle_hcm"
        context.strategy_used.append("oracle_hcm_api")

        info = self.parse_oracle_hcm_url(url)
        if not info:
            logger.warning(f"Could not parse Oracle HCM URL parameters from {url}")
            return []

        host, lang, site_number = info

        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        location_param = qs.get("location", [None])[0]
        keyword_param = qs.get("keyword", [None])[0]

        # Oracle HCM pagination: use offset and limit
        page_size = 25
        max_jobs_limit = context.max_jobs if (context.max_jobs and context.max_jobs > 0) else None

        client = self._client or httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        should_close = self._client is None

        raw_jobs: list[RawJob] = []
        offset = 0
        total_found = 0

        try:
            while True:
                # Stop if max_jobs limit reached
                if max_jobs_limit is not None and len(raw_jobs) >= max_jobs_limit:
                    logger.info(f"Oracle HCM extraction reached max_jobs limit ({max_jobs_limit})")
                    break

                # Build API URL with offset and limit for this page
                api_url = (
                    f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                    f"?onlyData=true&expand=requisitionList.workLocation,requisitionList.otherWorkLocations,"
                    f"requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields"
                    f"&finder=findReqs;siteNumber={site_number},"
                    f"facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,"
                    f"offset={offset},limit={page_size},sortBy=POSTING_DATES_DESC"
                )
                if location_param:
                    api_url += f",location={location_param}"
                if keyword_param:
                    api_url += f",keyword={keyword_param}"

                logger.info(f"Fetching Oracle HCM jobs from API (offset={offset}): {api_url}")

                r = await client.get(api_url)
                if r.status_code != 200:
                    logger.warning(f"Oracle HCM API returned HTTP {r.status_code} at offset {offset}")
                    context.warnings.append(f"Oracle HCM API returned status {r.status_code} at offset {offset}")
                    break

                data = r.json()
                items = data.get("items", [])
                if not items or not isinstance(items[0], dict):
                    break

                search_container = items[0]
                
                # Capture total count from first response
                if offset == 0:
                    total_found = search_container.get("TotalJobsCount", 0)
                    if total_found > 0:
                        context.total_jobs_found_override = int(total_found)
                        logger.info(f"Oracle HCM reports {total_found} total jobs available")

                req_list = search_container.get("requisitionList", [])
                if not req_list:
                    # No more jobs in this page
                    break

                for req in req_list:
                    # Stop if max_jobs limit reached
                    if max_jobs_limit is not None and len(raw_jobs) >= max_jobs_limit:
                        break
                    
                    req_id = req.get("Id") or req.get("RequisitionId")
                    title = req.get("Title")
                    if not title:
                        continue

                    location = req.get("PrimaryLocation")
                    if not location:
                        wl = req.get("workLocation", [])
                        if wl and isinstance(wl[0], dict):
                            loc_obj = wl[0]
                            city = loc_obj.get("TownOrCity", "")
                            region = loc_obj.get("Region2", "")
                            country = loc_obj.get("Country", "")
                            location = ", ".join(filter(None, [city, region, country]))

                    job_url = f"https://{host}/hcmUI/CandidateExperience/{lang}/sites/{site_number}/job/{req_id}"
                    if location_param:
                        job_url += f"?location={location_param}"

                    desc = req.get("ShortDescriptionStr") or req.get("ExternalResponsibilitiesStr")

                    raw_jobs.append(
                        RawJob(
                            source_id=str(req_id) if req_id else None,
                            title=title.strip(),
                            location=location,
                            department=req.get("Department") or req.get("JobFunction"),
                            employment_type=req.get("WorkplaceType") or req.get("JobType"),
                            description_html=desc,
                            description_text=strip_html_tags(desc) if desc else None,
                            posted_at=req.get("PostedDate"),
                            job_url=job_url,
                            source_url=url,
                            source_type="ats",
                            ats="oracle_hcm",
                            raw_data=req,
                        )
                    )

                # Move to next page
                offset += page_size

                # Stop if we've processed all available jobs
                if total_found > 0 and offset >= total_found:
                    logger.info(f"Oracle HCM extraction complete: processed all {total_found} available jobs")
                    break

            logger.info(f"OracleHCMExtractor extracted {len(raw_jobs)} jobs from Oracle HCM REST API (total available: {total_found})")
            return raw_jobs

        except Exception as e:
            msg = f"Oracle HCM extraction failed for {url}: {e}"
            logger.error(msg)
            context.warnings.append(msg)
            context.errors.append(ERROR_EXTRACTION_FAILED)
            return []
        finally:
            if should_close:
                await client.aclose()
