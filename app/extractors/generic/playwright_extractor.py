"""Playwright Browser Fallback Extractor."""

import asyncio
import json
import sys
import traceback
from typing import Any
from playwright.async_api import async_playwright, Browser, Page
from app.core.config import settings
from app.core.constants import CAREER_URL_KEYWORDS, ERROR_PLAYWRIGHT_FAILED
from app.core.logging import get_logger
from app.discovery.api_discovery import APIDiscovery
from app.extractors.base_extractor import BaseExtractor
from app.extractors.generic.api_extractor import APIExtractor
from app.extractors.generic.html_extractor import HTMLExtractor
from app.models.extraction_models import ExtractionContext, SourceClassification
from app.models.raw_job import RawJob

logger = get_logger(__name__)


class PlaywrightExtractor(BaseExtractor):
    """Playwright browser extractor with network inspection first, DOM fallback second."""

    def __init__(self):
        self.api_discovery = APIDiscovery()
        self.api_extractor = APIExtractor()
        self.html_extractor = HTMLExtractor()

    async def can_handle(self, url: str, classification: SourceClassification) -> bool:
        return True

    async def _scroll_to_load_all_jobs(self, page: Page, max_scrolls: int = 15) -> None:
        """
        Scroll page to trigger lazy-loaded job listings.
        
        Args:
            page: Playwright Page object
            max_scrolls: Maximum number of scroll attempts (default: 15)
        """
        previous_job_count = 0
        scroll_count = 0
        no_change_count = 0
        
        # Common selectors for job listings across different ATS platforms & SPAs (Phenom, Workday, etc.)
        job_selectors = [
            'a[href*="/job/"]',
            '[data-ph-at-id="job-title-text"]',
            '.jobs-list-item',
            '.job-tile',
            '.job-title',
            '[data-job-id]',
            '[data-qa="job-posting"]',
            '[class*="job-card"]',
            '[class*="job-item"]',
            '[class*="job-listing"]',
            '[class*="position"]',
            'article',
            '[role="article"]',
            'li[data-id]',
            '.job',
        ]
        
        while scroll_count < max_scrolls:
            # Get current job count using multiple selectors
            current_job_count = 0
            for selector in job_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > current_job_count:
                        current_job_count = count
                except Exception:
                    continue
            
            logger.debug(f"Scroll {scroll_count + 1}: Found {current_job_count} job elements")
            
            # If no jobs found yet, continue scrolling
            if current_job_count == 0:
                try:
                    await page.evaluate("window.scrollTo(0, document.body ? document.body.scrollHeight : 0)")
                except Exception:
                    pass
                await page.wait_for_timeout(1500)
                scroll_count += 1
                continue
            
            # If job count hasn't changed, increment no-change counter
            if current_job_count == previous_job_count:
                no_change_count += 1
                # Stop if count hasn't changed for 3 consecutive scrolls
                if no_change_count >= 3:
                    logger.info(f"No new jobs loaded after {no_change_count} scrolls. Total jobs: {current_job_count}")
                    break
            else:
                # Reset no-change counter if count increased
                no_change_count = 0
                logger.info(f"Loaded {current_job_count} jobs (was {previous_job_count})")
            
            previous_job_count = current_job_count
            
            # Scroll to bottom
            try:
                await page.evaluate("window.scrollTo(0, document.body ? document.body.scrollHeight : 0)")
            except Exception:
                pass

            
            # Wait for new content to load
            await page.wait_for_timeout(1500)
            
            # Try to click "Load More" or "Show More" buttons if present
            load_more_selectors = [
                'button:has-text("Load More")',
                'button:has-text("Show More")',
                'a:has-text("Load More")',
                'a:has-text("Show More")',
                '[data-qa="load-more"]',
                '.load-more',
                '.show-more',
            ]
            
            for selector in load_more_selectors:
                try:
                    load_more_btn = page.locator(selector).first
                    if await load_more_btn.is_visible(timeout=500):
                        await load_more_btn.click()
                        logger.info(f"Clicked '{selector}' button")
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue
            
            scroll_count += 1
        
        logger.info(f"Scrolling complete. Total scrolls: {scroll_count}, Final job count: {previous_job_count}")

    def _extract_sync(self, url: str, context: ExtractionContext) -> list[RawJob]:
        """Runs Playwright in an isolated thread with WindowsProactorEventLoopPolicy."""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        async def _async_worker():
            captured_api_json: list[dict] = []
            async with async_playwright() as p:
                browser: Browser = await p.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
                page: Page = await browser.new_page()

                logger.info(f"Inspecting network XHR/Fetch traffic during page load for: {url}")

                async def handle_response(response):
                    try:
                        res_url = response.url.lower()
                        if any(kw in res_url for kw in CAREER_URL_KEYWORDS) or "api" in res_url or "search" in res_url or "jobs" in res_url or "widgets" in res_url or "requisitions" in res_url:
                            content_type = response.headers.get("content-type", "")
                            if "json" in content_type:
                                data = await response.json()
                                if self.api_discovery.validate_job_schema(data):
                                    logger.info(f"Playwright intercepted validated job API call: {response.url}")
                                    captured_api_json.append(data)
                    except Exception:
                        pass

                page.on("response", handle_response)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=settings.PLAYWRIGHT_TIMEOUT_MS)
                    # Allow dynamic SPA widgets (Phenom, Vue3, React) to render jobs into DOM
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    logger.warning(f"Playwright navigation notice for {url}: {e}")
                    await page.wait_for_timeout(3500)

                # Step 5: If XHR API captured, prefer it over DOM scraping
                if captured_api_json:
                    logger.info(f"Extracting from {len(captured_api_json)} Playwright network-intercepted JSON API response(s)")
                    raw_jobs: list[RawJob] = []
                    for json_payload in captured_api_json:
                        jobs = await self.api_extractor.extract(url, context, json_data=json_payload)
                        raw_jobs.extend(jobs)
                    if raw_jobs:
                        await browser.close()
                        return raw_jobs

                # Step 5.5: Scroll to trigger lazy-loaded content (for Phenom, Oracle JET, etc.)
                logger.info("Scrolling page to trigger lazy-loaded job listings...")
                await self._scroll_to_load_all_jobs(page)

                # Step 6: Post-render DOM fallback extraction
                logger.info("No valid XHR/Fetch job API payload intercepted during page load. Falling back to post-rendered HTML DOM extraction")
                rendered_html = await page.content()
                await browser.close()

                dom_jobs = await self.html_extractor.extract(url, context, html_content=rendered_html)
                return dom_jobs

        return asyncio.run(_async_worker())

    async def extract(
        self,
        url: str,
        context: ExtractionContext,
    ) -> list[RawJob]:
        logger.info(f"Triggering Playwright browser fallback for URL: {url}")

        try:
            # Delegate Playwright execution to a dedicated thread to ensure ProactorEventLoop on Windows Uvicorn
            raw_jobs = await asyncio.to_thread(self._extract_sync, url, context)
            return raw_jobs

        except Exception as e:
            exc_type = type(e).__name__
            exc_details = str(e).strip() or repr(e)
            tb = traceback.format_exc()
            err_msg = f"Playwright extraction failed for {url} [{exc_type}]: {exc_details}"
            logger.error(f"{err_msg}\nTraceback:\n{tb}")
            context.errors.append(ERROR_PLAYWRIGHT_FAILED)
            context.warnings.append(err_msg)
            return []
