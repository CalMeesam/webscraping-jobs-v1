"""NormalizedJob public job model."""

from pydantic import BaseModel, Field


class JobLocation(BaseModel):
    raw: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class NormalizedJob(BaseModel):
    id: str | None = None
    external_job_id: str | None = None
    requisition_id: str | None = None

    title: str

    location: JobLocation | str | None = None
    department: str | None = None

    employment_type: str | None = None
    workplace_type: str | None = None
    experience_level: str | None = None

    description: str | None = None

    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferred_qualifications: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    job_url: str | None = None
    application_url: str | None = None

    posted_at: str | None = None

    source: str
    ats: str | None = None
