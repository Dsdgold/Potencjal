"""Tests for the scoring engine — verifying weights, tiers, and edge cases."""

from src.qualifier.scoring import (
    DEFAULT_WEIGHTS,
    ScoringInput,
    ScoringOutput,
    calculate_score,
    estimate_annual,
    revenue_band_of,
    categories_for_pkd,
)


class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_seven_factors_present(self):
        expected = {"employees", "revenue_band", "years_active", "vat_status", "pkd_fit", "basket_signal", "locality"}
        assert set(DEFAULT_WEIGHTS.keys()) == expected


class TestRevenueBand:
    def test_micro(self):
        assert revenue_band_of(500_000) == "micro"

    def test_small(self):
        assert revenue_band_of(5_000_000) == "small"

    def test_medium(self):
        assert revenue_band_of(25_000_000) == "medium"

    def test_large(self):
        assert revenue_band_of(100_000_000) == "large"

    def test_zero(self):
        assert revenue_band_of(0) == "micro"


class TestTierThresholds:
    def test_tier_s(self):
        """High-potential company should score S tier (85+)."""
        inp = ScoringInput(
            employees=300,
            revenue_pln=60_000_000,
            years_active=15,
            vat_status="Czynny VAT",
            pkd="41",
            basket_pln=10000,
            locality_hit=True,
        )
        out = calculate_score(inp)
        assert out.tier == "S"
        assert out.score >= 85

    def test_tier_a(self):
        """Medium-high company should score A tier (70-84)."""
        inp = ScoringInput(
            employees=100,
            revenue_pln=15_000_000,
            years_active=8,
            vat_status="Czynny VAT",
            pkd="43",
            basket_pln=4000,
            locality_hit=True,
        )
        out = calculate_score(inp)
        assert out.tier in ("S", "A")
        assert out.score >= 70

    def test_tier_c(self):
        """Minimal data should score C tier (<55)."""
        inp = ScoringInput(
            employees=3,
            revenue_pln=100_000,
            years_active=0.5,
            vat_status="Niepewny",
            pkd="",
            basket_pln=0,
            locality_hit=False,
        )
        out = calculate_score(inp)
        assert out.tier == "C"
        assert out.score < 55


class TestAnnualPotential:
    def test_s_tier(self):
        assert estimate_annual("S") == 540_000

    def test_a_tier(self):
        assert estimate_annual("A") == 216_000

    def test_b_tier(self):
        assert estimate_annual("B") == 90_000

    def test_c_tier(self):
        assert estimate_annual("C") == 36_000


class TestScoringOutput:
    def test_output_fields(self):
        inp = ScoringInput(employees=50, revenue_pln=5_000_000, pkd="41")
        out = calculate_score(inp)
        assert isinstance(out, ScoringOutput)
        assert 0 <= out.score <= 100
        assert out.tier in ("S", "A", "B", "C")
        assert out.annual_potential > 0
        assert out.revenue_band in ("micro", "small", "medium", "large")
        assert isinstance(out.categories, list)
        assert isinstance(out.recommended_actions, list)

    def test_zero_input(self):
        out = calculate_score(ScoringInput())
        assert out.score >= 0
        assert out.tier == "C"

    def test_categories_for_known_pkd(self):
        cats = categories_for_pkd("41")
        assert len(cats) > 0
        assert "materiały konstrukcyjne" in cats

    def test_categories_fallback(self):
        cats = categories_for_pkd("99.99")
        assert len(cats) > 0
        assert "materiały uniwersalne" in cats

    def test_basket_signal_effect(self):
        """Higher basket should increase score."""
        inp_low = ScoringInput(employees=50, revenue_pln=5_000_000, basket_pln=0)
        inp_high = ScoringInput(employees=50, revenue_pln=5_000_000, basket_pln=10000)
        out_low = calculate_score(inp_low)
        out_high = calculate_score(inp_high)
        assert out_high.score >= out_low.score

    def test_locality_effect(self):
        """Major city hit should increase score."""
        inp_no = ScoringInput(employees=50, revenue_pln=5_000_000, locality_hit=False)
        inp_yes = ScoringInput(employees=50, revenue_pln=5_000_000, locality_hit=True)
        out_no = calculate_score(inp_no)
        out_yes = calculate_score(inp_yes)
        assert out_yes.score >= out_no.score
