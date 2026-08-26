"""Debug Oracle HCM detail page structure."""
import asyncio
import httpx
from bs4 import BeautifulSoup

async def debug_oracle_job_page():
    """Fetch a sample Oracle HCM job page to see its structure."""
    job_url = "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/job/R286840"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        print(f"Fetching: {job_url}")
        r = await client.get(job_url)
        print(f"Status: {r.status_code}")
        print(f"Content length: {len(r.text)} bytes")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            
            # Check for various possible selectors
            selectors_to_try = [
                ("div.job-description", soup.find("div", class_="job-description")),
                ("div#job-description", soup.find("div", {"id": "job-description"})),
                ("div.jobDescription", soup.find("div", class_="jobDescription")),
                ("section.job-details", soup.find("section", class_="job-details")),
                ("div.job-posting-description", soup.find("div", class_="job-posting-description")),
                ("main", soup.find("main")),
                ("article", soup.find("article")),
            ]
            
            print("\n🔍 Trying selectors:")
            for selector_name, element in selectors_to_try:
                if element:
                    text_preview = element.get_text()[:200].replace("\n", " ").strip()
                    print(f"   ✅ {selector_name}: Found! Preview: {text_preview}...")
                else:
                    print(f"   ❌ {selector_name}: Not found")
            
            # Save full HTML for inspection
            with open("oracle_job_page_sample.html", "w", encoding="utf-8") as f:
                f.write(r.text)
            print(f"\n📄 Full HTML saved to: oracle_job_page_sample.html")
            
            # Check if it's a JavaScript-rendered page
            if "window.__INITIAL_STATE__" in r.text or "React" in r.text or "Vue" in r.text:
                print("\n⚠️ This appears to be a JavaScript-rendered page (React/Vue)")
                print("   Static HTML fetching may not work - may need Playwright")

if __name__ == "__main__":
    asyncio.run(debug_oracle_job_page())
