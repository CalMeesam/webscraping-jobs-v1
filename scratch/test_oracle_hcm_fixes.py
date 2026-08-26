"""Test Oracle HCM fixes: pagination and detail enrichment."""
import asyncio
import json
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager

async def test_oracle_hcm_fixes():
    """Test Oracle HCM with max_jobs=50 to verify pagination and detail enrichment."""
    
    # Test Dell Oracle HCM with higher max_jobs to test pagination
    manager = ExtractionManager()
    
    request = ExtractionRequest(
        url="https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location",
        max_jobs=50,  # Increased from 25 to test pagination
        include_details=True
    )
    
    print("🔍 Testing Oracle HCM with max_jobs=50...")
    print(f"   URL: {request.url}")
    print(f"   max_jobs: {request.max_jobs}")
    print(f"   include_details: {request.include_details}")
    print()
    
    response = await manager.extract_jobs(request)
    
    print(f"\n📊 Results:")
    print(f"   Total jobs found: {response.metadata.total_jobs_found}")
    print(f"   Total jobs returned: {response.metadata.total_jobs_returned}")
    print(f"   Jobs enrichment attempted: {response.metadata.jobs_enrichment_attempted}")
    print(f"   Jobs enriched: {response.metadata.jobs_enriched}")
    print(f"   Jobs enrichment failed: {response.metadata.jobs_enrichment_failed}")
    print()
    
    # Check pagination fix
    if response.metadata.total_jobs_returned > 25:
        print("✅ PAGINATION FIX VERIFIED: Returned more than 25 jobs (first page limit)")
    else:
        print("⚠️ PAGINATION: Returned 25 or fewer jobs")
    
    # Check detail enrichment fix by examining first few jobs
    jobs_with_full_desc = 0
    jobs_with_sections = 0
    jobs_with_skills = 0
    
    for i, job in enumerate(response.jobs[:5]):  # Check first 5 jobs
        has_full_desc = len(job.description) > 50 if job.description else False
        has_sections = len(job.responsibilities) > 0 or len(job.requirements) > 0
        has_skills = len(job.skills) > 0
        
        if has_full_desc:
            jobs_with_full_desc += 1
        if has_sections:
            jobs_with_sections += 1
        if has_skills:
            jobs_with_skills += 1
        
        print(f"\n   Job {i+1}: {job.title}")
        print(f"      Description length: {len(job.description) if job.description else 0} chars")
        print(f"      Responsibilities: {len(job.responsibilities)}")
        print(f"      Requirements: {len(job.requirements)}")
        print(f"      Skills: {len(job.skills)}")
    
    print()
    if jobs_with_full_desc >= 3:
        print(f"✅ DETAIL ENRICHMENT FIX VERIFIED: {jobs_with_full_desc}/5 jobs have full descriptions (>50 chars)")
    else:
        print(f"⚠️ DETAIL ENRICHMENT: Only {jobs_with_full_desc}/5 jobs have full descriptions")
    
    if jobs_with_sections >= 2:
        print(f"✅ SECTION PARSING VERIFIED: {jobs_with_sections}/5 jobs have parsed sections")
    else:
        print(f"⚠️ SECTION PARSING: Only {jobs_with_sections}/5 jobs have parsed sections")
    
    # Save sample to file for inspection
    sample_output = {
        "metadata": response.metadata.model_dump(),
        "sample_jobs": [job.model_dump() for job in response.jobs[:3]]
    }
    
    with open("oracle_hcm_fix_verification.json", "w", encoding="utf-8") as f:
        json.dump(sample_output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Sample output saved to: oracle_hcm_fix_verification.json")
    
    return response

if __name__ == "__main__":
    asyncio.run(test_oracle_hcm_fixes())
