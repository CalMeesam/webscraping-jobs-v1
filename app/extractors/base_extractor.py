"""Base Extractor interface."""

from abc import ABC, abstractmethod
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob


class BaseExtractor(ABC):
    """Abstract Base Extractor interface."""

    @abstractmethod
    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        """Returns True if this extractor can handle the given URL and classification."""
        ...

    @abstractmethod
    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        """
        Extracts jobs from the URL.
        Must return a list of RawJob objects. Must not raise on individual job parse errors.
        """
        ...
