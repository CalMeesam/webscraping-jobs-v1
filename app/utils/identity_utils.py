"""Job identity key computation utilities."""

from urllib.parse import urlparse
from app.models.normalized_job import NormalizedJob
from app.utils.html_utils import clean_whitespace


def normalize_url_key(url: str | None) -> str | None:
    """Normalize a URL into a canonical comparison key."""
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    path = parsed.path.rstrip("/").lower()
    return f"{parsed.netloc.lower()}{path}"


def get_composite_fingerprint(job: NormalizedJob) -> str:
    """Generate a composite text fingerprint (title|location|department)."""
    t = clean_whitespace(job.title) or ""
    l = clean_whitespace(job.location) or ""
    d = clean_whitespace(job.department) or ""
    return f"{t.lower()}|{l.lower()}|{d.lower()}"


def compute_job_identity_key(job: NormalizedJob) -> str:
    """Compute canonical job_identity_key following priority order:
    1. Source job ID (id)
    2. Job URL (normalized)
    3. Application URL (normalized)
    4. Composite fingerprint (title + location + department)
    """
    if job.id and str(job.id).strip():
        return f"id:{str(job.id).strip()}"

    norm_job_url = normalize_url_key(job.job_url)
    if norm_job_url:
        return f"job_url:{norm_job_url}"

    norm_app_url = normalize_url_key(job.application_url)
    if norm_app_url:
        return f"app_url:{norm_app_url}"

    fingerprint = get_composite_fingerprint(job)
    return f"fp:{fingerprint}"
