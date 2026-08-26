"""API Routes for job extraction engine."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, HttpUrl, field_validator
from app.core.constants import ERROR_INVALID_URL
from app.core.logging import get_logger
from app.models.request_models import ExtractionRequest
from app.models.response_models import ExtractionResponse
from app.orchestrator.extraction_manager import ExtractionManager
from app.utils.url_utils import is_valid_url
from app.utils.csv_exporter import JobCSVExporter
from app.utils.customer_config import CustomerConfigManager

logger = get_logger(__name__)

router = APIRouter()

STATIC_INDEX_PATH = Path(__file__).parent.parent / "static" / "index.html"


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
async def extract_jobs_endpoint(request: ExtractionRequest) -> ExtractionResponse:
    """Main extraction endpoint."""
    logger.info(f"Received extract-jobs request for URL: {request.url}")

    if not request.url or not is_valid_url(request.url):
        logger.warning(f"Malformed URL provided: {request.url}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: Provided URL syntax is invalid.",
        )

    try:
        manager = ExtractionManager()
        response = await manager.extract_jobs(request)
        return response
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{ERROR_INVALID_URL}: {ve}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error during job extraction: {exc}", exc_info=True)
        # Return structured partial failure response instead of unhandled 500
        from app.models.response_models import ExtractionMetadata
        return ExtractionResponse(
            metadata=ExtractionMetadata(
                input_url=request.url,
                errors=["EXTRACTION_FAILED: " + str(exc)],
            ),
            jobs=[],
        )


@router.post("/extract-jobs/csv", status_code=status.HTTP_200_OK)
async def extract_jobs_csv_endpoint(request: ExtractionRequest):
    """Extract jobs and return as CSV file download.
    
    This endpoint performs the same extraction as /extract-jobs but returns
    the results as a downloadable CSV file with flattened fields.
    """
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
        
        # If extraction failed or no jobs found, still return CSV with headers
        if not response.jobs:
            logger.warning("No jobs extracted for CSV export")
        
        # Convert jobs to CSV
        csv_content = JobCSVExporter.export_to_csv(response.jobs)
        
        # Generate filename from source
        source = response.metadata.source or "jobs"
        filename = f"{source}_jobs_export.csv"
        
        # Return as downloadable CSV file
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
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


# Customer Configuration Endpoints

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
    
    @field_validator('customer_name')
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("customer_name cannot be empty")
        return v.strip()
    
    @field_validator('career_links')
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
    
    @field_validator('customer_name')
    @classmethod
    def validate_customer_name(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("customer_name cannot be empty")
        return v.strip() if v else None
    
    @field_validator('career_links')
    @classmethod
    def validate_career_links(cls, v: list[CareerLink] | None) -> list[CareerLink] | None:
        if v is not None and not v:
            raise ValueError("At least one career link is required")
        return v


@router.get("/customers", status_code=status.HTTP_200_OK)
async def get_customers():
    """Get all customers from the configuration file.
    
    Reads the config/customers.json file fresh on each request.
    Returns error if file is missing or contains invalid JSON.
    """
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
    """Add a new customer to the configuration file.
    
    Validates uniqueness of customer_id (generated from customer_name),
    validates all URLs, and writes safely using atomic file replacement.
    """
    try:
        config_manager = CustomerConfigManager()
        
        # Convert Pydantic HttpUrl objects to strings
        career_links = [
            {"label": link.label, "url": str(link.url)}
            for link in request.career_links
        ]
        
        # Add customer (validates uniqueness and writes atomically)
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
        # Duplicate customer_id or other validation error
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
    """Update an existing customer in the configuration file.
    
    Only provided fields will be updated. If customer_name changes and
    generates a different customer_id, validates the new ID is unique.
    """
    try:
        config_manager = CustomerConfigManager()
        
        # Convert Pydantic HttpUrl objects to strings if career_links provided
        career_links = None
        if request.career_links is not None:
            career_links = [
                {"label": link.label, "url": str(link.url)}
                for link in request.career_links
            ]
        
        # Update customer
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
        # Customer not found or validation error
        logger.warning(f"Validation error updating customer: {e}")
        status_code = status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
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


