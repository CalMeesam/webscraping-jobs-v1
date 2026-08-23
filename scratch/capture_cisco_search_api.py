import asyncio
import json
from playwright.async_api import async_playwright

async def capture_cisco_search_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        captured_json = []

        async def handle_response(response):
            try:
                res_url = response.url.lower()
                if "widgets" in res_url or "search" in res_url or "api" in res_url or "jobs" in res_url:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        data = await response.json()
                        captured_json.append((response.url, data))
            except Exception:
                pass

        page.on("response", handle_response)
        
        # Navigate to search-results page
        await page.goto("https://careers.cisco.com/global/en/search-results?keywords=engineering", wait_until="networkidle")
        # Wait specifically for job result elements to render
        try:
            await page.wait_for_selector(".job-title, [data-ph-at-id='job-title-text'], a[href*='/job/']", timeout=10000)
        except Exception as e:
            print("Selector wait warning:", e)

        await page.wait_for_timeout(3000)
        await browser.close()

        print(f"Captured {len(captured_json)} JSON responses from Playwright!")

        # Find which captured JSON payload contains job objects with titles/locations
        for idx, (url, payload) in enumerate(captured_json):
            s = json.dumps(payload)
            if "ASIC" in s or "Verification" in s or "Engineer" in s or "refineSearch" in s or "job" in s:
                with open(f"scratch/payload_{idx}.json", "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                print(f"Saved candidate payload {idx} from {url} (size {len(s)})")

if __name__ == "__main__":
    asyncio.run(capture_cisco_search_api())
