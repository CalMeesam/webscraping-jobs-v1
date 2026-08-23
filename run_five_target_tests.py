"""Run and report full uncurated output for all 5 target URLs."""

import asyncio
import json
import time
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager


TARGET_TESTS = [
    (
        "1. Dell Oracle HCM Platform",
        "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location",
        25,
    ),
    (
        "2. Cisco Phenom Career Search",
        "https://careers.cisco.com/global/en/search-results",
        25,
    ),
    (
        "3. Broadcom Workday External Career Site",
        "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        25,
    ),
    (
        "4. HPE Phenom Career Search",
        "https://careers.hpe.com/us/en/search-results",
        25,
    ),
    (
        "5. IP Infusion Careers Site",
        "https://www.ipinfusion.com/careers/",
        25,
    ),
]


async def run_all_five():
    manager = ExtractionManager()
    results = {}

    for name, url, max_j in TARGET_TESTS:
        print(f"\n========================================================")
        print(f"RUNNING TEST: {name}")
        print(f"URL: {url}")
        print(f"========================================================")
        start_time = time.time()
        req = ExtractionRequest(
            url=url,
            max_jobs=max_j,
            include_details=True,
            preferred_location=None,
        )
        res = await manager.extract_jobs(req)
        elapsed = time.time() - start_time
        res_dict = res.model_dump()
        results[name] = {
            "elapsed_seconds": round(elapsed, 3),
            "response": res_dict,
        }
        print(f"Elapsed Time: {elapsed:.3f}s")
        print(f"Jobs Returned: {len(res_dict['jobs'])}")
        print("FULL UNCURATED RESPONSE JSON:")
        print(json.dumps(res_dict, indent=2))

    # Save to JSON file for report verification
    with open("five_target_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nSaved all 5 test outputs to five_target_results.json")


if __name__ == "__main__":
    asyncio.run(run_all_five())
