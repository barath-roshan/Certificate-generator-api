from datetime import date
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.config import settings
from app.models.enums import JobStatus


class RecipientCreate(BaseModel):
    """Schema for creating a certificate recipient."""

    name: str
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Name must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("Recipient name cannot be blank")
        return stripped


class GenerationJobCreate(BaseModel):
    """Schema for submitting a bulk certificate generation job."""

    event_name: str
    event_date: date
    recipients: list[RecipientCreate]

    @field_validator("event_name", mode="before")
    @classmethod
    def validate_event_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Event name must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("Event name cannot be blank")
        return stripped

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, recipients: list[RecipientCreate]) -> list[RecipientCreate]:
        if not recipients:
            raise ValueError("At least one recipient is required")
        if len(recipients) > settings.MAX_RECIPIENTS:
            raise ValueError(
                f"Number of recipients exceeds maximum limit of {settings.MAX_RECIPIENTS}"
            )
        return recipients


class GenerationJobResponse(BaseModel):
    """Response schema for a created bulk certificate generation job."""

    job_id: uuid.UUID
    status: JobStatus
    total_count: int

    model_config = ConfigDict(from_attributes=True)
