"""Add users table and owner_id to leads

Revision ID: 002
Revises: 001
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("role", sa.String(20), server_default="user", nullable=False),
        sa.Column("package", sa.String(20), server_default="starter", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("leads_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True)),
    )

    op.add_column("leads", sa.Column("owner_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_leads_owner",
        "leads",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_leads_owner_id", "leads", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_owner_id", "leads")
    op.drop_constraint("fk_leads_owner", "leads", type_="foreignkey")
    op.drop_column("leads", "owner_id")
    op.drop_table("users")
