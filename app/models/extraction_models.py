"""Extraction classification, resolved URL, and context models."""

from typing import Literal
from pydantic import BaseModel, Field


class SourceClassification(BaseModel):
    source_type: Literal["ats", "api", "static_html", "dynamic", "unknown"]
    ats: str | None = None
    confidence: float


class ResolvedURL(BaseModel):
    original_url: str
    final_url: str
    redirect_chain: list[str] = Field(default_factory=list)
    status_code: int


class ExtractionContext(BaseModel):
    input_url: str
    resolved_url: str | None = None
    visited_urls: set[str] = Field(default_factory=set)
    discovered_urls: list[str] = Field(default_factory=list)
    career_urls: list[str] = Field(default_factory=list)
    job_urls: list[str] = Field(default_factory=list)
    ats: str | None = None
    strategy_used: list[str] = Field(default_factory=list)
    max_jobs: int | None = None
    include_details: bool = True
    preferred_location: str | None = None
    total_jobs_found_override: int | None = None
    jobs_enrichment_attempted: int = 0
    jobs_enriched: int = 0
    jobs_enrichment_failed: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
