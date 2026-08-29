"""API Routes for job extraction engine."""

import json
from pathlib import Path
from urllib.parse import urlparse
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl, field_validator
from app.core.constants import ERROR_INVALID_URL
from app.core.logging import get_logger
from app.db.database import get_db_session
from app.db.models import ExtractionRun, JobSnapshot
from app.db.repository import (
    compare_runs,
    compute_customer_diff,
    export_comparison_to_csv,
    format_iso_utc,
    get_customer_history,
    save_extraction_run,
)
from app.models.request_models import ExtractionRequest
from app.models.response_models import ExtractionResponse
from app.orchestrator.extraction_manager import ExtractionManager
from app.utils.csv_exporter import JobCSVExporter
from app.utils.customer_config import CustomerConfigManager
from app.utils.identity_utils import compute_job_identity_key
from app.utils.url_utils import is_valid_url
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter()

STATIC_INDEX_PATH = Path(__file__).parent.parent / "static" / "index.html"


def resolve_customer_id(url: str, explicit_customer_id: str | None = None) -> str:
    """Resolve customer_id from explicit value, customer registry lookup, or URL host slug."""
    if explicit_customer_id and explicit_customer_id.strip():
        return explicit_customer_id.strip().lower()

    # 1. Match against config/customers.json registry
    try:
        config_manager = CustomerConfigManager()
        customers = config_manager.read_config()
        parsed_url = urlparse(url)
        url_netloc = parsed_url.netloc.lower()

        for customer in customers:
            for link in customer.get("career_links", []):
                link_url = link.get("url", "")
                if link_url:
                    parsed_link = urlparse(link_url)
                    if parsed_link.netloc.lower() == url_netloc:
                        is_shared_ats = any(
                            ats in url_netloc
                            for ats in ("lever.co", "greenhouse.io", "smartrecruiters.com", "myworkdayjobs.com")
                        )
                        if is_shared_ats:
                            link_slug = parsed_link.path.strip("/").split("/")[0] if parsed_link.path.strip("/") else ""
                            url_slug = parsed_url.path.strip("/").split("/")[0] if parsed_url.path.strip("/") else ""
                            if link_slug and url_slug and link_slug.lower() == url_slug.lower():
                                return customer["customer_id"]
                        else:
                            return customer["customer_id"]
    except Exception as e:
        logger.warning(f"Error resolving customer_id from config: {e}")

    # 2. Fallback: URL path / host parsing
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.strip("/").lower()

    if "lever.co" in netloc and path:
        parts = path.split("/")
        if parts and parts[0]:
            return parts[0]

    if "greenhouse.io" in netloc and path:
        parts = path.split("/")
        if parts and parts[0]:
            return parts[0]

    domain_parts = netloc.split(".")
    filtered_parts = [
        p
        for p in domain_parts
        if p
        not in (
            "www",
            "com",
            "co",
            "io",
            "org",
            "net",
            "myworkdayjobs",
            "careers",
            "enterpriseplatform",
            "jobs",
        )
    ]
    if filtered_parts:
        return filtered_parts[0]

    return "unknown-customer"


