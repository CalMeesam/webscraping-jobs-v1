"""Verify Lever API structure with a real public board."""
import asyncio
import httpx
import json

async def test_lever_api():
    """Test Lever's public API to understand the response structure."""
    
    # Test with a known public Lever board (e.g., Netflix uses Lever)
    test_companies = [
        "netflix",
        "grammarly",
        "lever"  # Lever's own careers page
    ]
    
    for company in test_companies:
        api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        
        print(f"\n{'='*80}")
        print(f"Testing Lever API for: {company}")
        print(f"URL: {api_url}")
        print(f"{'='*80}\n")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                r = await client.get(api_url)
                print(f"Status: {r.status_code}")
                print(f"Content-Type: {r.headers.get('content-type')}")
                
                if r.status_code == 200:
                    data = r.json()
                    print(f"Response type: {type(data)}")
                    print(f"Number of jobs: {len(data) if isinstance(data, list) else 'N/A'}")
                    
                    if isinstance(data, list) and len(data) > 0:
                        print(f"\n📋 Sample job structure (first job):")
                        sample = data[0]
                        print(json.dumps(sample, indent=2))
                        
                        print(f"\n🔑 Available fields in first job:")
                        for key in sample.keys():
                            value_type = type(sample[key]).__name__
                            value_preview = str(sample[key])[:100] if sample[key] else "None"
                            print(f"   - {key}: {value_type} = {value_preview}...")
                        
                        # Save full response for later reference
                        filename = f"lever_{company}_response.json"
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(data[:3], f, indent=2)  # Save first 3 jobs
                        print(f"\n✅ Saved first 3 jobs to: {filename}")
                        
                        return True  # Success, don't need to test more companies
                    else:
                        print("⚠️ No jobs in response")
                else:
                    print(f"❌ HTTP {r.status_code}: {r.text[:200]}")
            
            except Exception as e:
                print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_lever_api())
    if success:
        print("\n✅ Lever API structure verified and documented")
    else:
        print("\n❌ Could not verify Lever API structure")
