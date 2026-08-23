"""Location Normalizer module."""

import re
from app.models.normalized_job import JobLocation
from app.utils.html_utils import clean_whitespace

KNOWN_COUNTRIES = {
    "india",
    "us",
    "usa",
    "united states",
    "united states of america",
    "germany",
    "taiwan",
    "armenia",
    "canada",
    "uk",
    "united kingdom",
    "japan",
    "france",
    "australia",
    "singapore",
    "china",
    "israel",
    "netherlands",
    "switzerland",
    "poland",
    "romania",
    "ireland",
    "spain",
    "italy",
    "brazil",
    "mexico",
}


def normalize_location(location: str | None) -> JobLocation | None:
    """
    Standardizes raw location strings into structured JobLocation objects.
    - Preserves raw string for multi-location inputs (joined by •, |, or 'or') with null structured fields.
    - Correctly handles both Workday's 'Country, City' and standard 'City, Country' conventions.
    """
    if not location:
        return None

    cleaned = clean_whitespace(location)
    if not cleaned:
        return None

    # Multi-location check: do not attempt structured split if string contains multi-location delimiters
    if re.search(r"[•|]|\b(?:or|and)\b", cleaned, re.IGNORECASE) or cleaned.count(",") > 3:
        return JobLocation(raw=cleaned, city=None, state=None, country=None)

    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    city: str | None = None
    state: str | None = None
    country: str | None = None

    if len(parts) == 2:
        part0_lower = parts[0].lower()
        part1_lower = parts[1].lower()
        if part0_lower in KNOWN_COUNTRIES:
            # Workday convention: 'Country, City' (e.g. 'India, Bengaluru')
            country = parts[0]
            city = parts[1]
        else:
            # Standard convention: 'City, Country' (e.g. 'Bengaluru, India')
            city = parts[0]
            country = parts[1]

    elif len(parts) == 3:
        part0_lower = parts[0].lower()
        if part0_lower in KNOWN_COUNTRIES:
            # Workday convention: 'Country, State, City' (e.g. 'US, CA, Santa Clara')
            country = parts[0]
            state = parts[1]
            city = parts[2]
        else:
            # Standard convention: 'City, State, Country' (e.g. 'San Francisco, CA, United States')
            city = parts[0]
            state = parts[1]
            country = parts[2]

    elif len(parts) == 1:
        if parts[0].lower() in KNOWN_COUNTRIES:
            country = parts[0]
        else:
            city = parts[0]

    return JobLocation(
        raw=cleaned,
        city=city,
        state=state,
        country=country,
    )
