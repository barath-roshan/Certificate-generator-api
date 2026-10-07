import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.certificate_service import (
    get_certificate_by_id,
    resolve_certificate_file_for_download,
)

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get(
    "/{certificate_id}",
    response_class=FileResponse,
    summary="Download generated certificate PDF",
    description="Downloads the physical PDF certificate file if status is SUCCESS and file exists.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Successfully generated PDF certificate file stream.",
        },
        400: {"description": "Certificate is not available for download (status is not SUCCESS)."},
        403: {"description": "Access to requested file path is restricted."},
        404: {"description": "Certificate not found."},
        500: {"description": "Physical PDF file is missing on storage."},
    },
)
def download_certificate(
    certificate_id: uuid.UUID = Path(
        ...,
        description="The unique UUID identifier of the certificate to download",
    ),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Downloads the generated PDF file for a specified certificate."""
    cert = get_certificate_by_id(db, certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )

    pdf_file = resolve_certificate_file_for_download(cert)

    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=f"certificate-{certificate_id}.pdf",
    )
