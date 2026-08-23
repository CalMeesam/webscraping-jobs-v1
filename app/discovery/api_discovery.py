"""API Discovery and Validation module."""

import json
import re
from typing import Any
from bs4 import BeautifulSoup
from app.core.constants import JOB_SCHEMA_KEYWORDS
from app.core.logging import get_logger

logger = get_logger(__name__)


class APIDiscovery:
    """Discovers and validates JSON job APIs embedded in HTML or network responses."""

    def validate_job_schema(self, data: Any, current_depth: int = 0) -> bool:
        """
        Validates if JSON data represents real job data by checking for
        AT LEAST 3 matching job schema keys at any nesting depth up to 3 levels.
        """
        if current_depth > 3:
            return False

        found_keys: set[str] = set()

        def extract_keys(obj: Any, depth: int) -> None:
            if depth > 3 or not obj:
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    k_lower = str(k).lower()
                    for keyword in JOB_SCHEMA_KEYWORDS:
                        if keyword in k_lower:
                            found_keys.add(keyword)
                    extract_keys(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:5]:  # sample first 5 items
                    extract_keys(item, depth + 1)

        extract_keys(data, current_depth)
        is_valid = len(found_keys) >= 3
        if is_valid:
            logger.info(f"API data validated with {len(found_keys)} matching job schema keys: {found_keys}")
        return is_valid

    def find_embedded_json_apis(self, html_content: str) -> list[dict]:
        """Parses script tags and JSON-LD blocks for embedded job JSON data."""
        soup = BeautifulSoup(html_content, "lxml")
        valid_json_blocks: list[dict] = []

        # Check script type="application/ld+json"
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                if not script.string:
                    continue
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    valid_json_blocks.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            valid_json_blocks.append(item)
            except Exception:
                continue

        # Check raw JSON script tags
        for script in soup.find_all("script"):
            text = script.string or script.text or ""
            if len(text) > 20 and ("job" in text.lower() or "career" in text.lower()):
                # Match JSON array or object string
                matches = re.findall(r"(\[\s*\{.*?\}\s*\]|\{\s*\"jobs\".*?\})", text, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if self.validate_job_schema(data):
                            valid_json_blocks.append(data if isinstance(data, dict) else {"jobs": data})
                    except Exception:
                        continue

        return valid_json_blocks
