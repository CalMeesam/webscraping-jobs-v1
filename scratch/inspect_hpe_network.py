"""Inspect HPE careers page to find API or pagination."""
import asyncio
from playwright.async_api import async_playwright


async def inspect_hpe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Set up network monitoring
        requests = []
        
        async def capture_request(request):
            if 'api' in request.url.lower() or 'job' in request.url.lower():
                requests.append({
                    'url': request.url,
                    'method': request.method,
                    'resource_type': request.resource_type
                })
        
        page.on('request', capture_request)
        
        print("Navigating to HPE careers page...")
        await page.goto('https://careers.hpe.com/us/en/search-results', wait_until='networkidle')
        
        # Wait a bit for lazy-loaded content
        await page.wait_for_timeout(3000)
        
        # Check for pagination or load more button
        print("\nChecking for pagination elements...")
        load_more = await page.query_selector('button:has-text("Load"), button:has-text("More"), button:has-text("Show")')
        pagination = await page.query_selector('[class*="paginat"], [class*="Paginat"]')
        
        if load_more:
            print(f"Found load more button: {await load_more.inner_text()}")
        if pagination:
            print(f"Found pagination element")
        
        # Get job count on page
        job_cards = await page.query_selector_all('[class*="job"], [class*="result"], article, [data-ph-at-id]')
        print(f"\nJob elements found: {len(job_cards)}")
        
        # Print API-like requests
        print("\n=== Potential API Requests ===")
        api_requests = [r for r in requests if r['resource_type'] in ['fetch', 'xhr']]
        for req in api_requests[:10]:
            print(f"{req['method']} {req['url'][:120]}")
        
        # Check page meta
        print("\n=== Page Meta ===")
        title = await page.title()
        print(f"Title: {title}")
        
        # Look for Phenom vendor signals
        phenom_script = await page.query_selector('script[src*="phenom"]')
        if phenom_script:
            print("✅ Detected Phenom ATS")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_hpe())
