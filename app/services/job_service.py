import logging
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.schemas.job import GenerationJobCreate

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
