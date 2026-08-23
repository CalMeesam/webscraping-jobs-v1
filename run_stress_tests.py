"""Stress & Edge-Case Test Verification Script for Adaptive Career Job Extraction Engine."""

import asyncio
import json
import logging
import time
import httpx
from app.extractors.ats.greenhouse import GreenhouseExtractor
from app.enrichment.detail_enricher import DetailEnricher
from app.models.extraction_models import ExtractionContext
from app.models.raw_job import RawJob
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress_tests")


async def test_1_partial_enrichment_failure():
    logger.info("=== RUNNING TEST 1: PARTIAL ENRICHMENT FAILURE ===")
    manager = ExtractionManager()
    req = ExtractionRequest(
        url="https://boards.greenhouse.io/figma",
        max_jobs=5,
        include_details=False,
    )
    res = await manager.extract_jobs(req)
    
    raw_jobs = [
        RawJob(
            source_id="INVALID_JOB_ID_9999991" if i in (1, 3) else j.id,
            title=j.title,
            job_url=j.job_url,
            source_url="https://boards.greenhouse.io/figma",
            ats="greenhouse",
            location=j.location.raw if j.location else None,
        )
        for i, j in enumerate(res.jobs)
    ]

    context = ExtractionContext(
        request_id="test-partial-fail-123",
        input_url="https://boards.greenhouse.io/figma",
        resolved_url="https://boards.greenhouse.io/figma",
        include_details=True,
    )

    enricher = DetailEnricher()
    enriched_jobs = await enricher.enrich(raw_jobs, context)

    result = {
        "metadata": {
            "jobs_discovered": 5,
            "jobs_returned": len(enriched_jobs),
            "jobs_enrichment_attempted": context.jobs_enrichment_attempted,
            "jobs_enriched": context.jobs_enriched,
            "jobs_enrichment_failed": context.jobs_enrichment_failed,
        },
        "jobs_summary": [
            {
                "index": i,
                "id": j.source_id,
                "title": j.title,
                "is_enriched": j.is_enriched,
                "enrichment_error": j.enrichment_error,
                "has_description": bool(j.description_html or j.description_text),
            }
            for i, j in enumerate(enriched_jobs)
        ],
    }

    return result


async def test_2_concurrency_at_scale():
    logger.info("=== RUNNING TEST 2: CONCURRENCY AT SCALE (max_jobs=25, include_details=true) ===")
    manager = ExtractionManager()
    
    active_requests = 0
    max_concurrent_observed = 0

    original_enrich = DetailEnricher.enrich_single_job

    async def tracked_enrich_single_job(self, job, client, semaphore):
        nonlocal active_requests, max_concurrent_observed
        async with semaphore:
            active_requests += 1
            if active_requests > max_concurrent_observed:
                max_concurrent_observed = active_requests
            try:
                res = await original_enrich(self, job, client, asyncio.Semaphore(1))
            finally:
                active_requests -= 1
            return res

    DetailEnricher.enrich_single_job = tracked_enrich_single_job

    req = ExtractionRequest(
        url="https://boards.greenhouse.io/figma",
        max_jobs=25,
        include_details=True,
    )

    t0 = time.perf_counter()
    res = await manager.extract_jobs(req)
    t1 = time.perf_counter()

    wall_clock_time = round(t1 - t0, 3)

    DetailEnricher.enrich_single_job = original_enrich

    all_enriched = all(j.description is not None for j in res.jobs)
    enriched_count = sum(1 for j in res.jobs if j.description is not None)

    result = {
        "wall_clock_seconds": wall_clock_time,
        "max_concurrent_requests_observed": max_concurrent_observed,
        "total_jobs_returned": len(res.jobs),
        "jobs_enriched_count": enriched_count,
        "all_25_got_descriptions": all_enriched,
        "metadata": res.metadata.model_dump(),
    }

    return result, res


async def test_3_include_details_false_verification():
    logger.info("=== RUNNING TEST 3: INCLUDE_DETAILS=FALSE EXPLICIT VERIFICATION ===")
    manager = ExtractionManager()
    
    req = ExtractionRequest(
        url="https://boards.greenhouse.io/figma",
        max_jobs=25,
        include_details=False,
    )

    t0 = time.perf_counter()
    res = await manager.extract_jobs(req)
    t1 = time.perf_counter()

    wall_clock_time = round(t1 - t0, 3)

    result = {
        "wall_clock_seconds": wall_clock_time,
        "detail_api_calls_made": res.metadata.jobs_enrichment_attempted,
        "total_jobs_returned": len(res.jobs),
        "metadata": res.metadata.model_dump(),
    }

    return result


