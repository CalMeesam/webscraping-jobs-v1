"""API Endpoint tests using FastAPI TestClient."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import respx
import httpx
from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_extract_jobs_invalid_url():
    response = client.post("/extract-jobs", json={"url": "not a url"})
    assert response.status_code == 422
    data = response.json()
    assert "INVALID_URL" in data["detail"]


@respx.mock
def test_extract_jobs_greenhouse_success():
    with open(FIXTURES_DIR / "greenhouse_jobs_list.json", encoding="utf-8") as f:
        gh_data = json.load(f)

    respx.head("https://boards.greenhouse.io/figma").mock(return_value=httpx.Response(200))
    respx.get("https://boards-api.greenhouse.io/v1/boards/figma/jobs?content=true").mock(
        return_value=httpx.Response(200, json=gh_data)
    )

    response = client.post(
        "/extract-jobs",
        json={"url": "https://boards.greenhouse.io/figma", "max_jobs": 10, "include_details": True},
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["metadata"]["ats"] == "greenhouse"
    assert res_data["metadata"]["total_jobs_found"] == 2
    assert len(res_data["jobs"]) == 2
    assert res_data["jobs"][0]["title"] == "Senior Staff Software Engineer"
