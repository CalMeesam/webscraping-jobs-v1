"""Test Lever integration end-to-end through the API."""
import asyncio
import httpx
import json

async def test_lever_via_api():
    """Test Lever extraction through FastAPI endpoint."""
    
    # Ensure FastAPI server is running
    api_base = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test Lever extraction via API
        response = await client.post(
            f"{api_base}/api/extract",
            json={
                "url": "https://jobs.lever.co/spotify",
                "max_jobs": 10
            }
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 Results:")
            print(f"   Total jobs found: {data['metadata']['total_jobs_found']}")
            print(f"   Total jobs returned: {data['metadata']['total_jobs_returned']}")
            print(f"   ATS: {data['metadata']['ats']}")
            print(f"   Strategy used: {data['metadata']['strategy_used']}")
            
            if data['jobs']:
                print(f"\n📋 Sample job (first):")
                job = data['jobs'][0]
                print(f"   Title: {job['title']}")
                print(f"   Location: {job['location']['raw']}")
                print(f"   Department: {job['department']}")
                print(f"   Employment Type: {job['employment_type']}")
                print(f"   Workplace Type: {job['workplace_type']}")
                print(f"   URL: {job['job_url']}")
                print(f"   Description length: {len(job.get('description', ''))} chars")
            
            print("\n✅ Lever integration working via API!")
            return True
        else:
            print(f"❌ API error: {response.status_code}")
            print(response.text)
            return False

if __name__ == "__main__":
    success = asyncio.run(test_lever_via_api())
    if not success:
        print("\n⚠️ Make sure FastAPI server is running: uvicorn app.main:app")
