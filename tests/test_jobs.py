from collections.abc import Generator
import uuid

from fastapi import status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob


from sqlalchemy.pool import StaticPool


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
    """Fixture providing a TestClient with dependency override for get_db and worker session."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.workers.certificate_worker.get_worker_session", lambda: db_session)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_job_success(client: TestClient, db_session: Session) -> None:
    """Verify valid job creation returns 202 Accepted and creates DB records."""
    payload = {
        "event_name": "Python Workshop 2026",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Barath Roshan", "email": "barath@example.com"},
            {"name": "Arun Kumar", "email": "arun@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED

    data = response.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["total_count"] == 2

    job_id = uuid.UUID(data["job_id"])

    # Verify GenerationJob record in DB (processed by background worker)
    job = db_session.scalar(select(GenerationJob).where(GenerationJob.id == job_id))
    assert job is not None
    assert job.event_name == "Python Workshop 2026"
    assert str(job.event_date) == "2026-10-07"
    assert job.status == JobStatus.COMPLETED
    assert job.total_count == 2
    assert job.success_count == 2
    assert job.failure_count == 0

    # Verify Certificate records in DB
    certificates = db_session.scalars(
        select(Certificate).where(Certificate.job_id == job_id)
    ).all()
    assert len(certificates) == 2
    for cert in certificates:
        assert cert.status == CertificateStatus.SUCCESS
        assert cert.file_path is not None
        assert cert.error_message is None

    recipient_emails = {c.recipient_email for c in certificates}
    assert recipient_emails == {"barath@example.com", "arun@example.com"}


def test_create_job_rejects_missing_event_name(client: TestClient) -> None:
    """Verify request with missing event_name is rejected with HTTP 422."""
    payload = {
        "event_date": "2026-10-07",
        "recipients": [{"name": "Barath", "email": "barath@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_rejects_blank_event_name(client: TestClient) -> None:
    """Verify request with blank event_name is rejected with HTTP 422."""
    payload = {
        "event_name": "   ",
        "event_date": "2026-10-07",
        "recipients": [{"name": "Barath", "email": "barath@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_rejects_blank_recipient_name(client: TestClient) -> None:
    """Verify request with blank recipient name is rejected with HTTP 422."""
    payload = {
        "event_name": "Python Workshop",
        "event_date": "2026-10-07",
        "recipients": [{"name": "", "email": "barath@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_rejects_invalid_email(client: TestClient) -> None:
    """Verify request with invalid email format is rejected with HTTP 422."""
    payload = {
        "event_name": "Python Workshop",
        "event_date": "2026-10-07",
        "recipients": [{"name": "Barath Roshan", "email": "not-an-email"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_rejects_empty_recipients(client: TestClient) -> None:
    """Verify request with empty recipient list is rejected with HTTP 422."""
    payload = {
        "event_name": "Python Workshop",
        "event_date": "2026-10-07",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_rejects_exceeding_max_recipients(client: TestClient) -> None:
    """Verify request exceeding MAX_RECIPIENTS limit is rejected with HTTP 422."""
    recipients = [
        {"name": f"User {i}", "email": f"user{i}@example.com"}
        for i in range(settings.MAX_RECIPIENTS + 1)
    ]
    payload = {
        "event_name": "Large Event",
        "event_date": "2026-10-07",
        "recipients": recipients,
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_job_allows_duplicate_emails(client: TestClient, db_session: Session) -> None:
    """Verify identical emails appearing multiple times are permitted as per Phase 3 spec."""
    payload = {
        "event_name": "Duplicate Test Event",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Barath Roshan", "email": "barath@example.com"},
            {"name": "Barath Roshan Copy", "email": "barath@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["total_count"] == 2


def test_create_job_server_error_on_database_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that a database error causes HTTP 500 without exposing stack trace."""
    def mock_create_job(*args, **kwargs):
        raise RuntimeError("Simulated DB Connection Failure")

    monkeypatch.setattr("app.api.routes.jobs.create_generation_job", mock_create_job)

    payload = {
        "event_name": "Error Test Event",
        "event_date": "2026-10-07",
        "recipients": [{"name": "Barath Roshan", "email": "barath@example.com"}],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "An error occurred while creating the generation job."
    }

