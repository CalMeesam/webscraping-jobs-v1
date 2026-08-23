"""API Routes for job extraction engine."""

from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from app.core.constants import ERROR_INVALID_URL
from app.core.logging import get_logger
from app.models.request_models import ExtractionRequest
from app.models.response_models import ExtractionResponse
from app.orchestrator.extraction_manager import ExtractionManager
from app.utils.url_utils import is_valid_url

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
