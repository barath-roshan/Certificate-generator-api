"""create initial tables generation_jobs and certificates

Revision ID: 001_initial_tables
Revises:
Create Date: 2026-10-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_status_enum = sa.Enum(
        "PENDING",
        "PROCESSING",
        "COMPLETED",
        "COMPLETED_WITH_ERRORS",
        "FAILED",
        name="job_status",
    )

    cert_status_enum = sa.Enum(
        "PENDING",
        "PROCESSING",
        "SUCCESS",
        "FAILED",
        name="certificate_status",
    )

    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_name", sa.String(length=255), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            job_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_generation_jobs_status"),
        "generation_jobs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            cert_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["generation_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_certificates_job_id"),
        "certificates",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_certificates_status"),
        "certificates",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_certificates_status"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_job_id"), table_name="certificates")
    op.drop_table("certificates")
    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_table("generation_jobs")
