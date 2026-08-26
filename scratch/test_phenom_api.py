"""Test Phenom API structure for HPE."""
import asyncio
import httpx
import json


async def test_phenom_api():
    """Try to find the Phenom API endpoint and structure."""
    
    # The base seems to be https://careers.hpe.com/widgets
    # Common Phenom endpoints include:
    # - /widgets/jobs
    # - /widgets/search
    # - /api/apply/v2/jobs
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        
        # Try different common Phenom API patterns
        endpoints_to_try = [
            "https://careers.hpe.com/widgets/jobs",
            "https://careers.hpe.com/widgets/search",
            "https://careers.hpe.com/api/apply/v2/jobs",
            "https://careers.hpe.com/api/jobs",
            "https://careers.hpe.com/us/en/jobs",
        ]
        
        for endpoint in endpoints_to_try:
            try:
                print(f"\nTrying: {endpoint}")
                response = await client.get(endpoint, params={"limit": 50})
                print(f"  Status: {response.status_code}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    print(f"  Content-Type: {content_type}")
                    
                    if 'json' in content_type:
                        data = response.json()
                        print(f"  Response keys: {list(data.keys())[:10]}")
                        if 'data' in data:
                            print(f"  data keys: {list(data['data'].keys())[:10] if isinstance(data['data'], dict) else 'list'}")
                        if 'jobs' in data:
                            print(f"  jobs count: {len(data['jobs'])}")
                    else:
                        print(f"  Content length: {len(response.text)}")
            except Exception as e:
                print(f"  Error: {e}")
        
        # Also try POST with search params
        print("\n\nTrying POST to /widgets/jobs with search params...")
        try:
            response = await client.post(
                "https://careers.hpe.com/widgets/jobs",
                json={
                    "limit": 50,
                    "offset": 0,
                    "location": "US"
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200 and 'json' in response.headers.get('content-type', ''):
                data = response.json()
                print(f"Response keys: {list(data.keys())[:10]}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_phenom_api())
