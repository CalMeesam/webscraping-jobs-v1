"""Debug HPE page structure during scrolling."""
import asyncio
from playwright.async_api import async_playwright


async def debug_hpe_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible browser
        page = await browser.new_page()
        
        url = "https://careers.hpe.com/us/en/search-results"
        print(f"Loading: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except:
            # If timeout, just wait a bit
            await page.wait_for_timeout(5000)
        print("Page loaded")
        
        # Wait for initial render
        await page.wait_for_timeout(3000)
        
        # Check for job elements
        job_selectors = [
            '[data-job-id]',
            '[data-qa="job-posting"]',
            '[class*="job-card"]',
            '[class*="job-item"]',
            '[class*="job-listing"]',
            'article',
            'li[data-id]',
            '.job',
        ]
        
        print("\nChecking job selectors:")
        for selector in job_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"  ✓ {selector}: {count} elements")
            except:
                pass
        
        # Scroll and check for "Load More" button
        print("\nScrolling to bottom...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        # Check for load more buttons
        load_more_selectors = [
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            'a:has-text("Load More")',
            'button:has-text("more")',
            'button[class*="load"]',
            'button[class*="more"]',
        ]
        
        print("\nChecking for load more buttons:")
        for selector in load_more_selectors:
            try:
                locator = page.locator(selector)
                count = await locator.count()
                if count > 0:
                    for i in range(count):
                        element = locator.nth(i)
                        is_visible = await element.is_visible()
                        text = await element.inner_text()
                        print(f"  ✓ {selector}: visible={is_visible}, text='{text}'")
            except Exception as e:
                pass
        
        # Take screenshot
        await page.screenshot(path="hpe_page.png")
        print("\nScreenshot saved to hpe_page.png")
        
        # Get page HTML length
        html = await page.content()
        print(f"\nHTML length: {len(html)} bytes")
        
        # Wait so you can inspect manually
        print("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_hpe_page())
