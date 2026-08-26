"""Test enhanced HPE extraction with scrolling."""
import asyncio
import sys
sys.path.insert(0, r"d:\webscraping-jobs-v1")

from app.orchestrator.extraction_manager import ExtractionManager
from app.models.request_models import ExtractionRequest
from app.models.normalized_job import JobLocation
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_hpe_extraction():
    manager = ExtractionManager()
    
    url = "https://careers.hpe.com/us/en/search-results"
    request = ExtractionRequest(url=url)
    
    print(f"Testing enhanced extraction on: {url}")
    print("="*70)
    
    result = await manager.extract_jobs(request)
    
    print(f"\nResults:")
    print(f"  Jobs extracted: {len(result.jobs)}")
    print(f"  Total found: {result.metadata.total_jobs_found}")
    print(f"  ATS: {result.metadata.ats}")
    print(f"  Extraction strategy: {result.metadata.extraction_strategy}")
    print(f"  Errors: {result.metadata.errors}")
    print(f"  Warnings: {len(result.metadata.warnings)} warnings")
    
    if result.jobs:
        print(f"\nFirst 3 jobs:")
        for i, job in enumerate(result.jobs[:3], 1):
            location = job.location.raw if isinstance(job.location, JobLocation) else job.location if job.location else "N/A"
            print(f"  {i}. {job.title} - {location}")
        
        if len(result.jobs) > 3:
            print(f"\n  ... and {len(result.jobs) - 3} more jobs")
    
    print("\n" + "="*70)
    if len(result.jobs) > 5:
        print(f"✅ SUCCESS: Enhanced scrolling captured {len(result.jobs)} jobs (was 5 before)")
    else:
        print(f"⚠️  Still only {len(result.jobs)} jobs extracted")


if __name__ == "__main__":
    asyncio.run(test_hpe_extraction())
