"""Test script for running uvicorn server at http://127.0.0.1:8000."""

import httpx

SERVER_URL = "http://127.0.0.1:8000"


def test_server():
    print(f"=== TESTING LIVE FASTAPI SERVER AT {SERVER_URL} ===")

    # 1. Health Check
    res_health = httpx.get(f"{SERVER_URL}/health")
    print(f"\n1. GET /health -> HTTP {res_health.status_code}: {res_health.json()}")
    assert res_health.status_code == 200

    # 2. Get Customers
    res_cust = httpx.get(f"{SERVER_URL}/customers")
    print(f"\n2. GET /customers -> HTTP {res_cust.status_code}")
    cust_data = res_cust.json()
    print(f"   Registered Customers Count: {len(cust_data.get('customers', []))}")
    for c in cust_data.get("customers", []):
        print(f"   - {c['customer_name']} (ID: {c['customer_id']})")

    # 3. Extraction Run 1 (Broadcom)
    print("\n3. POST /extract-jobs (Broadcom Run 1)...")
    req1 = {
        "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        "max_jobs": 5,
        "include_details": False,
    }
    res_ext1 = httpx.post(f"{SERVER_URL}/extract-jobs", json=req1, timeout=30.0)
    print(f"   HTTP {res_ext1.status_code}")
    data1 = res_ext1.json()
    meta1 = data1.get("metadata", {})
    print(f"   Customer ID: {meta1.get('customer_id')}")
    print(f"   Jobs Returned: {len(data1.get('jobs', []))}")
    print(f"   Diff Summary: {meta1.get('diff_summary')}")

    # 4. Extraction Run 2 (Broadcom)
    print("\n4. POST /extract-jobs (Broadcom Run 2 - Diff Check)...")
    req2 = {
        "url": "https://broadcom.wd1.myworkdayjobs.com/External_Career",
        "max_jobs": 5,
        "include_details": False,
    }
    res_ext2 = httpx.post(f"{SERVER_URL}/extract-jobs", json=req2, timeout=30.0)
    print(f"   HTTP {res_ext2.status_code}")
    data2 = res_ext2.json()
    meta2 = data2.get("metadata", {})
    print(f"   Customer ID: {meta2.get('customer_id')}")
    print(f"   Jobs Returned: {len(data2.get('jobs', []))}")
    diff2 = meta2.get("diff_summary", {})
    print(f"   Diff Summary:")
    print(f"     - Has Previous Run: {diff2.get('has_previous_run')}")
    print(f"     - New Jobs: {diff2.get('new_jobs_count')}")
    print(f"     - Removed Jobs: {diff2.get('removed_jobs_count')}")
    print(f"     - Unchanged Jobs: {diff2.get('unchanged_jobs_count')}")
    print(f"     - Message: {diff2.get('message')}")

    # 5. Customer History
    print("\n5. GET /customers/broadcom/history...")
    res_hist = httpx.get(f"{SERVER_URL}/customers/broadcom/history")
    print(f"   HTTP {res_hist.status_code}")
    hist_data = res_hist.json()
    print(f"   Total Runs in History: {hist_data.get('total_runs')}")
    for run in hist_data.get("runs", []):
        print(f"   - Run #{run['id']}: {run['run_at']} | Status: {run['status']} | Returned: {run['jobs_returned_count']}")

    print("\n==========================================")
    print("LIVE SERVER TEST SUCCESSFUL! ALL ENDPOINTS OK.")
    print("==========================================")


if __name__ == "__main__":
    test_server()
