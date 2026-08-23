"""Source Classification module."""

from app.core.config import settings
from app.core.logging import get_logger
from app.discovery.ats_detector import ATSDetector
from app.models.extraction_models import SourceClassification

logger = get_logger(__name__)


class SourceClassifier:
    """Classifies URL into source type and ATS vendor with threshold enforcement."""

    def __init__(self, ats_detector: ATSDetector | None = None):
        self.ats_detector = ats_detector or ATSDetector()

    def classify(self, url: str, html_content: str | None = None) -> SourceClassification:
        ats_name, confidence = self.ats_detector.detect(url, html_content)

        if ats_name and confidence >= settings.CONFIDENCE_THRESHOLD:
            logger.info(f"Source classified as ATS: {ats_name} (confidence: {confidence:.2f})")
            return SourceClassification(
                source_type="ats",
                ats=ats_name,
                confidence=confidence,
            )

        # Check if URL looks directly like a JSON API
        if url.endswith(".json") or "/api/" in url.lower() or "/v1/" in url.lower():
            logger.info(f"Source classified as potential API: {url}")
            return SourceClassification(
                source_type="api",
                ats=None,
                confidence=0.7,
            )

        # Default fallback classification when unknown
        return SourceClassification(
            source_type="unknown",
            ats=None,
            confidence=0.0,
        )

    def classify_chain(self, redirect_chain: list[str], html_content: str | None = None) -> tuple[SourceClassification, str]:
        """
        Classifies URLs across the redirect chain. If any URL in the chain is an ATS,
        returns that classification and the matching URL.
        """
        for url in redirect_chain:
            classification = self.classify(url, html_content)
            if classification.source_type == "ats":
                return classification, url

        final_url = redirect_chain[-1] if redirect_chain else ""
        return self.classify(final_url, html_content), final_url
