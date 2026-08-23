# Adaptive Career Job Extraction Engine

A greenfield Python backend application that accepts company websites, career pages, job boards, or ATS URLs, and automatically discovers, extracts, enriches, normalizes, and returns structured job listings in JSON.

## Features
- **Adaptive Extraction Hierarchy**: Prefers cheap HTTP APIs over browser automation.
- **Native ATS API Support**:
  - **Greenhouse**: Full support via `boards-api.greenhouse.io`
  - **Workday**: Full support via Workday CXS JSON API endpoints with fixed `limit: 20` offset pagination.
- **Unsupported ATS Guardrails**: Explicitly returns `ATS_DETECTED_BUT_UNSUPPORTED` for Lever, SmartRecruiters, and Ashby instead of low-quality HTML scraping.
- **Static HTML Extractor**: JSON-LD `JobPosting` schema parsing + repeated DOM element heuristics.
- **Playwright Browser Fallback**: Asynchronous Chromium with XHR/Fetch network traffic inspection first, post-render DOM fallback second.
- **Detail Enrichment**: Async semaphore concurrency (default 5) bounded by `max_jobs`.
- **Normalization & Deduplication**: Cleans HTML tags, normalizes whitespace, formats locations, and deduplicates by `source_id` -> `job_url` -> `application_url` -> `composite fingerprint`.
- **Structured JSON Logging**: All pipeline decisions logged as structured JSON.

## Installation & Setup

1. **Install Python Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Install Playwright Chromium**:
```bash
python -m playwright install chromium
```

3. **Run the FastAPI Server**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### `GET /health`
Returns system health status:
```json
{
  "status": "ok"
}
```

### `POST /extract-jobs`
Request body:
```json
{
  "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
  "max_jobs": 5,
  "include_details": true
}
```

Response:
```json
{
  "metadata": {
    "input_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "resolved_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    "source_type": "ats",
    "ats": "workday",
    "extraction_strategy": "workday_cxs_api",
    "total_jobs_found": 2000,
    "total_jobs_returned": 5,
    "warnings": [],
    "errors": []
  },
  "jobs": [
    {
      "id": "JR2016463",
      "title": "Manager, Distinguished Engineer - DGX Systems Software",
      "location": "Santa Clara, CA",
      "department": null,
      "description": "NVIDIA DGX systems are the foundation...",
      "employment_type": null,
      "job_url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Manager--Distinguished-Engineer---DGX-Systems-Software_JR2016463",
      "application_url": null,
      "source": "nvidia",
      "ats": "workday"
    }
  ]
}
```

## Testing

Run unit tests:
```bash
pytest
```
