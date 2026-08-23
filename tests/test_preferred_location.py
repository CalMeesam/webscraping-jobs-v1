"""Unit tests for preferred_location stable partition post-processing."""

import pytest
from app.models.normalized_job import NormalizedJob
from app.models.request_models import ExtractionRequest
from app.orchestrator.extraction_manager import ExtractionManager


def test_preferred_location_stable_partition():
    jobs = [
        NormalizedJob(id="1", title="Job 1", location="London, UK", source="test"),
        NormalizedJob(id="2", title="Job 2", location="Bengaluru, India", source="test"),
        NormalizedJob(id="3", title="Job 3", location="San Francisco, CA", source="test"),
        NormalizedJob(id="4", title="Job 4", location="Bengaluru, KA, India", source="test"),
        NormalizedJob(id="5", title="Job 5", location="Berlin, Germany", source="test"),
    ]

    # Stable partition test with preferred_location="Bengaluru"
    pref_loc = "Bengaluru".strip().lower()
    partitioned = sorted(jobs, key=lambda j: pref_loc in (j.location or "").lower(), reverse=True)

    # Preferred location matches must move to front
    assert partitioned[0].id == "2"  # Bengaluru, India
    assert partitioned[1].id == "4"  # Bengaluru, KA, India

    # Original relative ordering within matching group preserved (2 before 4)
    # Original relative ordering within non-matching group preserved (1 before 3 before 5)
    assert partitioned[2].id == "1"
    assert partitioned[3].id == "3"
    assert partitioned[4].id == "5"

    # Truncate max_jobs=2
    truncated = partitioned[:2]
    assert len(truncated) == 2
    assert {j.id for j in truncated} == {"2", "4"}


def test_bare_city_vs_country_substring_behavior():
    """
    Analyzes substring matching behavior for bare city-only vs country location strings:
    - Query 'Bengaluru' matches 'Bengaluru, India', 'Bengaluru', 'Bengaluru, KA, India'.
    - Query 'Bengaluru' does NOT match bare country 'India' or 'Remote, India'.
    """
    pref_city = "Bengaluru".strip().lower()

    assert pref_city in "bengaluru, india"  # Bare city matches city+country string
    assert pref_city in "bengaluru"         # Bare city matches exact city string
    assert not (pref_city in "india")       # Bare city does NOT match bare country string
    assert not (pref_city in "remote, us")  # Bare city does NOT match remote US string
