import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.schemas.job import (
    CertificateSummaryResponse,
    GenerationJobCreate,
    JobCertificatesResponse,
    JobStatusResponse,
)

logger = logging.getLogger(__name__)


def create_generation_job(db: Session, job_in: GenerationJobCreate) -> GenerationJob:
    """Creates a GenerationJob and associated Certificate records in a single atomic transaction."""
    job = GenerationJob(
        event_name=job_in.event_name,
        event_date=job_in.event_date,
        status=JobStatus.PENDING,
        total_count=len(job_in.recipients),
        success_count=0,
        failure_count=0,
    )

    try:
        db.add(job)
        for recipient in job_in.recipients:
            certificate = Certificate(
                job=job,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                status=CertificateStatus.PENDING,
            )
            db.add(certificate)

        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        db.rollback()
        logger.error("Failed to persist generation job transaction: %s", exc, exc_info=True)
        raise


def get_job(db: Session, job_id: uuid.UUID) -> Optional[GenerationJob]:
    """Retrieves a GenerationJob by its primary key UUID."""
    return db.scalar(select(GenerationJob).where(GenerationJob.id == job_id))


def get_job_status_response(job: GenerationJob) -> JobStatusResponse:
    """Calculates progress metrics and constructs a JobStatusResponse schema."""
    completed_count = job.success_count + job.failure_count

    if job.total_count > 0:
        if completed_count == job.total_count:
            progress_percentage = 100.0
        else:
            progress_percentage = min(100.0, round((completed_count / job.total_count) * 100.0, 2))
    else:
        progress_percentage = 0.0

    return JobStatusResponse(
        job_id=job.id,
        event_name=job.event_name,
        event_date=job.event_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failure_count=job.failure_count,
        completed_count=completed_count,
        progress_percentage=progress_percentage,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def get_job_certificates_response(
    db: Session, job_id: uuid.UUID
) -> Optional[JobCertificatesResponse]:
    """Retrieves certificates belonging to a job in deterministic created_at ascending order."""
    job = get_job(db, job_id)
    if not job:
        return None

    certificates = db.scalars(
        select(Certificate)
        .where(Certificate.job_id == job_id)
        .order_by(Certificate.created_at.asc(), Certificate.id.asc())
    ).all()

    cert_summaries = [
        CertificateSummaryResponse(
            certificate_id=cert.id,
            recipient_name=cert.recipient_name,
            recipient_email=cert.recipient_email,
            status=cert.status,
            error_message=cert.error_message,
            created_at=cert.created_at,
            completed_at=cert.completed_at,
        )
        for cert in certificates
    ]

    return JobCertificatesResponse(
        job_id=job.id,
        certificates=cert_summaries,
    )
