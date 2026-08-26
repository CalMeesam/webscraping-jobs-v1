"""Find an active Lever board by testing multiple companies."""
import asyncio
import httpx
import json

async def find_active_lever_board():
    """Try to find an active Lever board from a list of companies."""
    
    # Extended list of companies that might use Lever
    companies = [
        "lever",  # Lever's own board
        "circleci",
        "cloudflare",
        "docker",
        "elastic",
        "github",
        "gitlab",
        "hashicorp",
        "hubspot",
        "monday",
        "notion",
        "postman",
        "segment",
        "shopify",
        "slack",
        "stripe",
        "twilio",
        "vercel",
        "zoom",
        # More companies
        "airtable",
        "asana",
        "atlassian",
        "databricks",
        "datadog",
        "dropbox",
        "instacart",
        "lyft",
        "pinterest",
        "reddit",
        "robinhood",
        "snap",
        "spotify",
        "square",
        "uber",
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for company in companies:
            api_url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            
            try:
                r = await client.get(api_url)
                
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list) and len(data) > 0:
                        print(f"\n{'='*80}")
                        print(f"✅ FOUND ACTIVE BOARD: {company}")
                        print(f"URL: {api_url}")
                        print(f"Jobs count: {len(data)}")
                        print(f"{'='*80}\n")
                        
                        # Show structure of first job
                        sample = data[0]
                        print("📋 Sample job structure (first job):")
                        print(json.dumps(sample, indent=2))
                        
                        print(f"\n🔑 Available fields:")
                        for key in sample.keys():
                            value_type = type(sample[key]).__name__
                            print(f"   - {key}: {value_type}")
                        
                        # Save response
                        filename = f"lever_{company}_response.json"
                        with open(filename, "w", encoding="utf-8") as f:
                            json.dump(data[:5], f, indent=2)  # Save first 5 jobs
                        print(f"\n✅ Saved first 5 jobs to: {filename}")
                        
                        return True
                    elif isinstance(data, list) and len(data) == 0:
                        print(f"   {company}: 200 OK, but 0 jobs")
                    else:
                        print(f"   {company}: Unexpected response type: {type(data)}")
                elif r.status_code == 404:
                    print(f"   {company}: 404 Not Found")
                else:
                    print(f"   {company}: HTTP {r.status_code}")
            
            except Exception as e:
                print(f"   {company}: Error - {e}")
            
            await asyncio.sleep(0.1)  # Small delay to avoid rate limiting
    
    return False

if __name__ == "__main__":
    success = asyncio.run(find_active_lever_board())
    if not success:
        print("\n❌ Could not find any active Lever boards in test list")
        print("\nNote: This might mean:")
        print("  1. These companies moved to different ATS platforms")
        print("  2. Company slugs have changed")
        print("  3. Lever API requires authentication now")
        print("\nTry visiting jobs.lever.co manually to find active boards")
