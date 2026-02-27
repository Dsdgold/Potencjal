"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Plans
    op.create_table('plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('limits_json', postgresql.JSON(), server_default='{}'),
        sa.Column('features_json', postgresql.JSON(), server_default='{}'),
        sa.Column('price_monthly', sa.Integer(), server_default='0'),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Organizations
    op.create_table('organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=True),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Users
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), server_default=''),
        sa.Column('role', sa.String(20), server_default='member'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Subscriptions
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('provider', sa.String(50), server_default='stripe'),
        sa.Column('provider_customer_id', sa.String(255), nullable=True),
        sa.Column('provider_subscription_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(30), server_default='trialing'),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Usage events
    op.create_table('usage_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('meta_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Companies
    op.create_table('companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('nip', sa.String(10), unique=True, nullable=False),
        sa.Column('name', sa.String(500), nullable=True),
        sa.Column('regon', sa.String(14), nullable=True),
        sa.Column('krs', sa.String(10), nullable=True),
        sa.Column('country', sa.String(2), server_default='PL'),
        sa.Column('legal_form', sa.String(100), nullable=True),
        sa.Column('pkd_main', sa.String(10), nullable=True),
        sa.Column('pkd_codes', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_companies_nip', 'companies', ['nip'])

    # Company snapshots
    op.create_table('company_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ttl_expires_at', sa.DateTime(), nullable=False),
        sa.Column('sources_json', postgresql.JSON(), server_default='{}'),
        sa.Column('raw_json', postgresql.JSON(), server_default='{}'),
        sa.Column('normalized_json', postgresql.JSON(), server_default='{}'),
        sa.Column('quality_json', postgresql.JSON(), server_default='{}'),
        sa.Column('lookup_count', sa.Integer(), server_default='1'),
    )

    # Company facet docs
    op.create_table('company_facet_docs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('facet', sa.String(50), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Score results
    op.create_table('score_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('company_snapshots.id'), nullable=False),
        sa.Column('score_version', sa.String(20), server_default='v1'),
        sa.Column('score_0_100', sa.Integer(), nullable=False),
        sa.Column('risk_band', sa.String(5), nullable=False),
        sa.Column('credit_limit_suggested', sa.Integer(), server_default='0'),
        sa.Column('credit_limit_min', sa.Integer(), server_default='0'),
        sa.Column('credit_limit_max', sa.Integer(), server_default='0'),
        sa.Column('payment_terms_days', sa.Integer(), server_default='0'),
        sa.Column('discount_pct', sa.Float(), server_default='0'),
        sa.Column('components_json', postgresql.JSON(), server_default='[]'),
        sa.Column('red_flags', postgresql.JSON(), server_default='[]'),
        sa.Column('green_flags', postgresql.JSON(), server_default='[]'),
        sa.Column('explanation_json', postgresql.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Material recommendations
    op.create_table('material_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('company_snapshots.id'), nullable=False),
        sa.Column('categories_json', postgresql.JSON(), server_default='[]'),
        sa.Column('explanation_json', postgresql.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Notes
    op.create_table('notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('tags_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Tasks
    op.create_table('tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('assigned_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), server_default='open'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Watchlists
    op.create_table('watchlists',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Alerts
    op.create_table('alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('payload_json', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(), nullable=True),
    )

    # Admin overrides
    op.create_table('admin_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('field_path', sa.String(255), nullable=False),
        sa.Column('value_json', postgresql.JSON(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Audit logs
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_type', sa.String(100), nullable=False),
        sa.Column('target_id', sa.String(255), nullable=False),
        sa.Column('diff_json', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('purpose', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Provider credentials
    op.create_table('provider_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('encrypted_credentials', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    tables = [
        'provider_credentials', 'audit_logs', 'admin_overrides',
        'alerts', 'watchlists', 'tasks', 'notes',
        'material_recommendations', 'score_results',
        'company_facet_docs', 'company_snapshots', 'companies',
        'usage_events', 'subscriptions', 'users', 'organizations', 'plans',
    ]
    for t in tables:
        op.drop_table(t)
