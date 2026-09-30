"""complete application schema for beauty, customer, consent, and subscription workflows

Revision ID: 0002_application_tables
Revises: 0001_initial
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_application_tables"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(bind, *values: str, name: str):
    enum = postgresql.ENUM(*values, name=name, create_type=False)
    enum.create(bind, checkfirst=True)
    return enum


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    beauty_job_status = _enum(bind, "QUEUED", "PROCESSING", "COMPLETED", "FAILED", name="beauty_job_status")

    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("consent_required", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_customers_salon_id", "customers", ["salon_id"])

    op.create_table(
        "beauty_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Uuid(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", beauty_job_status, nullable=False),
        sa.Column("selected_makeup", sa.String(500), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=False),
        sa.Column("shade", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("before_image_url", sa.String(1000), nullable=True),
        sa.Column("after_image_url", sa.String(1000), nullable=True),
        sa.Column("input_file_path", sa.String(2000), nullable=True),
        sa.Column("output_file_path", sa.String(2000), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_beauty_jobs_salon_id", "beauty_jobs", ["salon_id"])
    op.create_index("ix_beauty_jobs_customer_id", "beauty_jobs", ["customer_id"])

    op.create_table(
        "consultations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Uuid(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("beauty_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("beauty_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("selected_makeup", sa.String(500), nullable=False),
        sa.Column("shade", sa.String(100), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("before_image_url", sa.String(1000), nullable=True),
        sa.Column("after_image_url", sa.String(1000), nullable=True),
        sa.Column("consent_granted", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_consultations_salon_id", "consultations", ["salon_id"])
    op.create_index("ix_consultations_customer_id", "consultations", ["customer_id"])
    op.create_index("ix_consultations_beauty_job_id", "consultations", ["beauty_job_id"])

    op.create_table(
        "beauty_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("beauty_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("beauty_jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("before_image_url", sa.String(1000), nullable=False),
        sa.Column("after_image_url", sa.String(1000), nullable=False),
        sa.Column("identity_similarity", sa.Float(), nullable=False),
        sa.Column("skin_tone", sa.String(50), nullable=False),
        sa.Column("undertone", sa.String(50), nullable=False),
        sa.Column("foundation_match", sa.String(100), nullable=False),
        sa.Column("watermark_applied", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_beauty_results_salon_id", "beauty_results", ["salon_id"])
    op.create_index("ix_beauty_results_beauty_job_id", "beauty_results", ["beauty_job_id"])

    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Uuid(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("consent_text", sa.String(500), nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_consents_salon_id", "consents", ["salon_id"])
    op.create_index("ix_consents_customer_id", "consents", ["customer_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_subscriptions_salon_id", "subscriptions", ["salon_id"])

    op.create_table(
        "watermarks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("salon_id", sa.Uuid(as_uuid=True), sa.ForeignKey("salons.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("logo_url", sa.String(1000), nullable=True),
        sa.Column("salon_name", sa.Boolean(), nullable=False),
        sa.Column("phone", sa.Boolean(), nullable=False),
        sa.Column("instagram", sa.Boolean(), nullable=False),
        sa.Column("tiktok", sa.Boolean(), nullable=False),
        sa.Column("position", sa.String(20), nullable=False),
        sa.Column("opacity", sa.Float(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_watermarks_salon_id", "watermarks", ["salon_id"])


def downgrade() -> None:
    for table in ("watermarks", "subscriptions", "consents", "beauty_results", "consultations", "beauty_jobs", "customers"):
        op.drop_table(table)
    bind = op.get_bind()
    postgresql.ENUM(name="beauty_job_status").drop(bind, checkfirst=True)
