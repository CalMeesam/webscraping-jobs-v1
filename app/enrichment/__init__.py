"""Enrichment package export."""

from app.enrichment.detail_enricher import DetailEnricher, requires_enrichment

__all__ = [
    "DetailEnricher",
    "requires_enrichment",
]
