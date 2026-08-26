"""Use Playwright to inspect a real Lever careers page and capture API calls."""
import asyncio
from playwright.async_api import async_playwright
import json

async def inspect_lever_board():
    """Inspect a real Lever career page to understand the API structure."""
    
    # Known companies using Lever (as of 2024)
    test_urls = [
        "https://jobs.lever.co/reddit",
        "https://jobs.lever.co/vanta",
        "https://jobs.lever.co/plaid",
        "https://jobs.lever.co/figma",
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Collect API calls
        api_requests = []
        api_responses = []
        
        async def handle_request(request):
            if "api.lever.co" in request.url:
                api_requests.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers)
                })
                print(f"📤 API Request: {request.method} {request.url}")
        
        async def handle_response(response):
            if "api.lever.co" in response.url:
                try:
                    if "json" in response.headers.get("content-type", ""):
                        body = await response.json()
                        api_responses.append({
                            "url": response.url,
                            "status": response.status,
                            "body": body
                        })
                        print(f"📥 API Response: {response.status} {response.url}")
                        print(f"   Body type: {type(body)}, Length: {len(body) if isinstance(body, list) else 'N/A'}")
                except Exception as e:
                    print(f"   ⚠️ Could not parse response: {e}")
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        for test_url in test_urls:
            print(f"\n{'='*80}")
            print(f"Testing: {test_url}")
            print(f"{'='*80}\n")
            
            try:
                await page.goto(test_url, wait_until="networkidle", timeout=15000)
                await page.wait_for_timeout(2000)  # Wait for any delayed API calls
                
                # Check if jobs loaded
                jobs_found = await page.locator(".posting, .job-posting, [class*='job']").count()
                print(f"\n✅ Page loaded. Found {jobs_found} job elements on page.")
                
                if api_responses:
                    print(f"\n📊 Captured {len(api_responses)} API responses")
                    
                    # Save first response for analysis
                    if len(api_responses) > 0:
                        first_response = api_responses[0]
                        print(f"\n📋 First API Response:")
                        print(f"   URL: {first_response['url']}")
                        print(f"   Status: {first_response['status']}")
                        
                        body = first_response['body']
                        if isinstance(body, list) and len(body) > 0:
                            print(f"\n🔑 Sample job structure (first job):")
                            print(json.dumps(body[0], indent=2)[:2000])  # First 2000 chars
                            
                            # Save full response
                            company = test_url.split("/")[-1]
                            filename = f"lever_{company}_api_response.json"
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(body[:3], f, indent=2)  # Save first 3 jobs
                            print(f"\n✅ Saved first 3 jobs to: {filename}")
                            
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
    success = asyncio.run(inspect_lever_board())
    if success:
        print("\n✅ Lever API structure verified via network inspection")
    else:
        print("\n❌ Could not capture Lever API calls")
