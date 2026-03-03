"""Tests for configuration — enums, plan limits."""

from src.config import (
    PLAN_LIMITS,
    LeadActionType,
    LeadSource,
    LeadStatus,
    MaterialCategory,
    PlanType,
    UserRole,
)


class TestEnums:
    def test_user_roles(self):
        assert UserRole.PLATFORM_ADMIN.value == "platform_admin"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.SALESPERSON.value == "salesperson"
        assert UserRole.VIEWER.value == "viewer"
        assert len(UserRole) == 4

    def test_plan_types(self):
        assert PlanType.TRIAL.value == "trial"
        assert PlanType.STARTER.value == "starter"
        assert PlanType.GROWTH.value == "growth"
        assert PlanType.ENTERPRISE.value == "enterprise"
        assert len(PlanType) == 4

    def test_lead_statuses(self):
        expected = {"new", "contacted", "offer_sent", "won", "lost", "ignored"}
        actual = {s.value for s in LeadStatus}
        assert actual == expected

    def test_lead_sources(self):
        expected = {"bzp", "ted", "gunb", "krs", "scraping", "manual", "osint"}
        actual = {s.value for s in LeadSource}
        assert actual == expected

    def test_material_categories(self):
        assert len(MaterialCategory) >= 8  # at least 8 categories

    def test_lead_action_types(self):
        assert len(LeadActionType) >= 4


class TestPlanLimits:
    def test_all_plans_defined(self):
        for plan in PlanType:
            assert plan in PLAN_LIMITS, f"Missing limits for {plan}"

    def test_trial_limits(self):
        limits = PLAN_LIMITS[PlanType.TRIAL]
        assert limits["max_users"] == 2
        assert limits["max_regions"] == 1
        assert limits["price"] == 0
        assert "duration_days" in limits

    def test_enterprise_unlimited(self):
        limits = PLAN_LIMITS[PlanType.ENTERPRISE]
        assert limits["max_users"] == -1  # unlimited
        assert limits["max_regions"] == -1

    def test_growth_sources(self):
        limits = PLAN_LIMITS[PlanType.GROWTH]
        assert "bzp" in limits["sources"]
        assert "gunb" in limits["sources"]
        assert limits["email_digest"] is True

    def test_prices_ascending(self):
        trial = PLAN_LIMITS[PlanType.TRIAL]["price"]
        starter = PLAN_LIMITS[PlanType.STARTER]["price"]
        growth = PLAN_LIMITS[PlanType.GROWTH]["price"]
        enterprise = PLAN_LIMITS[PlanType.ENTERPRISE]["price"]
        assert trial <= starter <= growth <= enterprise
