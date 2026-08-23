"""HTML helper functions."""

import re
from bs4 import BeautifulSoup


def strip_html_tags(html_content: str | None) -> str | None:
    """Extract clean text from HTML content using BeautifulSoup get_text()."""
    if not html_content:
        return None

    try:
        soup = BeautifulSoup(html_content, "lxml")
        # Remove script and style elements
        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return clean_whitespace(text)
    except Exception:
        # Fallback simple regex if BS4 fails
        clean_re = re.compile(r"<[^>]+>")
        text = clean_re.sub(" ", html_content)
        return clean_whitespace(text)


def clean_whitespace(text: str | None) -> str | None:
    """Collapses multiple spaces, tabs, and newlines into single spaces."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None
