"""Fetch HPE page and analyze HTML structure."""
import asyncio
import httpx
from bs4 import BeautifulSoup


async def analyze_hpe_html():
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        print("Fetching HPE careers page...")
        response = await client.get('https://careers.hpe.com/us/en/search-results')
        
        print(f"Status: {response.status_code}")
        print(f"Content-Length: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Check for Phenom ATS signals
        print("\n=== ATS Detection ===")
        
        # Look for Phenom-specific elements
        phenom_scripts = soup.find_all('script', src=lambda x: x and 'phenom' in x.lower())
        if phenom_scripts:
            print(f"✅ Found {len(phenom_scripts)} Phenom script(s)")
            for script in phenom_scripts[:3]:
                print(f"   - {script.get('src', '')[:100]}")
        
        # Look for data attributes
        phenom_data = soup.find_all(attrs={'data-ph-at-id': True})
        if phenom_data:
            print(f"✅ Found {len(phenom_data)} elements with data-ph-at-id")
        
        # Check for API endpoint hints in scripts
        print("\n=== API Endpoint Hints ===")
        inline_scripts = soup.find_all('script', src=False)
        for script in inline_scripts[:5]:
            if script.string and ('api' in script.string.lower() or 'ajax' in script.string.lower()):
                # Extract potential API URLs
                import re
                urls = re.findall(r'https?://[^\s\'"<>]+', script.string)
                for url in urls[:3]:
                    if 'job' in url.lower() or 'search' in url.lower():
                        print(f"   - {url}")
        
        # Look for initial job data in HTML
        print("\n=== Job Data in HTML ===")
        job_elements = soup.find_all(['article', 'div'], class_=lambda x: x and ('job' in x.lower() or 'result' in x.lower()))
        print(f"Job-like elements: {len(job_elements)}")
        
        # Look for JSON-LD
        json_ld = soup.find_all('script', type='application/ld+json')
        if json_ld:
            print(f"JSON-LD scripts: {len(json_ld)}")
            for ld in json_ld[:2]:
                if 'JobPosting' in ld.string:
                    print("   - Contains JobPosting schema")
        
        # Look for pagination/total count
        print("\n=== Pagination/Count Info ===")
        total_elem = soup.find(text=lambda x: x and ('result' in x.lower() or 'job' in x.lower()) and any(c.isdigit() for c in x))
        if total_elem:
            print(f"Found text with counts: {total_elem[:100]}")


if __name__ == "__main__":
    asyncio.run(analyze_hpe_html())
