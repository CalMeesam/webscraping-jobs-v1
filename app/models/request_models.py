"""Extraction request schema."""

from pydantic import BaseModel


class ExtractionRequest(BaseModel):
    url: str
    max_jobs: int | None = None
    include_details: bool = True
    preferred_location: str | None = None
