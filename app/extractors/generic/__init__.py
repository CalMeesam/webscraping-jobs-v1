"""Generic Extractors package export."""

from app.extractors.generic.api_extractor import APIExtractor
from app.extractors.generic.html_extractor import HTMLExtractor
from app.extractors.generic.playwright_extractor import PlaywrightExtractor

__all__ = [
    "HTMLExtractor",
    "APIExtractor",
    "PlaywrightExtractor",
]
