"""Response schemas for job extraction endpoint."""

from typing import Any
from pydantic import BaseModel, Field
from app.models.normalized_job import NormalizedJob


class DiffSummary(BaseModel):
    has_previous_run: bool = False
    latest_run_id: int | None = None
    previous_run_id: int | None = None
    latest_run_at: str | None = None
    previous_run_at: str | None = None
    new_jobs_count: int = 0
    removed_jobs_count: int = 0
    unchanged_jobs_count: int = 0
    new_job_keys: list[str] = Field(default_factory=list)
    removed_job_keys: list[str] = Field(default_factory=list)
    unchanged_job_keys: list[str] = Field(default_factory=list)
    message: str | None = None


class ExtractionMetadata(BaseModel):
    input_url: str
    resolved_url: str | None = None

    career_url: str | None = None
    job_source_url: str | None = None

    source_type: str | None = None
    ats: str | None = None
    customer_id: str | None = None

    extraction_strategy: str | None = None

    visited_urls: list[str] = Field(default_factory=list)

    total_jobs_found: int = 0
    total_jobs_returned: int = 0

    jobs_discovered: int = 0
    jobs_returned: int = 0
    jobs_enrichment_attempted: int = 0
    jobs_enriched: int = 0
    jobs_enrichment_failed: int = 0

    diff_summary: dict[str, Any] | None = None

    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    metadata: ExtractionMetadata
    jobs: list[NormalizedJob] = Field(default_factory=list)
