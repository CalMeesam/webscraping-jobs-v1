"""RawJob universal internal contract model."""

from pydantic import BaseModel, Field


class RawJob(BaseModel):
    source_id: str | None = None
    external_job_id: str | None = None
    requisition_id: str | None = None

    title: str | None = None
    location: str | None = None
    location_raw: str | None = None
    department: str | None = None
    team: str | None = None

    employment_type: str | None = None
    workplace_type: str | None = None
    experience_level: str | None = None

    description_html: str | None = None
    description_text: str | None = None

    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    job_url: str | None = None
    application_url: str | None = None

    posted_at: str | None = None

    source_url: str | None = None
    source_type: str | None = None
    ats: str | None = None

    is_enriched: bool = False
    enrichment_error: str | None = None

    raw_data: dict = Field(default_factory=dict)
