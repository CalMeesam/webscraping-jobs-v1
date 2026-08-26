"""Test JazzHR API endpoints directly."""

import asyncio
import httpx
import json

async def test_jazzhr_api():
    """Test various JazzHR API patterns."""
    
    # JazzHR might have API patterns similar to other ATS
    test_companies = ["jazzhr", "teachaway", "brightwheel"]
    
    api_patterns = [
        "https://api.jazz.co/v1/{company}/jobs",
        "https://api.applytojob.com/{company}/jobs",
        "https://{company}.applytojob.com/api/jobs",
        "https://{company}.applytojob.com/api/positions",
        "https://{company}.jazz.co/api/jobs",
    ]
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for company in test_companies:
            print(f"\n{'='*80}")
            print(f"Testing company: {company}")
            print(f"{'='*80}")
            
            for pattern in api_patterns:
                url = pattern.format(company=company)
                print(f"\n🔍 {url}")
                
                try:
                    r = await client.get(url)
                    print(f"   Status: {r.status_code}")
                    
                    if r.status_code == 200:
                        content_type = r.headers.get("content-type", "")
                        if "json" in content_type:
                            data = r.json()
                            print(f"   ✅ JSON response!")
                            print(f"   Type: {type(data)}")
                            if isinstance(data, list):
                                print(f"   Length: {len(data)}")
                                if len(data) > 0:
                                    print(f"\n   Sample item:")
                                    print(json.dumps(data[0], indent=2)[:500])
                                    
                                    # Save it
                                    with open("scratch/jazzhr_api_response.json", "w") as f:
                                        json.dump(data[:3], f, indent=2)
                                    print(f"\n   ✅ Saved to scratch/jazzhr_api_response.json")
                                    return True
                            elif isinstance(data, dict):
                                print(f"   Keys: {list(data.keys())[:10]}")
                                if any(key in data for key in ["jobs", "positions", "openings", "postings"]):
                                    print(f"   ✅ Found job data!")
                                    print(json.dumps(data, indent=2)[:500])
                                    
                                    with open("scratch/jazzhr_api_response.json", "w") as f:
                                        json.dump(data, f, indent=2)
                                    print(f"\n   ✅ Saved to scratch/jazzhr_api_response.json")
                                    return True
                    elif r.status_code == 404:
                        print(f"   404 Not Found")
                    else:
                        print(f"   {r.status_code}: {r.text[:100]}")
                
                except httpx.ConnectError:
                    print(f"   ❌ Cannot connect")
                except Exception as e:
                    print(f"   ❌ {type(e).__name__}: {str(e)[:50]}")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_jazzhr_api())
    if not success:
        print("\n❌ Could not find public JazzHR API")
        print("\nJazzHR likely requires:")
        print("1. Scraping the HTML page directly")
        print("2. Or using Playwright to capture client-side API calls")
        print("3. Or may not have a public API like Greenhouse/Lever")
