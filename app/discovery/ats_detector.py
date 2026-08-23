"""ATS Detection module."""

import re
from urllib.parse import urlparse
from app.core.constants import ATS_PATTERNS
from app.core.logging import get_logger

logger = get_logger(__name__)


class ATSDetector:
    """Detects ATS type and confidence score based on URL, HTML signatures, and inline scripts."""

    def detect(self, url: str, html_content: str | None = None) -> tuple[str | None, float]:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        path = parsed.path.lower()

        # Signal 1: Domain matching (Highest confidence = 1.0)
        for ats_name, patterns in ATS_PATTERNS.items():
            for pattern in patterns:
                if pattern in hostname:
                    logger.info(f"ATS detected via domain: {ats_name} on {hostname}")
                    return ats_name, 1.0

        # Signal 2: URL Path matching
        if "greenhouse" in path:
            return "greenhouse", 0.9
        if "myworkdayjobs" in path or "/wday/cxs/" in path:
            return "workday", 0.9
        if "/hcmui/candidateexperience" in path or "oraclecloud.com" in hostname:
            return "oracle_hcm", 0.95
        if "lever.co" in path:
            return "lever", 0.9
        if "smartrecruiters" in path:
            return "smartrecruiters", 0.9
        if "ashbyhq" in path:
            return "ashby", 0.9

        # Signal 3: HTML signatures and embedded JavaScript configurations
        if html_content:
            html_lower = html_content.lower()

            if "boards.greenhouse.io" in html_lower or "grnhse" in html_lower:
                return "greenhouse", 0.85

            if "myworkdayjobs.com" in html_lower or "wday/cxs" in html_lower or "workday" in html_lower and "cxs" in html_lower:
                return "workday", 0.85

            if "hcmui/candidateexperience" in html_lower or "hcmrestapi" in html_lower:
                return "oracle_hcm", 0.85

            if "jobs.lever.co" in html_lower or "lever-jobs" in html_lower:
                return "lever", 0.85

            if "smartrecruiters.com" in html_lower:
                return "smartrecruiters", 0.85

            if "ashbyhq.com" in html_lower or "ashby" in html_lower and "jobs" in html_lower:
                return "ashby", 0.85

        return None, 0.0
