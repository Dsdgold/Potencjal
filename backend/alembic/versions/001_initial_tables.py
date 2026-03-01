"""Initial tables – leads and scoring_history

Revision ID: 001
Revises:
Create Date: 2026-03-01
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
    op.create_table(
        "leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("nip", sa.String(10), index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("employees", sa.Integer),
        sa.Column("revenue_pln", sa.Float),
        sa.Column("revenue_band", sa.String(20)),
        sa.Column("pkd", sa.String(10)),
        sa.Column("pkd_desc", sa.String(300)),
        sa.Column("years_active", sa.Float),
        sa.Column("vat_status", sa.String(30)),
        sa.Column("website", sa.String(300)),
        sa.Column("basket_pln", sa.Float, server_default="0"),
        sa.Column("score", sa.Integer),
        sa.Column("tier", sa.String(1)),
        sa.Column("annual_potential", sa.Integer),
        sa.Column("osint_raw", JSONB),
        sa.Column("sources", JSONB, server_default="[]"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

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


def downgrade() -> None:
    op.drop_table("scoring_history")
    op.drop_table("leads")
