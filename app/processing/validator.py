"""Job and Request Validation module."""

from app.core.constants import ERROR_INVALID_URL
from app.models.normalized_job import NormalizedJob
from app.utils.url_utils import is_valid_url


class Validator:
    """Validates ExtractionRequest input and output NormalizedJob models."""

    def validate_request_url(self, url: str) -> None:
        """Validates input URL syntax. Raises ValueError for invalid URLs."""
        if not is_valid_url(url):
            raise ValueError(f"Invalid URL format: {url}")

    def filter_valid_jobs(self, jobs: list[NormalizedJob]) -> list[NormalizedJob]:
        """Ensures all returned jobs satisfy schema constraints."""
        valid_jobs: list[NormalizedJob] = []
        for job in jobs:
            if job.title and len(job.title.strip()) > 0:
                valid_jobs.append(job)
        return valid_jobs
