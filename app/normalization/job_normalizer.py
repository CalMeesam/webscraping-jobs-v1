"""Job Normalizer module."""

from urllib.parse import urlparse
from app.core.logging import get_logger
from app.models.normalized_job import NormalizedJob
from app.models.raw_job import RawJob
from app.normalization.location_normalizer import normalize_location
from app.utils.html_utils import clean_whitespace, strip_html_tags
from app.utils.url_utils import clean_url
from app.validation.candidate_validator import is_valid_job_candidate

logger = get_logger(__name__)


class JobNormalizer:
    """Converts RawJob models into clean, standardized NormalizedJob models."""

    def normalize(self, raw_jobs: list[RawJob]) -> list[NormalizedJob]:
        normalized_jobs: list[NormalizedJob] = []

        for raw in raw_jobs:
            title_clean = clean_whitespace(raw.title)
            job_url_clean = clean_url(raw.job_url) if raw.job_url else None

            # Validate that raw job candidate is a legitimate job posting, not chrome/social link
            if not is_valid_job_candidate(title_clean, job_url_clean, raw.source_url):
                logger.warning(f"Dropping invalid candidate job in normalizer: title={title_clean!r}, url={job_url_clean!r}")
                continue

            desc_clean = raw.description_text
            if not desc_clean and raw.description_html:
                desc_clean = strip_html_tags(raw.description_html)
            else:
                desc_clean = clean_whitespace(desc_clean)

            app_url_clean = clean_url(raw.application_url) if raw.application_url else None

            # Source name extraction from domain
            source_name = "unknown"
            if raw.source_url:
                try:
                    netloc = urlparse(raw.source_url).netloc.lower()
                    source_name = netloc.replace("www.", "").split(".")[0]
                except Exception:
                    pass

            normalized_job = NormalizedJob(
                id=raw.source_id,
                external_job_id=raw.external_job_id,
                requisition_id=raw.requisition_id,
                title=title_clean,
                location=normalize_location(raw.location),
                department=clean_whitespace(raw.department),
                employment_type=clean_whitespace(raw.employment_type),
                workplace_type=clean_whitespace(raw.workplace_type),
                experience_level=clean_whitespace(raw.experience_level),
                description=desc_clean,
                responsibilities=raw.responsibilities,
                requirements=raw.requirements,
                preferred_qualifications=raw.preferred_qualifications,
                benefits=raw.benefits,
                skills=raw.skills,
                job_url=job_url_clean,
                application_url=app_url_clean,
                posted_at=raw.posted_at,
                source=source_name,
                ats=raw.ats,
            )
            normalized_jobs.append(normalized_job)

        logger.info(f"Normalized {len(normalized_jobs)} jobs from {len(raw_jobs)} raw jobs")
        return normalized_jobs
