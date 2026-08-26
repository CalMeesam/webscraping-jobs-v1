"""Search for real JazzHR career pages by trying different URL patterns."""

import asyncio
from playwright.async_api import async_playwright
import json

async def find_real_jazzhr_boards():
    """Try to find actual JazzHR job boards with different URL patterns."""
    
    # JazzHR boards can be at:
    # 1. {company}.applytojob.com/apply/{jobid}
    # 2. {company}.jazz.co
    # 3. Embedded in company websites
    
    # Try companies that might use JazzHR (smaller to mid-size companies)
    companies = [
        "jazzhr",  # JazzHR's own careers
        "teachaway",
        "brightwheel",
        "grammarly",
        "outreach",
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        api_calls = []
        
        async def handle_response(response):
            url = response.url
            # Capture any JSON responses
            if "json" in response.headers.get("content-type", ""):
                if "applytojob.com" in url or "jazz" in url.lower():
                    try:
                        body = await response.json()
                        api_calls.append({
                            "url": url,
                            "status": response.status,
                            "body": body
                        })
                        print(f"📥 {response.status} {url[:80]}")
                        if isinstance(body, list):
                            print(f"   List with {len(body)} items")
                        elif isinstance(body, dict):
                            print(f"   Dict with keys: {list(body.keys())[:5]}")
                    except:
                        pass
        
        page.on("response", handle_response)
        
        # Try direct board URLs
        for company in companies:
            # Pattern 1: applytojob.com
            urls_to_try = [
                f"https://{company}.applytojob.com/apply",
                f"https://jobs.{company}.com",
                f"https://{company}.com/careers",
            ]
            
            for url in urls_to_try:
                try:
                    print(f"\n🔍 Trying: {url}")
                    await page.goto(url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_timeout(2000)
                    
                    # Check for job listings
                    jobs = await page.locator("[class*='job'], [class*='position'], .listing").count()
                    if jobs > 0:
                        print(f"✅ Found {jobs} job elements!")
                        
                        # Get page HTML to inspect
                        content = await page.content()
                        
                        # Save for inspection
                        with open("scratch/jazzhr_page_sample.html", "w", encoding="utf-8") as f:
                            f.write(content)
                        
                        if api_calls:
                            with open("scratch/jazzhr_api_calls.json", "w", encoding="utf-8") as f:
                                json.dump(api_calls, f, indent=2)
                            print(f"\n✅ Captured {len(api_calls)} API calls")
                            print(f"✅ Saved to scratch/jazzhr_api_calls.json")
                            
                            await browser.close()
                            return True
                
                except Exception as e:
                    if "net::ERR_NAME_NOT_RESOLVED" not in str(e):
                        print(f"   ⚠️ {e}")
        
        await browser.close()
        
        # If we got here, try searching for actual JazzHR examples
        print("\n" + "="*80)
        print("Searching for real JazzHR boards online...")
        print("="*80)
        
        return False

if __name__ == "__main__":
    success = asyncio.run(find_real_jazzhr_boards())
    if not success:
        print("\n⚠️ Could not find active JazzHR boards automatically")
        print("\nManual search needed:")
        print("1. Visit https://www.jazzhr.com/customers to find companies using JazzHR")
        print("2. Or search Google for 'applytojob.com' to find active boards")
