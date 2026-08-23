"""Detail Enrichment module.

Enriches RawJob instances with job descriptions, parsed sections (responsibilities, requirements,
preferred qualifications, benefits), and technical skills using bounded concurrency.
"""

import asyncio
import html
from typing import Any
import httpx
from app.core.config import settings
from app.core.constants import ERROR_DETAIL_ENRICHMENT_FAILED
from app.core.logging import get_logger
from app.extractors.ats.greenhouse import GreenhouseExtractor
from app.extractors.ats.workday import WorkdayExtractor
from app.models.extraction_models import ExtractionContext
from app.models.raw_job import RawJob
from app.parsing.job_description_parser import JobDescriptionParser
from app.parsing.skills_extractor import SkillsExtractor
from app.utils.html_utils import strip_html_tags
from app.validation.candidate_validator import is_valid_job_candidate

logger = get_logger(__name__)


def requires_enrichment(job: RawJob) -> bool:
    """Returns True if job is missing description text or HTML."""
    return not (job.description_text or job.description_html)


class DetailEnricher:
    """Enriches RawJob instances with full details, parsed sections, and skills."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.greenhouse_extractor = GreenhouseExtractor()
        self.workday_extractor = WorkdayExtractor()
        self.section_parser = JobDescriptionParser()
        self.skills_extractor = SkillsExtractor()

    async def enrich_single_job(
        self,
        job: RawJob,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> RawJob:
        if not is_valid_job_candidate(job.title, job.job_url, job.source_url):
            logger.warning(f"Skipping detail enrichment for invalid non-job candidate: {job.title} ({job.job_url})")
            return job

        async with semaphore:
            try:
                # ATS Branch 1: Greenhouse
                if job.ats == "greenhouse" and job.source_url and job.source_id:
                    token = self.greenhouse_extractor.extract_board_token(job.source_url)
                    if token:
                        detail_api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job.source_id}"
                        r = await client.get(detail_api_url)
                        if r.status_code == 200:
                            data = r.json()
                            content_html = data.get("content")
                            if content_html:
                                unescaped_html = html.unescape(content_html)
                                job.description_html = unescaped_html
                                job.description_text = strip_html_tags(unescaped_html)

                            job.external_job_id = str(data.get("id")) if data.get("id") else job.source_id
                            job.posted_at = data.get("updated_at")

                            # Parse location name if available
                            loc_dict = data.get("location")
                            if isinstance(loc_dict, dict) and loc_dict.get("name"):
                                job.location = loc_dict["name"]

                            # Parse department
                            depts = data.get("departments")
                            if isinstance(depts, list) and depts and isinstance(depts[0], dict):
                                job.department = depts[0].get("name")

                            job.job_url = data.get("absolute_url") or job.job_url
                            job.application_url = f"{job.job_url}#app" if job.job_url else job.application_url
                            job.is_enriched = True

                # ATS Branch 2: Workday
                elif job.ats == "workday" and job.source_url and job.raw_data.get("externalPath"):
                    parsed_info = self.workday_extractor.parse_workday_url(job.source_url)
                    if parsed_info:
                        tenant, host_num, site = parsed_info
                        ext_path = job.raw_data["externalPath"]
                        cxs_detail_url = f"https://{tenant}.{host_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{ext_path}"
                        r = await client.get(cxs_detail_url)
                        if r.status_code == 200:
                            data = r.json()
                            info = data.get("jobPostingInfo", {})
                            job_desc_html = info.get("jobDescription")
                            if job_desc_html:
                                job.description_html = job_desc_html
                                job.description_text = strip_html_tags(job_desc_html)

                            job.requisition_id = info.get("jobReqId") or info.get("id")
                            job.external_job_id = info.get("jobPostingId") or job.source_id
                            job.employment_type = info.get("timeType")
                            job.posted_at = info.get("postedOn") or info.get("startDate")

                            # Location & additional locations
                            primary_loc = info.get("location")
                            add_locs = info.get("additionalLocations", [])
                            if primary_loc:
                                loc_parts = [primary_loc] + ([str(l) for l in add_locs] if add_locs else [])
                                job.location = " | ".join(loc_parts)

                            if info.get("externalUrl"):
                                job.job_url = info.get("externalUrl")

                            job.is_enriched = True

                # Fallback for generic HTML job URLs if description is missing
                elif job.job_url and not (job.description_html or job.description_text):
                    r = await client.get(job.job_url)
                    if r.status_code == 200:
                        job.description_html = r.text
                        job.description_text = strip_html_tags(r.text)
                        job.is_enriched = True

            except Exception as err:
                msg = f"Detail enrichment failed for job '{job.title}': {err}"
                logger.warning(msg)
                job.enrichment_error = str(err)

            # Perform Structured Job Description Section Parsing
            if job.description_html or job.description_text:
                sections = self.section_parser.parse(job.description_html, job.description_text)
                job.responsibilities = sections.get("responsibilities", [])
                job.requirements = sections.get("requirements", [])
                job.preferred_qualifications = sections.get("preferred_qualifications", [])
                job.benefits = sections.get("benefits", [])

            # Perform Skills Extraction
            job.skills = self.skills_extractor.extract_skills(
                job.description_text,
                [job.requirements, job.responsibilities, job.preferred_qualifications],
            )

            return job

    async def enrich(
        self,
        raw_jobs: list[RawJob],
        context: ExtractionContext,
    ) -> list[RawJob]:
        if not context.include_details:
            logger.info("include_details=False; skipping detail enrichment pipeline entirely")
            return raw_jobs

        if not raw_jobs:
            return raw_jobs

        # Filter to only valid candidate jobs before enrichment
        valid_raw_jobs = [j for j in raw_jobs if is_valid_job_candidate(j.title, j.job_url, j.source_url)]
        if not valid_raw_jobs:
            logger.warning("No valid job candidates to enrich")
            return []

        logger.info(
            f"Executing detail enrichment pipeline for {len(valid_raw_jobs)} target jobs "
            f"(bounded by concurrency semaphore {settings.DEFAULT_CONCURRENCY})"
        )

        semaphore = asyncio.Semaphore(settings.DEFAULT_CONCURRENCY)
        client = self._client or httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
            follow_redirects=True,
        )
        should_close = self._client is None

        context.jobs_enrichment_attempted = len(valid_raw_jobs)

        try:
            tasks = [self.enrich_single_job(job, client, semaphore) for job in valid_raw_jobs]
            enriched_jobs = await asyncio.gather(*tasks, return_exceptions=False)

            enriched_count = sum(1 for j in enriched_jobs if j.is_enriched)
            context.jobs_enriched = enriched_count
            context.jobs_enrichment_failed = len(valid_raw_jobs) - enriched_count

            logger.info(f"Detail enrichment completed: {enriched_count}/{len(valid_raw_jobs)} jobs enriched")
            return list(enriched_jobs)
        except Exception as e:
            msg = f"Detail enrichment batch failed: {e}"
            logger.warning(msg)
            context.warnings.append(msg)
            context.errors.append(ERROR_DETAIL_ENRICHMENT_FAILED)
            return valid_raw_jobs
        finally:
            if should_close:
                await client.aclose()
