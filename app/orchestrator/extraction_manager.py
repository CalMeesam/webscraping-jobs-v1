"""Extraction Manager / Orchestrator module."""

import httpx
from app.core.config import settings
from app.core.constants import ERROR_CAREER_PAGE_NOT_FOUND, ERROR_NO_JOBS_FOUND
from app.core.logging import get_logger
from app.discovery.career_discovery import CareerDiscovery
from app.discovery.source_classifier import SourceClassifier
from app.discovery.url_resolver import URLResolver
from app.enrichment.detail_enricher import DetailEnricher
from app.extractors.extractor_router import ExtractorRouter
from app.extractors.generic.html_extractor import HTMLExtractor
from app.extractors.generic.playwright_extractor import PlaywrightExtractor
from app.models.extraction_models import ExtractionContext
from app.models.raw_job import RawJob
from app.models.request_models import ExtractionRequest
from app.models.response_models import ExtractionMetadata, ExtractionResponse
from app.normalization.job_normalizer import JobNormalizer
from app.processing.deduplicator import Deduplicator
from app.utils.url_utils import clean_url

logger = get_logger(__name__)


class ExtractionManager:
    """Central Orchestrator for discovery, extraction, enrichment, normalization, and deduplication."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client
        self.url_resolver = URLResolver(client=client)
        self.classifier = SourceClassifier()
        self.career_discovery = CareerDiscovery(client=client)
        self.extractor_router = ExtractorRouter(client=client)
        self.html_extractor = HTMLExtractor(client=client)
        self.playwright_extractor = PlaywrightExtractor()
        self.detail_enricher = DetailEnricher(client=client)
        self.normalizer = JobNormalizer()
        self.deduplicator = Deduplicator()

    async def process_discovered_url(
        self,
        url: str,
        context: ExtractionContext,
        depth: int = 0,
        redirect_chain: list[str] | None = None,
    ) -> list[RawJob]:
        """
        Bounded recursive URL processor enforcing termination conditions:
        1. Max depth limit (MAX_DISCOVERY_DEPTH = 3)
        2. Cycle detection (already in visited_urls)
        3. Max total visited limit (MAX_VISITED_URLS = 20)
        """
        cleaned = clean_url(url)
        if not cleaned:
            return []

        # Termination Check 1: Max depth
        if depth >= settings.MAX_DISCOVERY_DEPTH:
            msg = f"Max discovery depth ({settings.MAX_DISCOVERY_DEPTH}) reached at URL: {cleaned}"
            logger.warning(msg)
            context.warnings.append(msg)
            return []

        # Termination Check 2: Cycle detection
        if cleaned in context.visited_urls:
            logger.info(f"Skipping already visited URL: {cleaned}")
            return []

        # Termination Check 3: Max visited limit
        if len(context.visited_urls) >= settings.MAX_VISITED_URLS:
            msg = f"Max total visited URLs limit ({settings.MAX_VISITED_URLS}) reached"
            logger.warning(msg)
            context.warnings.append(msg)
            return []

        context.visited_urls.add(cleaned)
        logger.info(f"Processing URL (depth {depth}): {cleaned}")

        # Classify URL (checking redirect chain if available)
        chain_urls = redirect_chain if redirect_chain else [cleaned]
        classification, target_url = self.classifier.classify_chain(chain_urls)

        # If ATS or API, route to specific extractor directly
        if classification.source_type in ("ats", "api"):
            logger.info(f"Target is {classification.source_type.upper()} ({classification.ats}) at {target_url}. Extracting...")
            return await self.extractor_router.route_and_extract(target_url, classification, context)

        # Try Static HTML / JSON-LD extraction on current page
        context.strategy_used.append("static_html")
        raw_jobs = await self.html_extractor.extract(cleaned, context)
        if raw_jobs:
            return raw_jobs

        # Pre-Discovery Guardrail: If current URL itself is already a candidate career/job page,
        # run Playwright fallback ON ITSELF FIRST before attempting child link discovery.
        if self.career_discovery.is_candidate_career_url(cleaned) and "playwright_fallback" not in context.strategy_used:
            logger.info(f"URL {cleaned} is already a candidate career page. Running Playwright fallback on target URL first.")
            context.strategy_used.append("playwright_fallback")
            playwright_jobs = await self.playwright_extractor.extract(cleaned, context)
            if playwright_jobs:
                return playwright_jobs

        # If static HTML AND target page Playwright yielded 0 jobs, search for candidate career URLs
        logger.info(f"Searching for candidate career links from: {cleaned}")
        candidate_urls = await self.career_discovery.discover_career_urls(cleaned)

        if candidate_urls:
            all_discovered_jobs: list[RawJob] = []
            for candidate_url in candidate_urls:
                if context.max_jobs is not None and len(all_discovered_jobs) >= context.max_jobs:
                    break
                # Recurse into candidate career URL
                jobs = await self.process_discovered_url(candidate_url, context, depth + 1)
                all_discovered_jobs.extend(jobs)
                if all_discovered_jobs:
                    return all_discovered_jobs

        # Final Fallback Playwright if not run yet
        if "playwright_fallback" not in context.strategy_used:
            logger.info(f"Triggering Playwright fallback for {cleaned}")
            context.strategy_used.append("playwright_fallback")
            playwright_jobs = await self.playwright_extractor.extract(cleaned, context)
            return playwright_jobs

        return []

    async def extract_jobs(self, request: ExtractionRequest) -> ExtractionResponse:
        context = ExtractionContext(
            input_url=request.url,
            max_jobs=request.max_jobs,
            include_details=request.include_details,
            preferred_location=request.preferred_location,
        )

        logger.info(f"Starting job extraction workflow for input URL: {request.url}")

        # Step 1: Resolve URL & follow redirects
        resolved = await self.url_resolver.resolve(request.url)
        context.resolved_url = resolved.final_url

        # Step 2: Bounded recursive discovery & listing extraction
        raw_jobs = await self.process_discovered_url(
            resolved.final_url,
            context,
            depth=0,
            redirect_chain=resolved.redirect_chain,
        )

        if not raw_jobs:
            if not context.errors:
                context.warnings.append("No job listings could be found for the given URL.")
                context.errors.append(ERROR_NO_JOBS_FOUND)

        # Step 3: Optional Preferred Location Stable Partition (Pure Post-Processing on raw_jobs)
        if request.preferred_location and request.preferred_location.strip():
            pref_loc_clean = request.preferred_location.strip().lower()
            logger.info(f"Applying stable partition for preferred_location: '{request.preferred_location}'")
            raw_jobs = sorted(
                raw_jobs,
                key=lambda j: pref_loc_clean in (j.location or "").lower(),
                reverse=True,
            )

        total_discovered = len(raw_jobs)
        total_found = context.total_jobs_found_override if context.total_jobs_found_override is not None else total_discovered

        # Step 4: Apply max_jobs bounding to raw_jobs BEFORE detail enrichment
        target_raw_jobs = raw_jobs
        if request.max_jobs is not None and request.max_jobs > 0:
            target_raw_jobs = raw_jobs[: request.max_jobs]

        # Step 5: Detail Enrichment (bounded by max_jobs)
        if target_raw_jobs and request.include_details:
            target_raw_jobs = await self.detail_enricher.enrich(target_raw_jobs, context)

        # Step 6: Normalization
        normalized_jobs = self.normalizer.normalize(target_raw_jobs)

        # Step 7: Deduplication
        deduped_jobs = self.deduplicator.remove_duplicates(normalized_jobs)

        # Step 8: Build Metadata with Enrichment Metrics
        metadata = ExtractionMetadata(
            input_url=request.url,
            resolved_url=resolved.final_url,
            career_url=list(context.visited_urls)[1] if len(context.visited_urls) > 1 else resolved.final_url,
            job_source_url=resolved.final_url,
            source_type=context.strategy_used[0] if context.strategy_used else "unknown",
            ats=context.ats,
            extraction_strategy=" -> ".join(context.strategy_used) if context.strategy_used else "none",
            visited_urls=list(context.visited_urls),
            total_jobs_found=total_found,
            total_jobs_returned=len(deduped_jobs),
            jobs_discovered=total_discovered,
            jobs_returned=len(deduped_jobs),
            jobs_enrichment_attempted=context.jobs_enrichment_attempted,
            jobs_enriched=context.jobs_enriched,
            jobs_enrichment_failed=context.jobs_enrichment_failed,
            warnings=context.warnings,
            errors=context.errors,
        )

        logger.info(f"Job extraction completed. Total found: {total_found}, Returned: {len(deduped_jobs)}")
        return ExtractionResponse(metadata=metadata, jobs=deduped_jobs)
