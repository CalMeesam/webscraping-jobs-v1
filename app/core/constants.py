"""Constants used throughout the job extraction engine."""

# Error Codes
ERROR_INVALID_URL = "INVALID_URL"
ERROR_URL_UNREACHABLE = "URL_UNREACHABLE"
ERROR_REDIRECT_LOOP = "REDIRECT_LOOP"
ERROR_CAREER_PAGE_NOT_FOUND = "CAREER_PAGE_NOT_FOUND"
ERROR_ATS_DETECTED_BUT_UNSUPPORTED = "ATS_DETECTED_BUT_UNSUPPORTED"
ERROR_EXTRACTION_FAILED = "EXTRACTION_FAILED"
ERROR_NO_JOBS_FOUND = "NO_JOBS_FOUND"
ERROR_PLAYWRIGHT_FAILED = "PLAYWRIGHT_FAILED"
ERROR_DETAIL_ENRICHMENT_FAILED = "DETAIL_ENRICHMENT_FAILED"

# Query parameters prefixes to strip from URLs
TRACKING_PARAM_PREFIXES = (
    "utm_",
    "gclid",
    "fbclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
)

# Supported and Known ATS domain patterns
ATS_PATTERNS = {
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
    "workday": ["myworkdayjobs.com"],
    "oracle_hcm": ["oraclecloud.com", "hcmUI/CandidateExperience"],
    "lever": ["jobs.lever.co", "lever.co"],
    "smartrecruiters": ["smartrecruiters.com"],
    "ashby": ["ashbyhq.com"],
}

SUPPORTED_ATS_VENDORS = {"greenhouse", "workday", "oracle_hcm"}

# Career URL Discovery Keywords
CAREER_URL_KEYWORDS = [
    "career",
    "careers",
    "job",
    "jobs",
    "join-us",
    "joinus",
    "work-with-us",
    "open-positions",
    "opportunities",
]

# API Discovery Schema Field Keywords (Minimum 3 required for positive API validation)
JOB_SCHEMA_KEYWORDS = [
    "title",
    "job",
    "location",
    "department",
    "description",
    "requisition",
    "position",
]
