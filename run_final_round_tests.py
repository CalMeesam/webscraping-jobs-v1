"""Final Round Test Verification Script for Adaptive Career Job Extraction Engine."""

import asyncio
import json
import logging
import time
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("final_round_tests")


async def run_final_tests():
    manager = ExtractionManager()
    
    test_cases = [
        {
            "name": "Cisco Bare Search Results",
            "request": ExtractionRequest(
                url="https://careers.cisco.com/global/en/search-results",
                max_jobs=25,
                include_details=True,
            ),
        },
        {
            "name": "Dell Oracle HCM Platform",
            "request": ExtractionRequest(
                url="https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location",
                max_jobs=25,
                include_details=True,
            ),
        },
        {
            "name": "HPE Phenom Career Search Results",
            "request": ExtractionRequest(
                url="https://careers.hpe.com/us/en/search-results",
                max_jobs=25,
                include_details=True,
            ),
        },
    ]

    results = []

    for test in test_cases:
        req = test["request"]
        logger.info(f"Running Test: {test['name']} -> {req.url}")
        
        t0 = time.perf_counter()
        try:
            res = await manager.extract_jobs(req)
            t1 = time.perf_counter()
            wall_time = round(t1 - t0, 3)

            results.append({
                "test_name": test["name"],
                "url": str(req.url),
                "wall_clock_seconds": wall_time,
                "source_type": res.metadata.source_type,
                "ats": res.metadata.ats,
                "extraction_strategy": res.metadata.extraction_strategy,
                "total_jobs_found": res.metadata.total_jobs_found,
                "total_jobs_returned": res.metadata.total_jobs_returned,
                "warnings": res.metadata.warnings,
                "errors": res.metadata.errors,
                "full_response": res.model_dump(),
            })
        except Exception as e:
            t1 = time.perf_counter()
            wall_time = round(t1 - t0, 3)
            results.append({
                "test_name": test["name"],
                "url": str(req.url),
                "wall_clock_seconds": wall_time,
                "error_exception": str(e),
            })

    # Save to report
    report_lines = []
    report_lines.append("# Final Round Test Verification Report")
    report_lines.append("**Adaptive Career Job Extraction Engine** — Cisco, Dell, and HPE Deep Verification\n")

    for idx, r in enumerate(results, 1):
        report_lines.append(f"## {idx}. Test {idx}: {r['test_name']}")
        report_lines.append(f"- **Input URL**: `{r['url']}`")
        report_lines.append(f"- **Wall-Clock Time**: `{r['wall_clock_seconds']} seconds`")
        
        if "full_response" in r:
            meta = r["full_response"]["metadata"]
            report_lines.append(f"- **Source Type**: `{meta['source_type']}`")
            report_lines.append(f"- **ATS Detected**: `{meta['ats']}`")
            report_lines.append(f"- **Extraction Strategy**: `{meta['extraction_strategy']}`")
            report_lines.append(f"- **Total Jobs Found**: `{meta['total_jobs_found']}`")
            report_lines.append(f"- **Total Jobs Returned**: `{meta['total_jobs_returned']}`")
            report_lines.append(f"- **Warnings**: `{meta['warnings']}`")
            report_lines.append(f"- **Errors**: `{meta['errors']}`\n")
            report_lines.append("**Full Raw Uncurated Response Payload**:")
            report_lines.append("```json\n" + json.dumps(r["full_response"], indent=2) + "\n```\n")
        else:
            report_lines.append(f"- **Exception Caught**: `{r.get('error_exception')}`\n")

        report_lines.append("---\n")

    with open("EXECUTION_AND_TEST_REPORT.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print("\nFinal round tests completed and saved to EXECUTION_AND_TEST_REPORT.md!")


if __name__ == "__main__":
    asyncio.run(run_final_tests())
