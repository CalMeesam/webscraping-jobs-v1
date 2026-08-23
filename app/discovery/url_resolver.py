"""URL resolver module."""

import httpx
from app.core.config import settings
from app.core.constants import ERROR_INVALID_URL, ERROR_REDIRECT_LOOP, ERROR_URL_UNREACHABLE
from app.core.logging import get_logger
from app.models.extraction_models import ResolvedURL
from app.utils.url_utils import clean_url, is_valid_url, make_absolute_url, normalize_url_scheme

logger = get_logger(__name__)


class URLResolver:
    """Validates URLs, tracks redirects using httpx, and cleans query parameters."""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def resolve(self, url: str) -> ResolvedURL:
        if not is_valid_url(url):
            raise ValueError(f"Invalid URL format: {url}")

        normalized_start = clean_url(normalize_url_scheme(url))
        redirect_chain: list[str] = [normalized_start]
        current_url = normalized_start

        client = self._client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"User-Agent": settings.USER_AGENT},
        )
        should_close = self._client is None

        try:
            hops = 0
            status_code = 200

            while hops < settings.MAX_REDIRECTS:
                try:
                    response = await client.head(current_url)
                    if response.status_code in (405, 501):
                        response = await client.get(current_url)
                except httpx.HTTPError as http_err:
                    logger.warning(f"HTTP connection error when resolving {current_url}: {http_err}")
                    return ResolvedURL(
                        original_url=url,
                        final_url=current_url,
                        redirect_chain=redirect_chain,
                        status_code=503,
                    )

                status_code = response.status_code

                if response.is_redirect:
                    location = response.headers.get("Location")
                    if not location:
                        break
                    next_url = make_absolute_url(current_url, location)
                    if not next_url:
                        break

                    if next_url in redirect_chain:
                        logger.warning(f"Redirect loop detected at {next_url}")
                        return ResolvedURL(
                            original_url=url,
                            final_url=next_url,
                            redirect_chain=redirect_chain,
                            status_code=308,
                        )

                    redirect_chain.append(next_url)
                    current_url = next_url
                    hops += 1
                else:
                    break

            if hops >= settings.MAX_REDIRECTS:
                logger.warning(f"Max redirects ({settings.MAX_REDIRECTS}) exceeded for {url}")

            return ResolvedURL(
                original_url=url,
                final_url=current_url,
                redirect_chain=redirect_chain,
                status_code=status_code,
            )

        finally:
            if should_close:
                await client.aclose()
