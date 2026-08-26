"""Deduplication Engine."""

from app.core.logging import get_logger
from app.models.normalized_job import NormalizedJob
from app.utils.identity_utils import (
    compute_job_identity_key,
    get_composite_fingerprint,
    normalize_url_key,
)

logger = get_logger(__name__)


class Deduplicator:
    """
    Deduplicates normalized jobs according to priority rules:
    1. Source job ID (id)
    2. Job URL (normalized)
    3. Application URL (normalized)
    4. Composite fingerprint (title + location + department, lowercased & whitespace collapsed fallback only)
    """

    def normalize_url_key(self, url: str | None) -> str | None:
        return normalize_url_key(url)

    def get_composite_fingerprint(self, job: NormalizedJob) -> str:
        return get_composite_fingerprint(job)

    def compute_identity_key(self, job: NormalizedJob) -> str:
        return compute_job_identity_key(job)

    def remove_duplicates(self, jobs: list[NormalizedJob]) -> list[NormalizedJob]:
        seen_keys: set[str] = set()
        seen_ids: set[str] = set()
        seen_job_urls: set[str] = set()
        seen_app_urls: set[str] = set()
        seen_fingerprints: set[str] = set()

        deduped: list[NormalizedJob] = []

        for job in jobs:
            identity_key = compute_job_identity_key(job)

            # Check if canonical identity key has already been seen
            if identity_key in seen_keys:
                logger.info(f"Duplicate job dropped by identity key: {identity_key}")
                continue

            # Detailed checks matching legacy logging rules
            if job.id and job.id in seen_ids:
                logger.info(f"Duplicate job dropped by source_id: {job.id}")
                continue

            norm_job_url = self.normalize_url_key(job.job_url)
            if norm_job_url and norm_job_url in seen_job_urls:
                logger.info(f"Duplicate job dropped by job_url: {job.job_url}")
                continue

            norm_app_url = self.normalize_url_key(job.application_url)
            if norm_app_url and norm_app_url in seen_app_urls:
                logger.info(f"Duplicate job dropped by application_url: {job.application_url}")
                continue

            has_identifier = bool(job.id or norm_job_url or norm_app_url)
            if not has_identifier:
                fingerprint = self.get_composite_fingerprint(job)
                if fingerprint in seen_fingerprints:
                    logger.info(f"Duplicate job dropped by composite fingerprint: {fingerprint}")
                    continue
                seen_fingerprints.add(fingerprint)

            # Record seen keys
            seen_keys.add(identity_key)
            if job.id:
                seen_ids.add(job.id)
            if norm_job_url:
                seen_job_urls.add(norm_job_url)
            if norm_app_url:
                seen_app_urls.add(norm_app_url)

            deduped.append(job)

        dropped_count = len(jobs) - len(deduped)
        logger.info(f"Deduplication complete: {dropped_count} duplicates removed, {len(deduped)} jobs remaining")
        return deduped
