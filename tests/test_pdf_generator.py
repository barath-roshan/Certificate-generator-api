from datetime import date
from pathlib import Path
import uuid

import pytest

from app.generators.pdf_generator import (
    CertificateData,
    PDFGenerationError,
    generate_certificate_pdf,
)


def test_generate_certificate_pdf_success(tmp_path: Path) -> None:
    """Verify successful PDF generation in temporary directory."""
    job_id = uuid.uuid4()
    cert_id = uuid.uuid4()

    data = CertificateData(
        certificate_id=cert_id,
        job_id=job_id,
        recipient_name="Barath Roshan",
        event_name="Advanced Python Workshop",
        event_date=date(2026, 10, 7),
    )

    pdf_path = generate_certificate_pdf(data, base_storage_dir=tmp_path)

    assert isinstance(pdf_path, Path)
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 0

    expected_path = tmp_path / "certificates" / str(job_id) / f"{cert_id}.pdf"
    assert pdf_path == expected_path


def test_pdf_magic_header(tmp_path: Path) -> None:
    """Verify that generated output file starts with valid PDF magic bytes (%PDF-)."""
    data = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        recipient_name="Arun Kumar",
        event_name="FastAPI Mastery",
        event_date=date(2026, 10, 7),
    )

    pdf_path = generate_certificate_pdf(data, base_storage_dir=tmp_path)

    with open(pdf_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_pdf_contains_recipient_text(tmp_path: Path) -> None:
    """Verify recipient name and event name text are rendered into the PDF stream."""
    recipient_name = "Unique Test Student"
    event_name = "Unique Event Title 2026"

    data = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        recipient_name=recipient_name,
        event_name=event_name,
        event_date=date(2026, 10, 7),
    )

    pdf_path = generate_certificate_pdf(data, base_storage_dir=tmp_path)
    content = pdf_path.read_bytes()

    assert recipient_name.encode("utf-8") in content
    assert event_name.encode("utf-8") in content


def test_different_ids_produce_different_files(tmp_path: Path) -> None:
    """Verify separate certificate IDs yield distinct PDF files."""
    job_id = uuid.uuid4()
    data1 = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=job_id,
        recipient_name="Alice",
        event_name="AI Summit",
        event_date=date(2026, 10, 7),
    )
    data2 = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=job_id,
        recipient_name="Bob",
        event_name="AI Summit",
        event_date=date(2026, 10, 7),
    )

    pdf_path1 = generate_certificate_pdf(data1, base_storage_dir=tmp_path)
    pdf_path2 = generate_certificate_pdf(data2, base_storage_dir=tmp_path)

    assert pdf_path1 != pdf_path2
    assert pdf_path1.name != pdf_path2.name
    assert pdf_path1.exists()
    assert pdf_path2.exists()


def test_pdf_generation_without_event_date(tmp_path: Path) -> None:
    """Verify PDF generator handles None event_date gracefully."""
    data = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        recipient_name="No Date Student",
        event_name="Ongoing Course",
        event_date=None,
    )

    pdf_path = generate_certificate_pdf(data, base_storage_dir=tmp_path)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0


def test_invalid_output_directory_raises_exception(tmp_path: Path) -> None:
    """Verify that an unusable storage directory raises PDFGenerationError."""
    file_as_dir = tmp_path / "blocker_file"
    file_as_dir.write_text("blocker")

    invalid_storage = file_as_dir / "certificates"

    data = CertificateData(
        certificate_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        recipient_name="Test Fail",
        event_name="Fail Event",
    )

    with pytest.raises(PDFGenerationError):
        generate_certificate_pdf(data, base_storage_dir=invalid_storage)
