"""Quick platform functionality verification."""
import asyncio
import sys
sys.path.insert(0, r"d:\webscraping-jobs-v1")

from app.orchestrator.extraction_manager import ExtractionManager
from app.models.request_models import ExtractionRequest
from app.utils.customer_config import CustomerConfigManager


async def test_extractors():
    """Test that key extractors still work."""
    manager = ExtractionManager()
    
    print("="*70)
    print("PLATFORM FUNCTIONALITY VERIFICATION")
    print("="*70)
    
    # Test 1: Lever ATS (Spotify)
    print("\n[1/2] Testing Lever ATS Extractor (Spotify)...")
    lever_request = ExtractionRequest(url="https://jobs.lever.co/spotify", max_jobs=5)
    lever_result = await manager.extract_jobs(lever_request)
    
    lever_status = "✅ PASS" if len(lever_result.jobs) > 0 else "❌ FAIL"
    print(f"   {lever_status} - Extracted {len(lever_result.jobs)} jobs")
    print(f"   ATS: {lever_result.metadata.ats}")
    
    # Test 2: Customer Config Manager
    print("\n[2/2] Testing Customer Config Manager...")
    config_manager = CustomerConfigManager()
    config = config_manager.read_config()
    customers = config.get("customers", []) if isinstance(config, dict) else config
    
    config_status = "✅ PASS" if len(customers) > 0 else "❌ FAIL"
    print(f"   {config_status} - Found {len(customers)} customers")
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    all_pass = len(lever_result.jobs) > 0 and len(customers) > 0
    
    if all_pass:
        print("✅ All systems operational - platform is working correctly!")
    else:
        print("⚠️  Some issues detected - see details above")
    
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_extractors())
