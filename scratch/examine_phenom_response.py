"""Examine Phenom API response structure for HPE."""
import asyncio
import httpx
import json


async def examine_phenom_response():
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        print("Fetching from Phenom API...")
        response = await client.get(
            "https://careers.hpe.com/api/apply/v2/jobs",
            params={"limit": 50}
        )
        
        print(f"Status: {response.status_code}\n")
        
        data = response.json()
        
        print("=== Response Structure ===")
        print(f"Keys: {list(data.keys())}")
        print(f"Status: {data.get('status')}")
        print(f"Error Code: {data.get('errorCode')}")
        
        if 'data' in data and isinstance(data['data'], list):
            jobs = data['data']
            print(f"\nJobs found: {len(jobs)}")
            
            if jobs:
                print("\n=== First Job Structure ===")
                first_job = jobs[0]
                print(f"Keys: {list(first_job.keys())}")
                print(json.dumps(first_job, indent=2)[:1500])
                
                print("\n\n=== Summary of All Jobs ===")
                for i, job in enumerate(jobs[:5]):
                    print(f"{i+1}. {job.get('title', 'No title')} | {job.get('location', 'No location')}")


if __name__ == "__main__":
    asyncio.run(examine_phenom_response())
