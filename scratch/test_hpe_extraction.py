"""Test HPE extraction to diagnose issue."""
import asyncio
from app.orchestrator.extraction_manager import ExtractionManager
from app.models.request_models import ExtractionRequest


async def test_hpe():
    manager = ExtractionManager()
    req = ExtractionRequest(
        url='https://careers.hpe.com/us/en/search-results',
        max_jobs=50
    )
    result = await manager.extract_jobs(req)
    
    print(f"\n=== HPE Extraction Results ===")
    print(f"Jobs Extracted: {len(result.jobs)}")
    print(f"Total Found: {result.metadata.total_jobs_found}")
    print(f"ATS Detected: {result.metadata.ats}")
    print(f"Strategy: {result.metadata.strategy_used}")
    print(f"Source: {result.metadata.source}")
    print(f"Errors: {result.metadata.errors}")
    
    if result.jobs:
        print(f"\nSample Job URLs:")
        for job in result.jobs[:3]:
            print(f"  - {job.job_url}")


if __name__ == "__main__":
    asyncio.run(test_hpe())
