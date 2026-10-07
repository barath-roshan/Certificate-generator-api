from collections.abc import Generator
from datetime import date, datetime, timezone
from pathlib import Path
import uuid

from fastapi import status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.generators import CertificateData, generate_certificate_pdf
from app.main import app
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.workers.certificate_worker import process_job


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture providing an isolated in-memory database session for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Fixture providing a TestClient with dependency overrides."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.workers.certificate_worker.get_worker_session", lambda: db_session)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_job_status_pending_and_processing(client: TestClient, db_session: Session) -> None:
    """Verify job status and progress calculation for pending and processing jobs."""
    job = GenerationJob(
        event_name="Progress Calculation Test",
        event_date=date(2026, 10, 7),
        status=JobStatus.PROCESSING,
        total_count=100,
        success_count=65,
        failure_count=2,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    response = client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["job_id"] == str(job.id)
    assert data["event_name"] == "Progress Calculation Test"
    assert data["status"] == "PROCESSING"
    assert data["total_count"] == 100
    assert data["success_count"] == 65
    assert data["failure_count"] == 2
    assert data["completed_count"] == 67
    assert data["progress_percentage"] == 67.0


def test_get_job_status_completed_100_percent(client: TestClient, db_session: Session) -> None:
    """Verify job status shows 100.0% progress when completed."""
    job = GenerationJob(
        event_name="Completed Job Test",
        event_date=date(2026, 10, 7),
        status=JobStatus.COMPLETED,
        total_count=5,
        success_count=5,
        failure_count=0,
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["completed_count"] == 5
    assert data["progress_percentage"] == 100.0


def test_get_job_status_not_found(client: TestClient) -> None:
    """Verify requesting non-existent job ID returns HTTP 404."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Job not found."}


def test_get_job_certificates_listing(client: TestClient, db_session: Session) -> None:
    """Verify certificate listing for a job returns certificates in deterministic order."""
    job = GenerationJob(
        event_name="Listing Test",
        event_date=date(2026, 10, 7),
        status=JobStatus.COMPLETED_WITH_ERRORS,
        total_count=2,
    )
    cert1 = Certificate(
        job=job,
        recipient_name="Barath Roshan",
        recipient_email="barath@example.com",
        status=CertificateStatus.SUCCESS,
        file_path="storage/certificates/sample.pdf",
    )
    cert2 = Certificate(
        job=job,
        recipient_name="Arun Kumar",
        recipient_email="arun@example.com",
        status=CertificateStatus.FAILED,
        error_message="Certificate PDF generation failed",
    )
    db_session.add(job)
    db_session.add_all([cert1, cert2])
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{job.id}/certificates")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["job_id"] == str(job.id)
    assert len(data["certificates"]) == 2

    c1 = data["certificates"][0]
    assert c1["recipient_name"] == "Barath Roshan"
    assert c1["status"] == "SUCCESS"
    assert c1["error_message"] is None

    c2 = data["certificates"][1]
    assert c2["recipient_name"] == "Arun Kumar"
    assert c2["status"] == "FAILED"
    assert c2["error_message"] == "Certificate PDF generation failed"


def test_get_job_certificates_not_found(client: TestClient) -> None:
    """Verify certificate listing for missing job returns HTTP 404."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/jobs/{random_id}/certificates")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_download_certificate_success(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify downloading a valid SUCCESS certificate returns PDF file stream."""
    monkeypatch.setattr("app.services.certificate_service.settings.STORAGE_PATH", str(tmp_path))

    job = GenerationJob(event_name="Download Test", status=JobStatus.COMPLETED, total_count=1, success_count=1)
    cert_id = uuid.uuid4()
    
    # Generate actual physical PDF using Phase 4 generator in tmp_path
    cert_data = CertificateData(certificate_id=cert_id, job_id=job.id, recipient_name="Download User", event_name="Download Test")
    pdf_path = generate_certificate_pdf(cert_data, base_storage_dir=tmp_path)

    cert = Certificate(
        id=cert_id,
        job=job,
        recipient_name="Download User",
        recipient_email="download@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=str(pdf_path),
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_download_certificate_not_success_status(client: TestClient, db_session: Session) -> None:
    """Verify downloading PENDING, PROCESSING, or FAILED certificate is rejected with 400 Bad Request."""
    job = GenerationJob(event_name="Pending Test", status=JobStatus.PENDING, total_count=1)
    cert = Certificate(
        job=job,
        recipient_name="Pending User",
        recipient_email="pending@example.com",
        status=CertificateStatus.PENDING,
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "not available for download" in response.json()["detail"]


def test_download_certificate_missing_physical_file(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify downloading a certificate whose physical file was deleted returns HTTP 500 cleanly."""
    monkeypatch.setattr("app.services.certificate_service.settings.STORAGE_PATH", str(tmp_path))

    job = GenerationJob(event_name="Missing File Test", status=JobStatus.COMPLETED, total_count=1)
    missing_file_path = tmp_path / "certificates" / str(job.id) / "non_existent.pdf"
    cert = Certificate(
        job=job,
        recipient_name="Missing File User",
        recipient_email="missing@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=str(missing_file_path),
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "The requested certificate file is missing on storage."}


def test_download_certificate_path_traversal_protection(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify path traversal attempt in file_path is rejected with HTTP 403 Forbidden."""
    monkeypatch.setattr("app.services.certificate_service.settings.STORAGE_PATH", str(tmp_path))

    job = GenerationJob(event_name="Security Test", status=JobStatus.COMPLETED, total_count=1)
    # Attempt to point outside tmp_path
    traversal_path = (tmp_path / ".." / "secret.txt").resolve()

    cert = Certificate(
        job=job,
        recipient_name="Hacker User",
        recipient_email="hacker@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=str(traversal_path),
    )
    db_session.add(job)
    db_session.add(cert)
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "restricted" in response.json()["detail"]


def test_end_to_end_job_lifecycle(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-End Test: POST job -> Background Processing -> GET Job -> GET Certificates -> Download PDF."""
    monkeypatch.setattr("app.generators.pdf_generator.settings.STORAGE_PATH", str(tmp_path))
    monkeypatch.setattr("app.services.certificate_service.settings.STORAGE_PATH", str(tmp_path))

    # 1. Submit Job
    payload = {
        "event_name": "E2E Masterclass 2026",
        "event_date": "2026-10-08",
        "recipients": [
            {"name": "Barath Roshan", "email": "barath@example.com"},
        ],
    }
    create_res = client.post("/api/v1/jobs", json=payload)
    assert create_res.status_code == status.HTTP_202_ACCEPTED
    job_id = uuid.UUID(create_res.json()["job_id"])

    # 2. Process Background Job
    process_job(job_id, db=db_session)

    # 3. Query Job Status API
    status_res = client.get(f"/api/v1/jobs/{job_id}")
    assert status_res.status_code == status.HTTP_200_OK
    status_data = status_res.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["progress_percentage"] == 100.0

    # 4. Query Certificates Listing API
    list_res = client.get(f"/api/v1/jobs/{job_id}/certificates")
    assert list_res.status_code == status.HTTP_200_OK
    list_data = list_res.json()
    assert len(list_data["certificates"]) == 1
    cert_summary = list_data["certificates"][0]
    assert cert_summary["status"] == "SUCCESS"
    cert_id = uuid.UUID(cert_summary["certificate_id"])

    # 5. Download Certificate PDF API
    download_res = client.get(f"/api/v1/certificates/{cert_id}")
    assert download_res.status_code == status.HTTP_200_OK
    assert download_res.headers["content-type"] == "application/pdf"
    assert download_res.content.startswith(b"%PDF-")


def test_download_certificate_openapi_schema() -> None:
    """Regression Test: Verify GET /api/v1/certificates/{certificate_id} OpenAPI schema has UUID path parameter and NO requestBody."""
    openapi = app.openapi()
    route_spec = openapi["paths"]["/api/v1/certificates/{certificate_id}"]["get"]
    
    assert "requestBody" not in route_spec, "GET /certificates/{certificate_id} must not require a requestBody"
    assert "parameters" in route_spec
    
    params = route_spec["parameters"]
    assert len(params) == 1
    param = params[0]
    assert param["name"] == "certificate_id"
    assert param["in"] == "path"
    assert param["required"] is True
    assert param["schema"]["type"] == "string"
    assert param["schema"]["format"] == "uuid"
