"""Unit tests for URL Resolver."""

import pytest
import respx
import httpx
from app.discovery.url_resolver import URLResolver
from app.utils.url_utils import clean_url, is_valid_url, normalize_url_scheme


def test_is_valid_url():
    assert is_valid_url("https://example.com")
    assert is_valid_url("http://example.com/careers")
    assert is_valid_url("company.com")  # Normalizer adds https://
    assert not is_valid_url("not a url")
    assert not is_valid_url("ftp://invalid-scheme.com")


def test_clean_url_strips_tracking():
    raw_url = "https://company.com/careers/?utm_source=google&gclid=12345&fbclid=abc&page=1"
    cleaned = clean_url(raw_url)
    assert "utm_source" not in cleaned
    assert "gclid" not in cleaned
    assert "fbclid" not in cleaned
    assert "page=1" in cleaned
    assert cleaned.startswith("https://company.com/careers")


@pytest.mark.asyncio
@respx.mock
async def test_url_resolver_redirect_chain():
    respx.route(method="HEAD", host="example.com", path="/").mock(
        return_value=httpx.Response(301, headers={"Location": "https://example.com/careers"})
    )
    respx.route(method="HEAD", host="example.com", path="/careers").mock(
        return_value=httpx.Response(302, headers={"Location": "https://boards.greenhouse.io/example"})
    )
    respx.route(method="HEAD", host="boards.greenhouse.io", path="/example").mock(
        return_value=httpx.Response(200)
    )

    resolver = URLResolver()
    resolved = await resolver.resolve("https://example.com")

    assert resolved.final_url == "https://boards.greenhouse.io/example"
    assert len(resolved.redirect_chain) == 3
    assert resolved.redirect_chain[0] == "https://example.com"
    assert resolved.redirect_chain[1] == "https://example.com/careers"
    assert resolved.redirect_chain[2] == "https://boards.greenhouse.io/example"
    assert resolved.status_code == 200
