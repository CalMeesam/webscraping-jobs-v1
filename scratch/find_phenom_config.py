"""Find Phenom widget configuration in HPE page."""
import asyncio
import httpx
import re
import json
from bs4 import BeautifulSoup


async def find_widget_config():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get('https://careers.hpe.com/us/en/search-results')
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for inline scripts with configuration
        scripts = soup.find_all('script', src=False)
        
        for script in scripts:
            if script.string and ('phApp' in script.string or 'widgetApiEndpoint' in script.string):
                # Extract the config
                config_text = script.string
                
                # Try to find the configuration object
                print("=== Found Widget Config ===\n")
                print(config_text[:2000])
                
                # Try to extract API params
                if 'widgetApiEndpoint' in config_text:
                    endpoint_match = re.search(r'"widgetApiEndpoint":"([^"]+)"', config_text)
                    if endpoint_match:
                        print(f"\nWidget API Endpoint: {endpoint_match.group(1)}")
                
                # Look for other config
                if 'locale' in config_text:
                    locale_match = re.search(r'"locale":"([^"]+)"', config_text)
                    if locale_match:
                        print(f"Locale: {locale_match.group(1)}")
                
                if 'siteType' in config_text:
                    site_match = re.search(r'"siteType":"([^"]+)"', config_text)
                    if site_match:
                        print(f"Site Type: {site_match.group(1)}")


if __name__ == "__main__":
    asyncio.run(find_widget_config())
