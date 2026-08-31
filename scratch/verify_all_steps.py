"""Comprehensive Verification Script for Steps 1 - 4
Performs:
1. Full extraction verification for all customers in config/customers.json
2. Pagination audit for Workday & Oracle HCM (max_jobs > 20, duplicate check)
3. Extraction/parsing defect sweep (HTML tags, entities, cuts, location swap, detection regressions)
4. Persistence & diff verification (run compare endpoint + CSV diff export)
"""

import sys
import json
import re
import html
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.db.database import get_db_session
from app.db.models import ExtractionRun, JobSnapshot
from app.utils.customer_config import CustomerConfigManager
from sqlalchemy import select, func

BASE_URL = "http://localhost:8000"

def run_step_1_and_3():
    print("=" * 80)
    print("STEP 1 & STEP 3: ALL CONFIGURED CUSTOMERS EXTRACTION & DEFECT SWEEP")
    print("=" * 80)

    config_mgr = CustomerConfigManager()
    customers = config_mgr.read_config()

    client = httpx.Client(base_url=BASE_URL, timeout=90.0)
    
    results = {}

    for cust in customers:
        cid = cust["customer_id"]
        cname = cust["customer_name"]
        career_links = cust.get("career_links", [])
        if not career_links:
            print(f"\n[-] Skipping {cname} ({cid}): No career links configured.")
            continue
        
        target_url = career_links[0]["url"]
        print(f"\n{'='*70}\n[>] CUSTOMER: {cname} (ID: {cid})\n    URL: {target_url}\n{'='*70}")

        payload = {
            "url": target_url,
            "customer_id": cid,
            "max_jobs": 15,
            "preferred_location": None,
            "include_details": True  # get enriched details for thorough check
        }

        try:
            resp = client.post("/extract-jobs", json=payload)
            if resp.status_code != 200:
                print(f"[-] HTTP Error {resp.status_code}: {resp.text}")
                results[cid] = {"error": f"HTTP {resp.status_code}: {resp.text}"}
                continue

            data = resp.json()
            meta = data.get("metadata", {})
            jobs = data.get("jobs", [])

            strategy = meta.get("extraction_strategy")
            source_type = meta.get("source_type")
            total_found = meta.get("total_jobs_found")
            total_returned = meta.get("total_jobs_returned", len(jobs))
            errors = meta.get("errors", [])

            print(f"[*] ATS Detected / Strategy: {strategy} (Source: {source_type})")
            print(f"[*] Jobs: Total Found = {total_found}, Total Returned = {total_returned}")
            print(f"[*] Errors/Warnings: {errors if errors else 'None'}")

            # Field Population & Defect Analysis
            field_stats = {
                "total_jobs": len(jobs),
                "has_title": sum(1 for j in jobs if j.get("title")),
                "has_description": sum(1 for j in jobs if j.get("description") and len(j.get("description", "").strip()) > 30),
                "has_location": sum(1 for j in jobs if j.get("location")),
                "has_skills": sum(1 for j in jobs if j.get("skills") and len(j.get("skills")) > 0),
                "has_responsibilities": sum(1 for j in jobs if j.get("responsibilities")),
                "has_requirements": sum(1 for j in jobs if j.get("requirements")),
                "has_department": sum(1 for j in jobs if j.get("department")),
            }

            print(f"[*] Field Population Stats (across {len(jobs)} jobs):")
            for k, v in field_stats.items():
                if k != "total_jobs":
                    print(f"    - {k}: {v}/{len(jobs)}")

            # Defect sweep
            defects = []
            html_tag_re = re.compile(r"<[^>]+>")
            html_entity_re = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")

            for i, j in enumerate(jobs):
                # Check title
                title = j.get("title") or ""
                if html_tag_re.search(title):
                    defects.append(f"Job #{i+1} Title contains raw HTML: '{title}'")
                if html_entity_re.search(title):
                    defects.append(f"Job #{i+1} Title contains unescaped HTML entity: '{title}'")

                # Check description
                desc = j.get("description") or ""
                if html_tag_re.search(desc):
                    defects.append(f"Job #{i+1} Description contains raw HTML tags")
                if html_entity_re.search(desc):
                    defects.append(f"Job #{i+1} Description contains unescaped HTML entity")

                # Check location
                loc = j.get("location")
                if loc:
                    if isinstance(loc, dict):
                        city = loc.get("city")
                        country = loc.get("country")
                        # Check if country looks like city or swapped
                        if city and country and city == country:
                            defects.append(f"Job #{i+1} Location city and country identical: '{city}'")
                    elif isinstance(loc, str):
                        if html_tag_re.search(loc):
                            defects.append(f"Job #{i+1} Location string contains HTML: '{loc}'")

            print(f"[*] Parsing Defect Sweep:")
            if defects:
                for d in defects[:5]:
                    print(f"    [!] DEFECT: {d}")
                if len(defects) > 5:
                    print(f"    ... and {len(defects) - 5} more defects.")
            else:
                print("    [+] Zero text/entity/HTML defects detected.")

            # Sample 3 full uncurated jobs
            sample_jobs = jobs[:3]

            results[cid] = {
                "customer_name": cname,
                "url": target_url,
                "strategy": strategy,
                "source_type": source_type,
                "total_found": total_found,
                "total_returned": total_returned,
                "errors": errors,
                "field_stats": field_stats,
                "defects": defects,
                "sample_jobs": sample_jobs
            }

        except Exception as e:
            print(f"[-] Exception extracting {cid}: {e}")
            results[cid] = {"error": str(e)}

    return results

