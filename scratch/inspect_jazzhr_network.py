"""Find and inspect JazzHR career pages to understand their API structure.

JazzHR reconnaissance: Use Playwright to capture real API calls from a public
JazzHR-hosted career page, then document the actual response structure.
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def find_and_inspect_jazzhr():
    """Find a public JazzHR board and inspect its network calls."""
    
    # Known JazzHR career pages (typically at {company}.applytojob.com or {company}.jazz.co)
    test_urls = [
        "https://www.applytojob.com/apply",  # JazzHR main domain
        "https://clearbanc.applytojob.com/apply",
        "https://fullscript.applytojob.com/apply",
        "https://hootsuite.applytojob.com/apply",
        "https://jazzhr.applytojob.com/apply",  # JazzHR's own careers
    ]
    
    # Also try jazz.co domain
    jazz_co_urls = [
        "https://jobs.jazz.co/hootsuite",
        "https://jobs.jazz.co/jazzhr",
    ]
    
    all_urls = test_urls + jazz_co_urls
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Collect API calls
        api_requests = []
        api_responses = []
        
        async def handle_request(request):
            if "applytojob.com" in request.url or "jazz" in request.url.lower():
                if any(keyword in request.url.lower() for keyword in ["api", "job", "posting", "position", "career"]):
                    api_requests.append({
                        "url": request.url,
                        "method": request.method,
                        "headers": dict(request.headers)
                    })
                    print(f"📤 API Request: {request.method} {request.url}")
        
        async def handle_response(response):
            if "applytojob.com" in response.url or "jazz" in response.url.lower():
                if any(keyword in response.url.lower() for keyword in ["api", "job", "posting", "position", "career"]):
                    try:
                        content_type = response.headers.get("content-type", "")
                        if "json" in content_type:
                            body = await response.json()
                            api_responses.append({
                                "url": response.url,
                                "status": response.status,
                                "body": body
                            })
                            print(f"📥 API Response: {response.status} {response.url}")
                            print(f"   Body type: {type(body)}")
                            if isinstance(body, dict):
                                print(f"   Keys: {list(body.keys())[:10]}")
                            elif isinstance(body, list):
                                print(f"   Length: {len(body)}")
                    except Exception as e:
                        print(f"   ⚠️ Could not parse response: {e}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        for test_url in all_urls:
            print(f"\n{'='*80}")
            print(f"Testing: {test_url}")
            print(f"{'='*80}\n")
            
            try:
                await page.goto(test_url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(3000)  # Wait for any delayed API calls
                
                # Check if jobs loaded
                jobs_found = await page.locator("[class*='job'], [class*='position'], .listing, .posting").count()
                print(f"\n✅ Page loaded. Found {jobs_found} potential job elements on page.")
                
                if api_responses:
                    print(f"\n📊 Captured {len(api_responses)} API responses")
                    
                    # Save and analyze responses
                    for idx, resp in enumerate(api_responses):
                        print(f"\n{'='*60}")
                        print(f"API Response #{idx + 1}:")
                        print(f"URL: {resp['url']}")
                        print(f"Status: {resp['status']}")
                        
                        body = resp['body']
                        if isinstance(body, dict):
                            print(f"\nTop-level keys: {list(body.keys())}")
                            
                            # Look for job data
                            for key in body.keys():
                                if any(keyword in key.lower() for keyword in ["job", "position", "posting", "opening"]):
                                    print(f"\n🔑 Found job-related key: {key}")
                                    print(f"   Type: {type(body[key])}")
                                    if isinstance(body[key], list) and len(body[key]) > 0:
                                        print(f"   Length: {len(body[key])}")
                                        print(f"\n   Sample item structure:")
                                        print(json.dumps(body[key][0], indent=2)[:1000])
                        
                        elif isinstance(body, list) and len(body) > 0:
                            print(f"\nList with {len(body)} items")
                            print(f"\nSample item structure:")
                            print(json.dumps(body[0], indent=2)[:1000])
                    
                    # Save full response for later analysis
                    if api_responses:
                        filename = f"scratch/jazzhr_api_response.json"
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(api_responses, f, indent=2)
                        print(f"\n✅ Saved all responses to: {filename}")
                        
                        await browser.close()
                        return True
                else:
                    print("⚠️ No API calls captured")
                
                # Clear for next iteration
                api_requests.clear()
                api_responses.clear()
            
            except Exception as e:
                print(f"❌ Error loading page: {e}")
        
        await browser.close()
        return False

if __name__ == "__main__":
    success = asyncio.run(find_and_inspect_jazzhr())
    if success:
        print("\n✅ JazzHR API structure captured via network inspection")
    else:
        print("\n❌ Could not capture JazzHR API calls")
        print("\nNote: JazzHR boards may require specific company subdomains")
        print("Try manually visiting applytojob.com to find active boards")
