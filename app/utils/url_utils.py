"""URL helper functions."""

import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
from app.core.constants import TRACKING_PARAM_PREFIXES


def normalize_url_scheme(url: str) -> str:
    """Prepend https:// if missing scheme."""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        return f"https://{url}"
    return url


def is_valid_url(url: str) -> bool:
    """Validate URL format strictly."""
    if not url or not isinstance(url, str):
        return False
    try:
        url_norm = normalize_url_scheme(url)
        parsed = urlparse(url_norm)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        # Ensure domain has at least one dot or localhost, and no spaces in netloc
        if " " in parsed.netloc or ("." not in parsed.netloc and parsed.netloc != "localhost"):
            return False
        return True
    except Exception:
        return False


def clean_url(url: str) -> str:
    """
    Strips tracking query parameters (utm_*, gclid, fbclid, etc.)
    and normalizes trailing slashes.
    """
    if not url:
        return ""

    parsed = urlparse(url)

    # Clean query parameters against allowlist/prefix list
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {}
    for param_key, param_vals in query_params.items():
        key_lower = param_key.lower()
        if any(key_lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
            continue
        filtered_params[param_key] = param_vals

    new_query = urlencode(filtered_params, doseq=True)

    # Normalize path trailing slash (keep root slash if empty path)
    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    cleaned_parsed = urlunparse((
        parsed.scheme,
        parsed.netloc.lower(),
        path,
        parsed.params,
        new_query,
        ""  # strip fragment
    ))

    return cleaned_parsed


def make_absolute_url(base_url: str, relative_url: str | None) -> str | None:
    """Resolves relative URL against base_url and cleans tracking parameters."""
    if not relative_url:
        return None
    if relative_url.startswith("javascript:") or relative_url.startswith("mailto:"):
        return None

    abs_url = urljoin(base_url, relative_url)
    return clean_url(abs_url)
