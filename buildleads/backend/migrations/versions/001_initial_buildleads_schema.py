"""Initial BuildLeads schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-03-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === TENANTS ===
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, index=True, nullable=False),
        sa.Column("plan", sa.String(20), server_default="trial", nullable=False),
        sa.Column("plan_status", sa.String(20), server_default="active", nullable=False),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("stripe_subscription_id", sa.String(255)),
        sa.Column("max_users", sa.Integer, server_default="2", nullable=False),
        sa.Column("max_regions", sa.Integer, server_default="1", nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === REGIONS ===
    op.create_table(
        "regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("voivodeships", JSONB, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === USERS ===
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(150), nullable=False),
        sa.Column("last_name", sa.String(150), nullable=False),
        sa.Column("role", sa.String(20), server_default="salesperson", nullable=False),
        sa.Column("region_id", UUID(as_uuid=True), sa.ForeignKey("regions.id", ondelete="SET NULL"), index=True),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("email_verified", sa.Boolean, server_default="false", nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === LEADS ===
    op.create_table(
        "leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("region_id", UUID(as_uuid=True), sa.ForeignKey("regions.id", ondelete="SET NULL"), index=True),
        sa.Column("source", sa.String(20), server_default="manual", nullable=False),
        sa.Column("source_id", sa.String(255)),
        sa.Column("nip", sa.String(10), index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("voivodeship", sa.String(50)),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("employees", sa.Integer),
        sa.Column("revenue_pln", sa.Float),
        sa.Column("revenue_band", sa.String(20)),
        sa.Column("pkd", sa.String(10)),
        sa.Column("pkd_desc", sa.String(300)),
        sa.Column("years_active", sa.Float),
        sa.Column("vat_status", sa.String(30)),
        sa.Column("website", sa.String(300)),
        sa.Column("title", sa.String(500)),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(50)),
        sa.Column("subcategory", sa.String(100)),
        sa.Column("estimated_value", sa.Float),
        sa.Column("cpv_codes", JSONB, server_default="[]"),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("contact_company", sa.String(300)),
        sa.Column("contact_person", sa.String(200)),
        sa.Column("contact_phone", sa.String(50)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("basket_pln", sa.Float, server_default="0"),
        sa.Column("score", sa.Integer),
        sa.Column("tier", sa.String(1)),
        sa.Column("annual_potential", sa.Integer),
        sa.Column("ai_summary", sa.Text),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("qualified_at", sa.DateTime(timezone=True)),
        sa.Column("osint_raw", JSONB),
        sa.Column("sources", JSONB, server_default="[]"),
        sa.Column("raw_data", JSONB),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === LEAD ACTIONS ===
    op.create_table(
        "lead_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === SCORING HISTORY ===
    op.create_table(
        "scoring_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("tier", sa.String(1), nullable=False),
        sa.Column("annual_potential", sa.Integer, nullable=False),
        sa.Column("weights_snapshot", JSONB),
        sa.Column("scored_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === NOTIFICATIONS ===
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("read", sa.Boolean, server_default="false", nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === EMAIL LOGS ===
    op.create_table(
        "email_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), server_default="sent", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
    )

    # === SCRAPE JOBS ===
    op.create_table(
        "scrape_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("items_found", sa.Integer, server_default="0"),
        sa.Column("items_qualified", sa.Integer, server_default="0"),
        sa.Column("error_log", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # === STRIPE EVENTS ===
    op.create_table(
        "stripe_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("stripe_event_id", sa.String(255), unique=True, nullable=False),
        sa.Column("data", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_table("scrape_jobs")
    op.drop_table("email_logs")
    op.drop_table("notifications")
    op.drop_table("scoring_history")
    op.drop_table("lead_actions")
    op.drop_table("leads")
    op.drop_table("users")
    op.drop_table("regions")
    op.drop_table("tenants")
