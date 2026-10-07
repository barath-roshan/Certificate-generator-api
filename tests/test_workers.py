from collections.abc import Generator
from datetime import date
from pathlib import Path
import uuid

from fastapi import status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.generators import PDFGenerationError
from app.main import app
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob
from app.workers.certificate_worker import process_job


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture providing an isolated in-memory database session for worker tests."""
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
    """Fixture providing a TestClient with get_db dependency override and worker session override."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.workers.certificate_worker.get_worker_session", lambda: db_session)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_process_job_all_success(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify worker processes all certificates successfully and marks job COMPLETED."""
    # Direct output directory to pytest tmp_path
    monkeypatch.setattr("app.generators.pdf_generator.settings.STORAGE_PATH", str(tmp_path))

    job = GenerationJob(
        event_name="Python Automation Workshop",
        event_date=date(2026, 10, 7),
        status=JobStatus.PENDING,
        total_count=2,
    )
    cert1 = Certificate(
        job=job,
        recipient_name="Barath Roshan",
        recipient_email="barath@example.com",
        status=CertificateStatus.PENDING,
    )
    cert2 = Certificate(
        job=job,
        recipient_name="Arun Kumar",
        recipient_email="arun@example.com",
        status=CertificateStatus.PENDING,
    )
    db_session.add(job)
    db_session.add_all([cert1, cert2])
    db_session.commit()
    db_session.refresh(job)

    # Process job synchronously
    process_job(job.id, db=db_session)
    db_session.refresh(job)

    assert job.status == JobStatus.COMPLETED
    assert job.success_count == 2
    assert job.failure_count == 0
    assert job.completed_at is not None

    certs = db_session.scalars(select(Certificate).where(Certificate.job_id == job.id)).all()
    assert len(certs) == 2
    for cert in certs:
        assert cert.status == CertificateStatus.SUCCESS
        assert cert.file_path is not None
        assert Path(cert.file_path).exists()
        assert cert.error_message is None
        assert cert.completed_at is not None


def test_process_job_failure_isolation(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify one failing certificate does not halt processing of subsequent certificates."""
    monkeypatch.setattr("app.generators.pdf_generator.settings.STORAGE_PATH", str(tmp_path))

    job = GenerationJob(
        event_name="Fault Isolation Test Event",
        event_date=date(2026, 10, 7),
        status=JobStatus.PENDING,
        total_count=3,
    )
    cert1 = Certificate(job=job, recipient_name="Student 1", recipient_email="s1@example.com", status=CertificateStatus.PENDING)
    cert2 = Certificate(job=job, recipient_name="Student 2", recipient_email="s2@example.com", status=CertificateStatus.PENDING)
    cert3 = Certificate(job=job, recipient_name="Student 3", recipient_email="s3@example.com", status=CertificateStatus.PENDING)

    db_session.add(job)
    db_session.add_all([cert1, cert2, cert3])
    db_session.commit()
    db_session.refresh(job)

    # Mock PDF generator so cert2 fails while cert1 and cert3 succeed
    from app.generators import pdf_generator as real_gen
    original_generate = real_gen.generate_certificate_pdf

    def mock_generate(data, base_storage_dir=None):
        if data.certificate_id == cert2.id:
            raise PDFGenerationError("Simulated PDF generation failure for cert 2")
        return original_generate(data, base_storage_dir=base_storage_dir)

    monkeypatch.setattr("app.workers.certificate_worker.generate_certificate_pdf", mock_generate)

    process_job(job.id, db=db_session)
    db_session.refresh(job)

    assert job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert job.success_count == 2
    assert job.failure_count == 1

    c1 = db_session.get(Certificate, cert1.id)
    c2 = db_session.get(Certificate, cert2.id)
    c3 = db_session.get(Certificate, cert3.id)

    assert c1.status == CertificateStatus.SUCCESS
    assert c1.file_path is not None

    assert c2.status == CertificateStatus.FAILED
    assert c2.error_message == "Certificate PDF generation failed"
    assert c2.file_path is None

    assert c3.status == CertificateStatus.SUCCESS
    assert c3.file_path is not None


def test_process_job_all_failed(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify job status is COMPLETED_WITH_ERRORS when all certificates fail."""
    job = GenerationJob(
        event_name="All Fail Event",
        event_date=date(2026, 10, 7),
        status=JobStatus.PENDING,
        total_count=2,
    )
    cert1 = Certificate(job=job, recipient_name="Fail 1", recipient_email="f1@example.com", status=CertificateStatus.PENDING)
    cert2 = Certificate(job=job, recipient_name="Fail 2", recipient_email="f2@example.com", status=CertificateStatus.PENDING)

    db_session.add(job)
    db_session.add_all([cert1, cert2])
    db_session.commit()

    def mock_fail_all(data, base_storage_dir=None):
        raise PDFGenerationError("All PDF generation failed")

    monkeypatch.setattr("app.workers.certificate_worker.generate_certificate_pdf", mock_fail_all)

    process_job(job.id, db=db_session)
    db_session.refresh(job)

    assert job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert job.success_count == 0
    assert job.failure_count == 2


def test_api_schedules_and_processes_job(client: TestClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify API POST /api/v1/jobs returns 202 and worker processes job."""
    monkeypatch.setattr("app.generators.pdf_generator.settings.STORAGE_PATH", str(tmp_path))

    payload = {
        "event_name": "API Background Integration Test",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    data = response.json()
    job_id = uuid.UUID(data["job_id"])

    # Process job using test session
    process_job(job_id, db=db_session)

    job = db_session.scalar(select(GenerationJob).where(GenerationJob.id == job_id))
    assert job is not None
    assert job.status == JobStatus.COMPLETED
    assert job.success_count == 1
    assert job.failure_count == 0
