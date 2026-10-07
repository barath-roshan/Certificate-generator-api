from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.generators import CertificateData, PDFGenerationError, generate_certificate_pdf
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob

logger = logging.getLogger(__name__)


def get_worker_session() -> Session:
    """Creates a new database session for worker execution."""
    return SessionLocal()


def process_job(job_id: uuid.UUID, db: Optional[Session] = None) -> None:
    """Orchestrates background processing for a bulk certificate generation job."""
    logger.info("Starting background processing for job %s", job_id)
    session_created = False
    if db is None:
        db = get_worker_session()
        session_created = True

    try:
        job = db.scalar(select(GenerationJob).where(GenerationJob.id == job_id))
        if not job:
            logger.error("Job %s not found in database for background processing", job_id)
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        certificates = db.scalars(
            select(Certificate)
            .where(
                Certificate.job_id == job_id,
                Certificate.status == CertificateStatus.PENDING,
            )
            .order_by(Certificate.created_at)
        ).all()

        success_count = job.success_count
        failure_count = job.failure_count

        for cert in certificates:
            logger.info("Processing certificate %s for recipient %s", cert.id, cert.recipient_email)
            cert.status = CertificateStatus.PROCESSING
            db.commit()

            try:
                cert_data = CertificateData(
                    certificate_id=cert.id,
                    job_id=job.id,
                    recipient_name=cert.recipient_name,
                    event_name=job.event_name,
                    event_date=job.event_date,
                )

                output_path = generate_certificate_pdf(cert_data)

                cert.status = CertificateStatus.SUCCESS
                cert.file_path = str(output_path)
                cert.error_message = None
                cert.completed_at = datetime.now(timezone.utc)
                success_count += 1
                logger.info("Successfully generated certificate %s", cert.id)

            except PDFGenerationError as pge:
                logger.warning("PDF generation failed for certificate %s: %s", cert.id, pge)
                cert.status = CertificateStatus.FAILED
                cert.error_message = "Certificate PDF generation failed"
                cert.completed_at = datetime.now(timezone.utc)
                failure_count += 1

            except Exception as exc:
                logger.error(
                    "Unexpected error processing certificate %s: %s",
                    cert.id,
                    exc,
                    exc_info=True,
                )
                cert.status = CertificateStatus.FAILED
                cert.error_message = "Certificate PDF generation failed due to an unexpected error"
                cert.completed_at = datetime.now(timezone.utc)
                failure_count += 1

            db.commit()

        job.success_count = success_count
        job.failure_count = failure_count
        job.completed_at = datetime.now(timezone.utc)

        if failure_count == 0 and success_count == job.total_count:
            job.status = JobStatus.COMPLETED
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS

        db.commit()
        logger.info(
            "Completed processing job %s with final status=%s (success=%d, failure=%d, total=%d)",
            job_id,
            job.status,
            success_count,
            failure_count,
            job.total_count,
        )

    except Exception as fatal_exc:
        logger.error(
            "Fatal error during processing of job %s: %s", job_id, fatal_exc, exc_info=True
        )
        if "job" in locals() and job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if session_created and db:
            db.close()
