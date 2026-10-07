import logging
from pathlib import Path
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus

logger = logging.getLogger(__name__)


def get_certificate_by_id(db: Session, certificate_id: uuid.UUID) -> Optional[Certificate]:
    """Retrieves a Certificate database model by its UUID primary key."""
    return db.scalar(select(Certificate).where(Certificate.id == certificate_id))


def resolve_certificate_file_for_download(
    cert: Certificate,
    base_storage_dir: Optional[Path] = None,
) -> Path:
    """Validates certificate status, verifies path security, and returns physical PDF file path."""
    if cert.status != CertificateStatus.SUCCESS:
        logger.warning(
            "Certificate download rejected for %s: status is %s", cert.id, cert.status
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate is not available for download because its status is {cert.status.value}.",
        )

    if not cert.file_path:
        logger.error("Certificate record %s has status SUCCESS but empty file_path", cert.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Certificate file path record is missing.",
        )

    storage_root = (
        base_storage_dir.resolve()
        if base_storage_dir is not None
        else Path(settings.STORAGE_PATH).resolve()
    )

    try:
        raw_path = Path(cert.file_path)
        resolved_file = raw_path.resolve()
    except Exception as exc:
        logger.error("Failed to resolve file path for certificate %s: %s", cert.id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid certificate file path format.",
        )

    try:
        resolved_file.relative_to(storage_root)
    except ValueError:
        logger.error(
            "Security violation: Certificate %s file_path '%s' resolves outside storage root '%s'",
            cert.id,
            cert.file_path,
            storage_root,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the requested certificate file path is restricted.",
        )

    if not resolved_file.exists() or not resolved_file.is_file():
        logger.error(
            "Physical PDF file missing on disk for certificate %s at path: %s",
            cert.id,
            resolved_file,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The requested certificate file is missing on storage.",
        )

    return resolved_file
