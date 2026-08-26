"""Verification script for live extraction persistence and diff calculation."""

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import app.db.repository
import app.db.database
from app.main import app as fastapi_app


def run_live_verification():
    temp_dir = tempfile.TemporaryDirectory()
    temp_db_path = Path(temp_dir.name) / "live_verification.db"

    orig_init_db = app.db.repository.init_db
    orig_get_session = app.db.repository.get_db_session

    app.db.repository.init_db = lambda db_path=None: orig_init_db(temp_db_path)
    app.db.repository.get_db_session = lambda db_path=None: orig_get_session(temp_db_path)
    app.db.database.get_db_session = lambda db_path=None: orig_get_session(temp_db_path)

    print("--- 1. INITIALIZING FRESH DATABASE ---")
    app.db.repository.init_db(temp_db_path)
    print(f"Isolated DB initialized at: {temp_db_path}")

    client = TestClient(fastapi_app)

    print("\n--- 2. RUNNING FIRST EXTRACTION (Baseline Run for Broadcom Workday) ---")
    req1 = {
        "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        "max_jobs": 10,
        "include_details": False,
    }
    res1 = client.post("/extract-jobs", json=req1)
    assert res1.status_code == 200, f"Extraction failed: {res1.text}"
    data1 = res1.json()
    meta1 = data1["metadata"]
    diff1 = meta1.get("diff_summary", {})

    print(f"Status Code: {res1.status_code}")
    print(f"Customer ID: {meta1.get('customer_id')}")
    print(f"Jobs Returned: {len(data1['jobs'])}")
    print(f"Diff Summary (First Run):")
    print(f"  - Has Previous Run: {diff1.get('has_previous_run')}")
    print(f"  - Summary Message: {diff1.get('message')}")
    assert diff1.get("has_previous_run") is False, "First run must be baseline with has_previous_run = False"

    print("\n--- 3. RUNNING SECOND EXTRACTION (Run 2 for Broadcom Workday) ---")
    req2 = {
        "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        "max_jobs": 10,
        "include_details": False,
    }
    res2 = client.post("/extract-jobs", json=req2)
    assert res2.status_code == 200, f"Extraction failed: {res2.text}"
    data2 = res2.json()
    meta2 = data2["metadata"]
    diff2 = meta2.get("diff_summary", {})

    print(f"Status Code: {res2.status_code}")
    print(f"Jobs Returned: {len(data2['jobs'])}")
    print(f"Diff Summary (Second Run):")
    print(f"  - Has Previous Run: {diff2.get('has_previous_run')}")
    print(f"  - New Jobs Count: {diff2.get('new_jobs_count')}")
    print(f"  - Removed Jobs Count: {diff2.get('removed_jobs_count')}")
    print(f"  - Unchanged Jobs Count: {diff2.get('unchanged_jobs_count')}")
    print(f"  - Summary Message: {diff2.get('message')}")
    assert diff2.get("has_previous_run") is True, "Second run must have has_previous_run = True"

    print("\n--- 4. RUNNING THIRD EXTRACTION (Run 3 for Broadcom Workday) ---")
    req3 = {
        "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        "max_jobs": 10,
        "include_details": False,
    }
    res3 = client.post("/extract-jobs", json=req3)
    assert res3.status_code == 200, f"Extraction failed: {res3.text}"
    data3 = res3.json()
    meta3 = data3["metadata"]
    diff3 = meta3.get("diff_summary", {})

    print(f"Status Code: {res3.status_code}")
    print(f"Jobs Returned: {len(data3['jobs'])}")
    print(f"Diff Summary (Third Run):")
    print(f"  - Has Previous Run: {diff3.get('has_previous_run')}")
    print(f"  - New Jobs Count: {diff3.get('new_jobs_count')}")
    print(f"  - Removed Jobs Count: {diff3.get('removed_jobs_count')}")
    print(f"  - Unchanged Jobs Count: {diff3.get('unchanged_jobs_count')}")
    print(f"  - Summary Message: {diff3.get('message')}")
    assert diff3.get("has_previous_run") is True
    assert diff3.get("unchanged_jobs_count") == len(data3["jobs"]), "All jobs should be unchanged on consecutive run"

    print("\n--- 5. QUERYING CUSTOMER HISTORY ENDPOINT (/customers/broadcom/history) ---")
    history_res = client.get("/customers/broadcom/history")
    assert history_res.status_code == 200
    history_data = history_res.json()
    print(f"Total Runs Recorded: {history_data.get('total_runs')}")
    print("Recorded Runs:")
    for run in history_data.get("runs", []):
        print(f"  - Run ID {run['id']}: {run['run_at']} | Status: {run['status']} | Jobs: {run['jobs_returned_count']} | Strategy: {run['strategy_used']}")

    try:
        temp_dir.cleanup()
    except Exception:
        pass

    print("\n==========================================")
    print("VERIFICATION COMPLETE: ALL CHECKS PASSED!")
    print("==========================================")


if __name__ == "__main__":
    run_live_verification()
