from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import GenerationJobCreate, GenerationJobResponse
from app.services.job_service import create_generation_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
    description=(
        "Validates event details and recipient list, creates job and certificate records "
        "atomically in PENDING status, and returns HTTP 202 Accepted with the generated job ID."
    ),
)
def create_job(
    job_in: GenerationJobCreate,
    db: Session = Depends(get_db),
) -> GenerationJobResponse:
    """Submits a new bulk certificate generation job."""
    try:
        job = create_generation_job(db=db, job_in=job_in)
        return GenerationJobResponse(
            job_id=job.id,
            status=job.status,
            total_count=job.total_count,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the generation job.",
        )
