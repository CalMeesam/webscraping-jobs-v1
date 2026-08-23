"""Career Link Discovery Engine."""

from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx
from app.core.config import settings
from app.core.constants import ATS_PATTERNS, CAREER_URL_KEYWORDS
from app.core.logging import get_logger
from app.utils.url_utils import is_valid_url, make_absolute_url

logger = get_logger(__name__)

SOCIAL_DOMAINS = (
    "x.com",
    "twitter.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "linkedin.com",
    "github.com",
    "t.co",
)


class CareerDiscovery:
    """Discovers career and job board URLs from company websites."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    def _is_social_media_url(self, url: str) -> bool:
        """Returns True if URL points to a social media domain."""
        netloc = urlparse(url).netloc.lower()
        return any(d in netloc for d in SOCIAL_DOMAINS)

    def is_candidate_career_url(self, url: str) -> bool:
        """Determines if the given URL itself is already a candidate career/job page."""
        if self._is_social_media_url(url):
            return False

        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        # External ATS domain
        for ats_name, patterns in ATS_PATTERNS.items():
            for pattern in patterns:
                if pattern in netloc:
                    return True

        # Hostname contains career/jobs
        if any(kw in netloc for kw in ("career", "careers", "job", "jobs")):
            return True

        # Path contains career/jobs
        if any(kw in path for kw in CAREER_URL_KEYWORDS):
            return True

        return False

    def score_candidate_url(self, base_url: str, candidate_url: str, anchor_text: str = "") -> int:
        """Scores candidate link based on ATS pattern matches, URL path, and anchor text."""
        if self._is_social_media_url(candidate_url):
            return 0

        score = 0
        parsed = urlparse(candidate_url)
        path = parsed.path.lower()
        netloc = parsed.netloc.lower()
        anchor_lower = anchor_text.lower().strip()

        # Highest signal: External ATS domain
        for ats_name, patterns in ATS_PATTERNS.items():
            for pattern in patterns:
                if pattern in netloc:
                    return 100

        # URL path signals
        if path in ("/careers", "/careers/", "/jobs", "/jobs/"):
            score += 95
        elif "/careers/open-positions" in path or "/jobs/openings" in path:
            score += 90
        elif any(kw in path for kw in CAREER_URL_KEYWORDS):
            score += 70

        # Anchor text signals
        if anchor_lower in ("careers", "jobs", "join us", "open positions", "work with us", "view open jobs"):
            score += 30
        elif any(kw in anchor_lower for kw in CAREER_URL_KEYWORDS):
            score += 15

        # Penalize non-career pages
        if any(bad in path for bad in ("blog", "news", "about", "contact", "privacy", "terms")):
            score -= 50

        return max(score, 0)

    async def discover_career_urls(self, url: str, html_content: str | None = None) -> list[str]:
        """Finds candidate career URLs ordered by confidence score."""
        if self._is_social_media_url(url):
            return []

        if not html_content:
            client = self._client or httpx.AsyncClient(
                timeout=settings.HTTP_TIMEOUT_SECONDS,
                headers={"User-Agent": settings.USER_AGENT},
                follow_redirects=True,
            )
            should_close = self._client is None
            try:
                r = await client.get(url)
                html_content = r.text
            except Exception as e:
                logger.warning(f"Failed to fetch {url} for career discovery: {e}")
                return []
            finally:
                if should_close:
                    await client.aclose()

        soup = BeautifulSoup(html_content, "lxml")
        candidates: list[tuple[int, str]] = []
        seen_urls: set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            abs_url = make_absolute_url(url, href)
            if not abs_url or not is_valid_url(abs_url) or abs_url in seen_urls or self._is_social_media_url(abs_url):
                continue

            seen_urls.add(abs_url)
            anchor_text = a_tag.get_text(strip=True)
            score = self.score_candidate_url(url, abs_url, anchor_text)

            if score > 20:
                candidates.append((score, abs_url))

        # Sort descending by score
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [url for score, url in candidates[: settings.MAX_CANDIDATE_URLS]]
        logger.info(f"Discovered {len(top_candidates)} career candidate URLs for {url}")
        return top_candidates
