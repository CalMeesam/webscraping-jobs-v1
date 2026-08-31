# Adaptive Career Job Extraction Engine 🚀

An enterprise-grade, multi-platform career portal scraping and organizational intelligence system built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL / SQLite**.

Designed to automatically discover, extract, normalize, and monitor job openings across diverse Applicant Tracking Systems (ATS) and custom corporate career pages, with automatic run-to-run differential change tracking and persistence.

---

## 🌟 Key Features

- **Multi-ATS Native & Fallback Extractors**:
  - **Workday**: Direct CXS REST API pagination & detail enrichment.
  - **Greenhouse**: High-throughput public REST API parser.
  - **Lever**: Structured posting extraction with department & location normalization.
  - **Oracle HCM Cloud**: Candidate Experience REST API integration.
  - **Phenom People / Dynamic SPAs**: Intelligent Playwright browser fallback with DOM heuristic parsing.
- **Run-to-Run Diff Engine**:
  - Automatically identifies **New**, **Removed**, **Changed**, and **Unchanged** jobs between sequential extraction runs.
  - Calculates detailed field-level diffs (title changes, location updates, description modifications).
  - Generates downloadable CSV comparison reports (`/runs/{target_id}/compare/{base_id}/csv`).
- **Dual PostgreSQL & SQLite Persistence**:
  - Stores every extraction run in `extraction_runs` and individual job snapshots in `job_snapshots`.
  - JSON snapshot storage with deterministic `job_identity_key` deduplication and indexing.
- **LLM Extraction Refinement Pipeline**:
  - Optional AI-powered schema refinement behind a feature flag (`ENABLE_LLM_REFINEMENT=true`).
- **Interactive Cockpit UI**:
  - Glassmorphic dark UI with client roster grid, quick ATS presets, live diff delta badges, and history modal with comparison tabs.
- **Client Portfolio Management**:
  - Config-driven client registry (`config/customers.json`) with FastAPI CRUD endpoints and UI modal support.

---

## 🏗️ System Architecture

```
                                  [ User / Web UI / REST Client ]
                                                 │
                                                 ▼
                                        [ FastAPI Router ]
                                                 │
                        ┌────────────────────────┼────────────────────────┐
                        ▼                        ▼                        ▼
               [ ATS Detector ]        [ Customer Registry ]     [ Run Diff Engine ]
                        │                        │                        │
        ┌───────────────┴───────────────┐        │                        ▼
        ▼                               ▼        │              [ SQLAlchemy Models ]
 [ Native Extractors ]          [ Fallback Engine ]                      │
  • Workday (CXS API)            • Generic HTML / JSON-LD                ├── extraction_runs
  • Greenhouse (REST API)        • Playwright Headless Browser           └── job_snapshots
  • Lever (REST API)                                                     │
  • Oracle HCM (REST API)                                         [ PostgreSQL / SQLite ]
        │
        ▼
 [ Normalizer & Deduplicator ] ──▶ [ Detail Enricher ] ──▶ [ Database Persistence ]
```

---

## 📋 Supported ATS Platforms & Strategies

| Platform / Vendor | Detection Rule | Extraction Strategy | Primary Targets |
| :--- | :--- | :--- | :--- |
| **Workday** | `myworkdayjobs.com` | `workday_cxs_api` | Broadcom, Target, Walmart |
| **Greenhouse** | `boards.greenhouse.io`, `job-boards.greenhouse.io` | `greenhouse_api` | Figma, Sumologic, Stripe |
| **Lever** | `jobs.lever.co` | `lever_api` | Spotify, Netflix |
| **Oracle HCM Cloud** | `hcmUI/CandidateExperience`, `oraclecloud.com` | `oracle_hcm_api` | Dell Technologies, EXL Service |
| **Phenom People / SPAs** | `careers.*.com` | `playwright_fallback` | Cisco Systems, HPE |
| **Generic Portals** | Static corporate sites | `static_html` (JSON-LD / Microdata) | Custom career pages |

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- (Optional) PostgreSQL 14+ or Docker

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-org/web-scrapping-jobs.git
cd web-scrapping-jobs

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Configuration
Copy `.env.example` to `.env` and adjust settings as needed:
```bash
cp .env.example .env
```

Key environment variables:
```ini
APP_ENV=development
DATABASE_URL=sqlite:///./data/jobs.db  # Or postgresql://user:pass@localhost:5432/jobs_db
PORT=8000
PLAYWRIGHT_HEADLESS=true
ENABLE_LLM_REFINEMENT=false
```

### 4. Running with Docker Compose (PostgreSQL + App)
```bash
docker-compose up --build -d
```

### 5. Running Locally (FastAPI)
```bash
uvicorn app.main:app --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 📡 REST API Reference

### Job Extraction
- **`POST /extract-jobs`**: Trigger extraction for a career URL.
  ```json
  {
    "url": "https://boards.greenhouse.io/figma",
    "customer_id": "figma",
    "max_jobs": 25,
    "preferred_location": "San Francisco",
    "include_details": true
  }
  ```

### Customer Management
- **`GET /customers`**: List all configured enterprise clients.
- **`POST /customers`**: Register a new customer profile.
- **`PUT /customers/{customer_id}`**: Update customer details and career links.
- **`GET /customers/{customer_id}/history`**: Retrieve extraction run history for a customer.

### Run Comparison & Diffing
- **`GET /runs/{target_id}/compare/{base_id}`**: Compute Added, Removed, Changed, and Unchanged jobs between two runs.
- **`GET /runs/{target_id}/compare/{base_id}/csv`**: Download comparison report as a formatted CSV file.

### Health Check
- **`GET /health`**: Returns engine status (`{"status": "ok"}`).

---

## 🔍 Database Inspection CLI Tool

To inspect historical runs, snapshots, and customer portfolios directly from your terminal:

```bash
python scratch/view_postgres_data.py
```

Sample output:
```text
===========================================================================
           POSTGRESQL DATABASE INSPECTOR & VIEWER
===========================================================================

[*] DATABASE SUMMARY:
    - Total Extraction Runs : 65
    - Total Job Snapshots   : 480

[*] RUNS PARTITIONED BY CUSTOMER:
    - Customer 'broadcom': 20 runs
    - Customer 'figma': 16 runs
    - Customer 'cisco': 12 runs
    - Customer 'dell': 8 runs
    - Customer 'spotify': 5 runs
    - Customer 'hewlett-packard-enterprise': 4 runs

[*] RECENT EXTRACTION RUNS:
  ID    Customer                    Run At (UTC)             Status     Jobs Ret/Found
  ------------------------------------------------------------------------------------
  #65   hewlett-packard-enterprise  2026-08-31 19:18:00.63   SUCCESS    10/13
  #63   dell                        2026-08-31 18:57:12.34   SUCCESS    45/386
  #62   broadcom                    2026-08-31 18:57:07.70   SUCCESS    45/385
```

---

## 🧪 Running Automated Tests

Run the full pytest test suite (85 unit and integration tests):

```bash
pytest tests/ -v
```

Run test suite with short summary:
```bash
pytest tests/ -q
```

---

## 🛡️ License

Proprietary enterprise software. All rights reserved.
