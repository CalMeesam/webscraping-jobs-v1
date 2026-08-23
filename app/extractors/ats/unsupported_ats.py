"""Unsupported ATS Extractor stub."""

from app.core.constants import ERROR_ATS_DETECTED_BUT_UNSUPPORTED, SUPPORTED_ATS_VENDORS
from app.core.logging import get_logger
from app.extractors.base_extractor import BaseExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob

logger = get_logger(__name__)


class UnsupportedATSExtractor(BaseExtractor):
    """
    Extractor stub for detected ATS vendors that are currently unsupported
    (e.g., Lever, SmartRecruiters, Ashby).
    Explicitly logs and records ERROR_ATS_DETECTED_BUT_UNSUPPORTED.
    """

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        if classification.source_type == "ats" and classification.ats:
            return classification.ats not in SUPPORTED_ATS_VENDORS
        return False

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        vendor_name = context.ats or "unsupported_ats"
        err_msg = (
            f"ATS '{vendor_name}' was detected at '{url}', but is currently unsupported. "
            "Only Greenhouse and Workday ATS extractions are supported in this engine."
        )
        logger.warning(err_msg)
        context.errors.append(ERROR_ATS_DETECTED_BUT_UNSUPPORTED)
        context.warnings.append(err_msg)
        return []
