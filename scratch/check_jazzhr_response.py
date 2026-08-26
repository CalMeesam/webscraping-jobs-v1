import asyncio
import httpx

async def check():
    async with httpx.AsyncClient() as client:
        r = await client.get('https://jazzhr.applytojob.com/api/jobs')
        print(f'Content-Type: {r.headers.get("content-type")}')
        print(f'Length: {len(r.text)}')
        print(f'\nFirst 1000 chars:')
        print(r.text[:1000])

asyncio.run(check())
