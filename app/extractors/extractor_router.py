"""Extractor Router module."""

import httpx
from app.core.constants import ERROR_ATS_DETECTED_BUT_UNSUPPORTED, SUPPORTED_ATS_VENDORS
from app.core.logging import get_logger
from app.extractors.ats.greenhouse import GreenhouseExtractor
from app.extractors.ats.oracle_hcm import OracleHCMExtractor
from app.extractors.ats.unsupported_ats import UnsupportedATSExtractor
from app.extractors.ats.workday import WorkdayExtractor
from app.extractors.base_extractor import BaseExtractor
from app.extractors.generic.api_extractor import APIExtractor
from app.extractors.generic.html_extractor import HTMLExtractor
from app.extractors.generic.playwright_extractor import PlaywrightExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob

logger = get_logger(__name__)


class ExtractorRouter:
    """Selects and executes the appropriate job extractor based on SourceClassification."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.greenhouse_extractor = GreenhouseExtractor(client=client)
        self.workday_extractor = WorkdayExtractor(client=client)
        self.oracle_hcm_extractor = OracleHCMExtractor(client=client)
        self.unsupported_ats_extractor = UnsupportedATSExtractor()
        self.html_extractor = HTMLExtractor(client=client)
        self.api_extractor = APIExtractor()
        self.playwright_extractor = PlaywrightExtractor()

    async def close(self) -> None:
        """Closes resources like Playwright browser."""
        await self.playwright_extractor.close()

    async def route_and_extract(
        self,
        url: str,
        classification: SourceClassification,
        context: ExtractionContext,
    ) -> list[RawJob]:
        # Branch 1: Known ATS
        if classification.source_type == "ats":
            ats_vendor = classification.ats
            context.ats = ats_vendor

            if ats_vendor == "greenhouse":
                logger.info("Routing to GreenhouseExtractor")
                context.strategy_used.append("greenhouse_api")
                return await self.greenhouse_extractor.extract(url, context)

            elif ats_vendor == "workday":
                logger.info("Routing to WorkdayExtractor")
                context.strategy_used.append("workday_cxs_api")
                return await self.workday_extractor.extract(url, context)

            elif ats_vendor == "oracle_hcm":
                logger.info("Routing to OracleHCMExtractor")
                context.strategy_used.append("oracle_hcm_api")
                return await self.oracle_hcm_extractor.extract(url, context)

            else:
                logger.info(f"Routing to UnsupportedATSExtractor for ATS '{ats_vendor}'")
                context.strategy_used.append("unsupported_ats")
                return await self.unsupported_ats_extractor.extract(url, context)

        # Branch 2: Discovered API
        if classification.source_type == "api":
            logger.info("Routing to APIExtractor")
            context.strategy_used.append("discovered_api")
            return await self.api_extractor.extract(url, context)

        # Branch 3: Static HTML / Unknown -> Static HTML Extractor first
        logger.info("Routing to HTMLExtractor")
        context.strategy_used.append("static_html")
        raw_jobs = await self.html_extractor.extract(url, context)
        if raw_jobs:
            return raw_jobs

        # Branch 4: Playwright Browser Fallback
        # Trigger condition per Section 15: 0 jobs from static/API and source is non-ATS
        logger.info("Static HTML yielded 0 jobs. Routing to PlaywrightExtractor fallback")
        context.strategy_used.append("playwright_fallback")
        playwright_jobs = await self.playwright_extractor.extract(url, context)
        return playwright_jobs
