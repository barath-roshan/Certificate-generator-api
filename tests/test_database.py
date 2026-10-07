from datetime import date
import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.models.certificate import Certificate
from app.models.enums import CertificateStatus, JobStatus
from app.models.job import GenerationJob


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Fixture providing an isolated in-memory database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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


def test_models_importable() -> None:
    """Verify that models and enums can be imported without error."""
    assert GenerationJob.__tablename__ == "generation_jobs"
    assert Certificate.__tablename__ == "certificates"
    assert JobStatus.PENDING == "PENDING"
    assert CertificateStatus.SUCCESS == "SUCCESS"


def test_persist_generation_job(db_session: Session) -> None:
    """Verify that a GenerationJob can be persisted and retrieved."""
    job = GenerationJob(
        event_name="Annual Tech Summit 2026",
        event_date=date(2026, 10, 15),
        status=JobStatus.PENDING,
        total_count=100,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert isinstance(job.id, uuid.UUID)
    assert job.event_name == "Annual Tech Summit 2026"
    assert job.status == JobStatus.PENDING
    assert job.total_count == 100
    assert job.success_count == 0
    assert job.failure_count == 0
    assert job.created_at is not None


def test_persist_certificate_and_relationship(db_session: Session) -> None:
    """Verify Certificate persistence and GenerationJob 1-N relationship."""
    job = GenerationJob(
        event_name="Python Workshop",
        event_date=date(2026, 11, 1),
        status=JobStatus.PROCESSING,
        total_count=2,
    )
    cert1 = Certificate(
        job=job,
        recipient_name="Alice Smith",
        recipient_email="alice@example.com",
        status=CertificateStatus.PENDING,
    )
    cert2 = Certificate(
        job=job,
        recipient_name="Bob Jones",
        recipient_email="bob@example.com",
        status=CertificateStatus.SUCCESS,
        file_path="/certificates/bob_jones.pdf",
    )

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # Verify job -> certificates relationship
    assert len(job.certificates) == 2
    recipient_emails = {c.recipient_email for c in job.certificates}
    assert recipient_emails == {"alice@example.com", "bob@example.com"}

    # Verify certificate -> job foreign-key relationship
    saved_cert = db_session.scalar(
        select(Certificate).where(Certificate.recipient_email == "alice@example.com")
    )
    assert saved_cert is not None
    assert saved_cert.job_id == job.id
    assert saved_cert.job.event_name == "Python Workshop"


def test_get_db_dependency() -> None:
    """Verify get_db generator yields a session and closes it."""
    db_gen = get_db()
    session = next(db_gen)
    assert isinstance(session, Session)
    try:
        next(db_gen)
    except StopIteration:
        pass
