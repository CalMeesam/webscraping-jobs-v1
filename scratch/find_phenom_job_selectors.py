"""Find actual job element selectors used by Phenom ATS."""
import asyncio
from playwright.async_api import async_playwright


async def find_job_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        url = "https://careers.hpe.com/us/en/search-results"
        print(f"Loading: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except:
            pass
        
        # Wait for Vue app to render
        await page.wait_for_timeout(5000)
        
        print("\n=== Analyzing DOM Structure ===\n")
        
        # Find all elements with job-related content
        job_title_elements = await page.locator('text=/engineer|developer|manager|analyst|consultant|intern/i').all()
        
        if job_title_elements:
            print(f"Found {len(job_title_elements)} elements with job titles\n")
            
            # Analyze first few elements to find common patterns
            for i, elem in enumerate(job_title_elements[:5]):
                try:
                    # Get parent element
                    parent = elem.locator('..')
                    
                    # Get element attributes
                    tag_name = await elem.evaluate('el => el.tagName')
                    class_name = await elem.evaluate('el => el.className')
                    parent_class = await parent.evaluate('el => el.className')
                    parent_tag = await parent.evaluate('el => el.tagName')
                    
                    # Get text content
                    text = await elem.inner_text()
                    
                    print(f"Job {i+1}:")
                    print(f"  Text: {text[:50]}")
                    print(f"  Tag: {tag_name}, Class: {class_name}")
                    print(f"  Parent Tag: {parent_tag}, Parent Class: {parent_class}")
                    
                    # Try to find the job card container
                    card = elem
                    for _ in range(5):  # Go up 5 levels
                        card = card.locator('..')
                        card_class = await card.evaluate('el => el.className')
                        card_tag = await card.evaluate('el => el.tagName')
                        if 'card' in card_class.lower() or 'job' in card_class.lower() or 'result' in card_class.lower():
                            print(f"  Job Card: {card_tag}.{card_class}")
                            break
                    
                    print()
                except Exception as e:
                    print(f"  Error analyzing element: {e}\n")
        
        # Check for specific Phenom patterns
        print("\n=== Checking Phenom-specific Patterns ===\n")
        
        phenom_selectors = [
            '[data-ph-at-id]',
            '[data-ph-id]',
            '.jobs-list-item',
            '.job-item',
            '.ph-card',
            '.search-result',
            '.result-card',
            'li[role="listitem"]',
            '[class*="JobCard"]',
            '[class*="job-card"]',
            '[class*="SearchResult"]',
        ]
        
        for selector in phenom_selectors:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"✓ {selector}: {count} elements")
                    # Get first element's class
                    first = page.locator(selector).first
                    class_name = await first.evaluate('el => el.className')
                    print(f"  First element class: {class_name}\n")
            except:
                pass
        
        # Check the main container
        print("\n=== Main Container Analysis ===\n")
        main_container_selectors = [
            'main',
            '[role="main"]',
            '#main-content',
            '.job-results',
            '.search-results',
        ]
        
        for selector in main_container_selectors:
            try:
                elem = page.locator(selector).first
                if await elem.count() > 0:
                    html = await elem.inner_html()
                    print(f"{selector}: {len(html)} chars of HTML")
                    # Count child elements
                    children = await elem.locator('> *').count()
                    print(f"  Direct children: {children}\n")
            except:
                pass
        
        print("\nPress Ctrl+C to close browser and exit...")
        await page.wait_for_timeout(60000)
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(find_job_selectors())
