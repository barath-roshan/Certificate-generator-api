import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import (
    GenerationJobCreate,
    GenerationJobResponse,
    JobCertificatesResponse,
    JobStatusResponse,
)
from app.services.job_service import (
    create_generation_job,
    get_job,
    get_job_certificates_response,
    get_job_status_response,
)
from app.workers.certificate_worker import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
    description=(
        "Validates event details and recipient list, creates job and certificate records "
        "atomically in PENDING status, schedules background processing, and returns HTTP 202 Accepted."
    ),
)
def create_job(
    job_in: GenerationJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> GenerationJobResponse:
    """Submits a new bulk certificate generation job and schedules background processing."""
    try:
        job = create_generation_job(db=db, job_in=job_in)
        background_tasks.add_task(process_job, job.id)
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


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get generation job status and progress",
    description="Returns overall job status, progress percentage, and success/failure counts.",
)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """Retrieves progress and status metrics for a specified generation job."""
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return get_job_status_response(job)


@router.get(
    "/{job_id}/certificates",
    response_model=JobCertificatesResponse,
    summary="List certificates belonging to a job",
    description="Returns all certificate records and their status for the specified job in creation order.",
)
def list_job_certificates(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobCertificatesResponse:
    """Lists all certificate records associated with a generation job."""
    response = get_job_certificates_response(db, job_id)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return response
