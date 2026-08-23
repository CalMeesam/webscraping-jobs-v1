# Adaptive Career Job Extraction Engine — Architecture

## Overview
The **Adaptive Career Job Extraction Engine** is a high-performance Python backend system built with FastAPI, Pydantic v2, `httpx`, BeautifulSoup4, lxml, and Playwright. Rather than acting as a simple webpage scraper, it operates as an **adaptive extraction system** that discovers authoritative job data sources, classifies site architectures, selects optimal extraction strategies, enriches job details, normalizes data models, and deduplicates listings.

## Extraction Strategy Hierarchy
1. **Known ATS Public APIs** (Greenhouse Public REST API, Workday CXS REST API, Oracle Fusion HCM REST API)
2. **Discovered Public APIs** (Regex/DOM scanned JSON endpoints passing schema validation)
3. **Static HTML Extraction** (JSON-LD `JobPosting` schema.org blocks, repeated DOM element heuristics)
4. **Browser-Rendered DOM Fallback & Network Inspection** (Playwright async Chromium with network traffic capture)
5. **Explicit Error Code Fallback** (Unsupported ATS like Lever, SmartRecruiters, Ashby return `ATS_DETECTED_BUT_UNSUPPORTED`)

## Data Flow Pipeline

```text
Input URL (POST /extract-jobs)
    │
    ▼
URL Resolver (httpx redirect chain, query param cleaning, scheme normalization)
    │
    ▼
Source Classifier & ATS Detector (Greenhouse, Workday, Oracle HCM, Lever, SmartRecruiters, Ashby)
    │
    ├─► Known Supported ATS (Greenhouse / Workday / Oracle HCM)
    │       ├── Greenhouse Extractor (Boards REST API)
    │       ├── Workday Extractor (CXS JSON REST API)
    │       └── Oracle HCM Extractor (recruitingCEJobRequisitions REST API)
    │
    ├─► Known Unsupported ATS (Lever / SmartRecruiters / Ashby) ──► Error: ATS_DETECTED_BUT_UNSUPPORTED
    │
    ├─► Generic API Discovered ──────────────────────► API Extractor
    │
    ├─► Static HTML ─────────────────────────────────► HTML Extractor (JSON-LD / DOM Heuristics)
    │
    └─► Dynamic JS Page ─────────────────────────────► Playwright Extractor (Network XHR inspection first, DOM second)
    │
    ▼
Candidate Job Validator (Domain scoping, social media rejection, non-job title filtering)
    │
    ▼
Detail Enrichment (Bounded by max_jobs & asyncio.Semaphore(5) concurrency control)
    │
    ▼
Normalization Engine (Location parsing, HTML section parsing, skills extraction, text cleaning)
    │
    ▼
Deduplication Engine (source_id -> job_url -> application_url -> composite fingerprint)
    │
    ▼
ExtractionResponse (JSON output with full ExtractionMetadata & NormalizedJob list)
```

## Native ATS Integrations

### 1. Workday CXS API (`WorkdayExtractor`)
- **Listing Endpoint**: `POST https://{tenant}.{host_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs`
- **Pagination**: Fixed limit 20 per request, async offset loop (`offset += 20`) until `offset >= total` or `max_jobs` limit reached.
- **Detail Endpoint**: `GET https://{tenant}.{host_num}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{externalPath}`
- **Location Normalization**:
  - Handles Workday's `"Country, City"` order (e.g., `"India, Bengaluru"`) vs Greenhouse's `"City, Country"` order.
  - Correctly leaves multi-location delimiter strings intact (e.g., `"CA • New York"`).
- **HTML Description Parsing**:
  - Slices sections cleanly without cutting through raw HTML tags mid-string.
  - Excludes trailing legal boilerplate, salary disclosure text, EEOC language, and interview accommodation disclaimers from the `benefits` field.

### 2. Greenhouse Public API (`GreenhouseExtractor`)
- **Board Token Extraction**: Regex extraction from URL paths (e.g. `boards.greenhouse.io/{board_token}`).
- **Listing Endpoint**: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- **Detail Endpoint**: `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}`

### 3. Oracle Fusion HCM REST API (`OracleHCMExtractor`)
- **URL Parameter Parser**: Extracts `host`, `lang`, and `siteNumber` from `/hcmUI/CandidateExperience/{lang}/sites/{siteNumber}/...` or `*.fa.ocs.oraclecloud.com`.
- **Listings REST Endpoint**:
  `GET https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields&finder=findReqs;siteNumber={siteNumber},facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit={limit},sortBy=POSTING_DATES_DESC`
- **Canonical Job URL Builder**: `https://{host}/hcmUI/CandidateExperience/{lang}/sites/{siteNumber}/job/{Id}`

---

## Candidate Job Validation Engine (`candidate_validator.py`)
To eliminate false positives and fake jobs scraped from page chrome or footer links:
1. **Domain Boundary Scoping**: Rejects links whose domain does not match the source site's base domain or a known ATS platform domain.
2. **Forbidden Social Media Domains**: Immediately rejects URLs belonging to `facebook.com`, `linkedin.com`, `twitter.com`, `x.com`, `youtube.com`, `instagram.com`, `glassdoor.com`, `github.com`, `t.co`.
3. **Non-Job Title Exclusions**: Rejects candidate links with non-job titles (`"Facebook"`, `"LinkedIn"`, `"Twitter"`, `"YouTube"`, `"Home"`, `"About Us"`, `"Privacy Policy"`, `"Terms of Use"`, `"User Agreement"`, `"Candidate Experience"`).
4. **Job Path Matching**: Requires candidate link paths to match job patterns (`/job/`, `/jobs/`, `/requisition/`, `/opening/`, `/career/`, or numeric IDs).
5. **Honest Empty Fallback**: If all candidates are filtered out, returns an honest `NO_JOBS_FOUND` empty result without returning unvalidated links.

---

## Windows Uvicorn Event Loop Policy & Thread Isolation
To prevent `NotImplementedError` when executing Playwright subprocesses under Uvicorn CLI `--reload` on Windows:
- Process entrypoint (`app/main.py`) sets `asyncio.WindowsProactorEventLoopPolicy()`.
- `PlaywrightExtractor` wraps Playwright execution in `await asyncio.to_thread(self._extract_sync, url, context)` with per-worker thread `WindowsProactorEventLoopPolicy` setup.

---

## Verification & Concurrency Engine
- **Concurrency Bound**: Detail enrichment HTTP requests are bounded by `asyncio.Semaphore(5)` to prevent network rate-limiting.
- **Partial Failure Resilience**: If individual job detail requests fail during enrichment, the response retains all discovered job listings, populates listing fields, increments `jobs_enrichment_failed`, and avoids failing the overall request.