async def test_4_cisco_edge_cases():
    logger.info("=== RUNNING TEST 4: CISCO EDGE-CASE ENTRY URLS ===")
    manager = ExtractionManager()
    
    urls_to_test = [
        "https://careers.cisco.com/global/en/job/1433061/Software-Engineer",
        "https://careers.cisco.com/global/en/search-results?keywords=engineering",
        "https://careers.cisco.com/global/en/c/engineering-jobs",
    ]

    results = []

    for entry_url in urls_to_test:
        logger.info(f"Testing Cisco Entry URL: {entry_url}")
        req = ExtractionRequest(
            url=entry_url,
            max_jobs=3,
            include_details=False,
        )
        try:
            t0 = time.perf_counter()
            res = await manager.extract_jobs(req)
            t1 = time.perf_counter()

            results.append({
                "entry_url": entry_url,
                "wall_clock_seconds": round(t1 - t0, 3),
                "full_response": res.model_dump(),
            })
        except Exception as e:
            results.append({
                "entry_url": entry_url,
                "error": str(e),
            })

    return results


async def main():
    print("Starting Stress & Edge Case Test Suite...\n")
    t1_res = await test_1_partial_enrichment_failure()
    t2_res, t2_payload = await test_2_concurrency_at_scale()
    t3_res = await test_3_include_details_false_verification()
    t4_res = await test_4_cisco_edge_cases()

    # Build report
    report_lines = []
    report_lines.append("# Stress & Edge-Case Verification Report")
    report_lines.append("**Adaptive Career Job Extraction Engine** — Concurrency, Partial Failures, and Edge-Case Routing\n")

    report_lines.append("## 1. Test 1: Partial Enrichment Failure Verification")
    report_lines.append("Corrupted job IDs `#1` and `#3` out of 5 Figma jobs to simulate partial HTTP/API detail failures.")
    report_lines.append("```json\n" + json.dumps(t1_res, indent=2) + "\n```\n")

    report_lines.append("## 2. Test 2: Concurrency at Scale (`max_jobs=25`, `include_details=true`)")
    report_lines.append(f"- **Wall-Clock Time**: `{t2_res['wall_clock_seconds']} seconds`")
    report_lines.append(f"- **Max Active Concurrent Requests Observed**: `{t2_res['max_concurrent_requests_observed']}` (Bounded by `Semaphore(5)`)")
    report_lines.append(f"- **Total Jobs Returned**: `{t2_res['total_jobs_returned']}`")
    report_lines.append(f"- **All 25 Jobs Enriched**: `{t2_res['all_25_got_descriptions']}`\n")
    report_lines.append("**Full Raw Uncurated Response Payload**:")
    report_lines.append("```json\n" + json.dumps(t2_payload.model_dump(), indent=2) + "\n```\n")

    report_lines.append("## 3. Test 3: `include_details=false` Speed & Zero-Call Verification")
    report_lines.append(f"- **Wall-Clock Time (`include_details=false`)**: `{t3_res['wall_clock_seconds']} seconds` (vs `{t2_res['wall_clock_seconds']}s` with details)")
    report_lines.append(f"- **Detail API Calls Attempted**: `{t3_res['detail_api_calls_made']}`")
    report_lines.append(f"- **Speedup**: `{round(t2_res['wall_clock_seconds'] / max(t3_res['wall_clock_seconds'], 0.001), 2)}x faster`\n")
    report_lines.append("**Metadata Response**:")
    report_lines.append("```json\n" + json.dumps(t3_res['metadata'], indent=2) + "\n```\n")

    report_lines.append("## 4. Test 4: Cisco Multi-Entry URL Routing & Uncurated Response Verification")
    report_lines.append("Tested 3 distinct Cisco entry URLs (direct job link, search query URL, and category URL).")
    report_lines.append("```json\n" + json.dumps(t4_res, indent=2) + "\n```\n")

    with open("EXECUTION_AND_TEST_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("\nAll stress tests completed and saved to EXECUTION_AND_TEST_REPORT.md!")

if __name__ == "__main__":
    asyncio.run(main())