def run_step_2_pagination():
    print("\n" + "=" * 80)
    print("STEP 2: PAGINATION AUDIT (WORKDAY & ORACLE HCM)")
    print("=" * 80)

    client = httpx.Client(base_url=BASE_URL, timeout=120.0)

    pagination_targets = [
        ("broadcom", "https://broadcom.wd1.myworkdayjobs.com/External_Career", 45),
        ("dell", "https://enterpriseplatform.dell.com/hcmUI/CandidateExperience/en/sites/careers/jobs?mode=location", 45)
    ]

    for cid, url, req_jobs in pagination_targets:
        print(f"\n[>] Auditing Pagination for {cid.upper()} (Requesting max_jobs={req_jobs})...")
        payload = {
            "url": url,
            "customer_id": cid,
            "max_jobs": req_jobs,
            "preferred_location": None,
            "include_details": False
        }

        resp = client.post("/extract-jobs", json=payload)
        if resp.status_code != 200:
            print(f"[-] Failed with HTTP {resp.status_code}: {resp.text}")
            continue

        data = resp.json()
        meta = data.get("metadata", {})
        jobs = data.get("jobs", [])

        print(f"    - Strategy Used: {meta.get('extraction_strategy')}")
        print(f"    - Total Found Reported: {meta.get('total_jobs_found')}")
        print(f"    - Total Returned: {len(jobs)}")
        
        # Check uniqueness of job keys in returned list
        keys = [j.get("identity_key") or j.get("id") or (j.get("title", "") + "_" + str(j.get("location", ""))) for j in jobs]
        unique_keys = set(keys)
        duplicates = len(keys) - len(unique_keys)
        
        print(f"    - Keys Count: {len(keys)}, Unique Keys: {len(unique_keys)}")
        if duplicates > 0:
            print(f"    [!] REGRESSION: {duplicates} duplicate jobs detected across pages!")
        else:
            print(f"    [+] Zero duplicate jobs across pagination pages.")

        # Check in DB
        with get_db_session() as session:
            latest_run = session.scalar(
                select(ExtractionRun).where(ExtractionRun.customer_id == cid).order_by(ExtractionRun.id.desc()).limit(1)
            )
            if latest_run:
                snaps = session.scalars(
                    select(JobSnapshot).where(JobSnapshot.run_id == latest_run.id)
                ).all()
                db_keys = [s.job_identity_key for s in snaps]
                db_dups = len(db_keys) - len(set(db_keys))
                print(f"    - Persisted Run #{latest_run.id}: {len(snaps)} snapshots, DB key duplicates: {db_dups}")

def run_step_4_diff():
    print("\n" + "=" * 80)
    print("STEP 4: PERSISTENCE & RUN-DIFF ENGINE VERIFICATION")
    print("=" * 80)

    client = httpx.Client(base_url=BASE_URL, timeout=30.0)

    test_customers = ["broadcom", "cisco", "figma"]
    for cid in test_customers:
        print(f"\n[>] Testing Run Comparison for Customer: {cid.upper()}")
        r_hist = client.get(f"/customers/{cid}/history")
        if r_hist.status_code != 200:
            print(f"[-] History fetch failed: {r_hist.status_code}")
            continue

        hist_data = r_hist.json()
        runs = hist_data.get("runs", [])
        if len(runs) < 2:
            print(f"[-] Not enough runs to compare (found {len(runs)})")
            continue

        target_run = runs[0]
        base_run = runs[1]
        print(f"    Comparing Target Run #{target_run['id']} vs Base Run #{base_run['id']}...")

        r_comp = client.get(f"/runs/{target_run['id']}/compare/{base_run['id']}")
        if r_comp.status_code != 200:
            print(f"    [-] Compare API failed: {r_comp.status_code}")
            continue

        comp_data = r_comp.json()
        summary = comp_data.get("summary", {})
        print(f"    [+] Comparison Summary:")
        print(f"        - Added Jobs    : {summary.get('added_count')}")
        print(f"        - Removed Jobs  : {summary.get('removed_count')}")
        print(f"        - Changed Jobs  : {summary.get('changed_count')}")
        print(f"        - Unchanged Jobs: {summary.get('unchanged_count')}")

        # Test CSV export
        r_csv = client.get(f"/runs/{target_run['id']}/compare/{base_run['id']}/csv")
        if r_csv.status_code == 200:
            csv_lines = r_csv.text.strip().splitlines()
            print(f"    [+] CSV Diff Export: HTTP 200, {len(csv_lines)} lines (Header + Rows)")
            print(f"        Header: {csv_lines[0] if csv_lines else 'None'}")
        else:
            print(f"    [-] CSV Export Failed: {r_csv.status_code}")

if __name__ == "__main__":
    results = run_step_1_and_3()
    # Save full raw results to a JSON file for inspection
    with open("scratch/full_verification_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved full verification results to scratch/full_verification_results.json")

    run_step_2_pagination()
    run_step_4_diff()
