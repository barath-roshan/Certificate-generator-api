from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import GenerationJobCreate, GenerationJobResponse
from app.services.job_service import create_generation_job
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
