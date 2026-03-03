"""Tests for SQLAlchemy models — table names, required fields."""

from src.tenants.models import Tenant
from src.users.models import User
from src.regions.models import Region
from src.leads.models import Lead, LeadAction, ScoringHistory
from src.notifications.models import Notification, EmailLog, ScrapeJob, StripeEvent


class TestTableNames:
    def test_tenant_table(self):
        assert Tenant.__tablename__ == "tenants"

    def test_user_table(self):
        assert User.__tablename__ == "users"

    def test_region_table(self):
        assert Region.__tablename__ == "regions"

    def test_lead_table(self):
        assert Lead.__tablename__ == "leads"

    def test_lead_action_table(self):
        assert LeadAction.__tablename__ == "lead_actions"

    def test_scoring_history_table(self):
        assert ScoringHistory.__tablename__ == "scoring_history"

    def test_notification_table(self):
        assert Notification.__tablename__ == "notifications"

    def test_email_log_table(self):
        assert EmailLog.__tablename__ == "email_logs"

    def test_scrape_job_table(self):
        assert ScrapeJob.__tablename__ == "scrape_jobs"

    def test_stripe_event_table(self):
        assert StripeEvent.__tablename__ == "stripe_events"


class TestModelColumns:
    def test_tenant_has_plan(self):
        columns = {c.name for c in Tenant.__table__.columns}
        assert "plan" in columns
        assert "slug" in columns
        assert "is_active" in columns

    def test_user_has_role(self):
        columns = {c.name for c in User.__table__.columns}
        assert "role" in columns
        assert "tenant_id" in columns
        assert "email" in columns
        assert "region_id" in columns

    def test_lead_has_source(self):
        columns = {c.name for c in Lead.__table__.columns}
        assert "source" in columns
        assert "source_id" in columns
        assert "tenant_id" in columns
        assert "region_id" in columns
        assert "score" in columns
        assert "tier" in columns
        assert "status" in columns
        assert "cpv_codes" in columns
        assert "category" in columns

    def test_lead_has_contact_fields(self):
        columns = {c.name for c in Lead.__table__.columns}
        assert "contact_company" in columns
        assert "contact_person" in columns
        assert "contact_phone" in columns
        assert "contact_email" in columns

    def test_scrape_job_columns(self):
        columns = {c.name for c in ScrapeJob.__table__.columns}
        assert "source" in columns
        assert "status" in columns
        assert "items_found" in columns
        assert "items_qualified" in columns
