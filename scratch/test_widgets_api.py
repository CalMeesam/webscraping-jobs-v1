"""Test Phenom widgets API with proper parameters."""
import asyncio
import httpx
import json


async def test_widgets_api():
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Try the widgets endpoint with proper parameters
        print("Testing /widgets endpoint...")
        
        # Common params for Phenom widgets API
        params = {
            "c": "HPE1US",  # Client ref number
            "lang": "en_us",
            "l": "50",  # limit
            "w": "Search Results",  # widget name
           # Try variations
        }
        
        try:
            response = await client.get(
                "https://careers.hpe.com/widgets",
                params=params
            )
            print(f"Status: {response.status_code}")
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'json' in content_type:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                if 'eagerLoadRefreshedData' in data:
                    print(f"Has eagerLoadRefreshedData")
                if 'jobs' in str(data):
                    print("Contains 'jobs' in response")
            else:
                print(f"Content length: {len(response.text)}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*60 + "\n")
        
        # Try a direct search API call
        print("Testing search results page data...")
        try:
            response = await client.get(
                "https://careers.hpe.com/us/en/search-results",
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
            print(f"Status: {response.status_code}")
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_widgets_api())