@router.get("/", status_code=status.HTTP_200_OK)
async def serve_ui():
    """Serves the job extractor web application UI."""
    if STATIC_INDEX_PATH.exists():
        return FileResponse(STATIC_INDEX_PATH)
    return {"message": "Adaptive Career Job Extraction Engine API"}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Health check endpoint with no external dependencies."""
    return {"status": "ok"}


@router.post("/extract-jobs", response_model=ExtractionResponse, status_code=status.HTTP_200_OK)
async def extract_jobs_endpoint(
    request: ExtractionRequest, background_tasks: BackgroundTasks
) -> ExtractionResponse:
    """Main extraction endpoint with background persistence and diff calculation."""
    logger.info(f"Received extract-jobs request for URL: {request.url}")

    if not request.url or not is_valid_url(request.url):
        logger.warning(f"Malformed URL provided: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: Provided URL syntax is invalid.",
        )

    customer_id = resolve_customer_id(request.url, request.customer_id)

    try:
        manager = ExtractionManager()
        response = await manager.extract_jobs(request)

        # Compute diff against the customer's prior run in DB (before background write adds current run)
        try:
            with get_db_session() as session:
                stmt = (
                    select(ExtractionRun)
                    .where(ExtractionRun.customer_id == customer_id)
                    .order_by(ExtractionRun.run_at.desc(), ExtractionRun.id.desc())
                    .limit(1)
                )
                previous_run = session.scalar(stmt)

                if previous_run:
                    prev_keys_stmt = select(JobSnapshot.job_identity_key).where(
                        JobSnapshot.run_id == previous_run.id
                    )
                    prev_keys = set(session.scalars(prev_keys_stmt).all())
                    curr_keys = set([compute_job_identity_key(j) for j in response.jobs])

                    new_keys = sorted(list(curr_keys - prev_keys))
                    removed_keys = sorted(list(prev_keys - curr_keys))
                    unchanged_keys = sorted(list(curr_keys & prev_keys))

                    prev_iso = format_iso_utc(previous_run.run_at)
                    diff_summary = {
                        "has_previous_run": True,
                        "latest_run_id": None,
                        "previous_run_id": previous_run.id,
                        "latest_run_at": None,
                        "previous_run_at": prev_iso,
                        "new_jobs_count": len(new_keys),
                        "removed_jobs_count": len(removed_keys),
                        "unchanged_jobs_count": len(unchanged_keys),
                        "new_job_keys": new_keys,
                        "removed_job_keys": removed_keys,
                        "unchanged_job_keys": unchanged_keys,
                        "message": f"{len(new_keys)} new jobs, {len(removed_keys)} removed since last check on {prev_iso}",
                    }
                else:
                    diff_summary = {
                        "has_previous_run": False,
                        "latest_run_id": None,
                        "previous_run_id": None,
                        "latest_run_at": None,
                        "previous_run_at": None,
                        "new_jobs_count": 0,
                        "removed_jobs_count": 0,
                        "unchanged_jobs_count": 0,
                        "new_job_keys": [],
                        "removed_job_keys": [],
                        "unchanged_job_keys": [],
                        "message": "Baseline run, no comparison available",
                    }

            response.metadata.diff_summary = diff_summary
            response.metadata.customer_id = customer_id
        except Exception as diff_err:
            logger.warning(f"Error computing diff summary for response: {diff_err}")

        # Async background persistence write (fire and forget)
        run_status = "success" if not response.metadata.errors else "partial"
        background_tasks.add_task(
            save_extraction_run,
            customer_id=customer_id,
            career_link_url=request.url,
            status=run_status,
            strategy_used=response.metadata.extraction_strategy,
            jobs_found_count=response.metadata.total_jobs_found,
            jobs_returned_count=response.metadata.total_jobs_returned,
            jobs=response.jobs,
        )

        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: {ve}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during job extraction: {exc}", exc_info=True)
        from app.models.response_models import ExtractionMetadata

        return ExtractionResponse(
            metadata=ExtractionMetadata(
                input_url=request.url,
                customer_id=customer_id,
                errors=["EXTRACTION_FAILED: " + str(exc)],
            ),
            jobs=[],
        )


@router.post("/extract-jobs/csv", status_code=status.HTTP_200_OK)
async def extract_jobs_csv_endpoint(request: ExtractionRequest):
    """Extract jobs and return as CSV file download."""
    logger.info(f"Received CSV export request for URL: {request.url}")

    if not request.url or not is_valid_url(request.url):
        logger.warning(f"Malformed URL provided: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: Provided URL syntax is invalid.",
        )

    try:
        manager = ExtractionManager()
        response = await manager.extract_jobs(request)

        if not response.jobs:
            logger.warning("No jobs extracted for CSV export")

        csv_content = JobCSVExporter.export_to_csv(response.jobs)

        source = response.metadata.source_type or "jobs"
        filename = f"{source}_jobs_export.csv"

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: {ve}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during CSV export: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CSV export failed: {str(exc)}",
        )


# Customer Configuration & Run History Endpoints


@router.get("/customers/{customer_id}/history", status_code=status.HTTP_200_OK)
async def get_customer_history_endpoint(customer_id: str, limit: int = 20):
    """Get extraction run history and diff summary for a specific customer."""
    try:
        history = get_customer_history(customer_id=customer_id, limit=limit)
        return history
    except Exception as e:
        logger.error(f"Error fetching history for customer '{customer_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch customer history: {str(e)}",
        )


@router.get("/runs/{target_run_id}/compare/{base_run_id}", status_code=status.HTTP_200_OK)
async def get_run_comparison_endpoint(target_run_id: int, base_run_id: int):
    """Compare two specific extraction runs (base_run vs target_run)."""
    try:
        comparison = compare_runs(base_run_id=base_run_id, target_run_id=target_run_id)
        return comparison
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Error comparing runs {base_run_id} vs {target_run_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Run comparison failed: {str(exc)}",
        )


@router.get("/runs/{target_run_id}/compare/{base_run_id}/csv")
async def get_run_comparison_csv_endpoint(target_run_id: int, base_run_id: int):
    """Download comparison diff between two runs as CSV."""
    try:
        comparison = compare_runs(base_run_id=base_run_id, target_run_id=target_run_id)
        csv_content = export_comparison_to_csv(comparison)
        
        filename = f"comparison_run_{base_run_id}_vs_{target_run_id}.csv"
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        )
    except Exception as exc:
        logger.error(f"Error generating comparison CSV for runs {base_run_id} vs {target_run_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison CSV export failed: {str(exc)}",
        )



class CareerLink(BaseModel):
    """Career link with label and URL."""

    label: str
    url: HttpUrl


class AddCustomerRequest(BaseModel):
    """Request model for adding a new customer."""

    customer_name: str
    director: str
    bizdev: list[str]
    career_links: list[CareerLink]

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("customer_name cannot be empty")
        return v.strip()

    @field_validator("career_links")
    @classmethod
    def validate_career_links(cls, v: list[CareerLink]) -> list[CareerLink]:
        if not v:
            raise ValueError("At least one career link is required")
        return v


class UpdateCustomerRequest(BaseModel):
    """Request model for updating an existing customer."""

    customer_name: str | None = None
    director: str | None = None
    bizdev: list[str] | None = None
    career_links: list[CareerLink] | None = None

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("customer_name cannot be empty")
        return v.strip() if v else None

    @field_validator("career_links")
    @classmethod
    def validate_career_links(cls, v: list[CareerLink] | None) -> list[CareerLink] | None:
        if v is not None and not v:
            raise ValueError("At least one career link is required")
        return v


@router.get("/customers", status_code=status.HTTP_200_OK)
async def get_customers():
    """Get all customers from the configuration file."""
    try:
        config_manager = CustomerConfigManager()
        customers = config_manager.read_config()
        return {"customers": customers}
    except FileNotFoundError as e:
        logger.error(f"Customer config file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer configuration file not found. Please ensure config/customers.json exists.",
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in customer config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Customer configuration file contains invalid JSON: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error reading customer config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read customer configuration: {str(e)}",
        )


@router.post("/customers", status_code=status.HTTP_201_CREATED)
async def add_customer(request: AddCustomerRequest):
    """Add a new customer to the configuration file."""
    try:
        config_manager = CustomerConfigManager()

        career_links = [
            {"label": link.label, "url": str(link.url)} for link in request.career_links
        ]

        customer = config_manager.add_customer(
            customer_name=request.customer_name,
            director=request.director,
            bizdev=request.bizdev,
            career_links=career_links,
        )

        logger.info(f"Successfully added customer: {customer['customer_id']}")
        return {
            "message": "Customer added successfully",
            "customer": customer,
        }

    except ValueError as e:
        logger.warning(f"Validation error adding customer: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error adding customer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add customer: {str(e)}",
        )


@router.put("/customers/{customer_id}", status_code=status.HTTP_200_OK)
async def update_customer(customer_id: str, request: UpdateCustomerRequest):
    """Update an existing customer in the configuration file."""
    try:
        config_manager = CustomerConfigManager()

        career_links = None
        if request.career_links is not None:
            career_links = [
                {"label": link.label, "url": str(link.url)} for link in request.career_links
            ]

        customer = config_manager.update_customer(
            customer_id=customer_id,
            customer_name=request.customer_name,
            director=request.director,
            bizdev=request.bizdev,
            career_links=career_links,
        )

        logger.info(f"Successfully updated customer: {customer['customer_id']}")
        return {
            "message": "Customer updated successfully",
            "customer": customer,
        }

    except ValueError as e:
        logger.warning(f"Validation error updating customer: {e}")
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in str(e).lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating customer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update customer: {str(e)}",
        )
