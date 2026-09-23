"""Section 25: cost calculation, carbon calculation, water estimation."""

import pytest

from app.calculations.carbon import compute_carbon
from app.calculations.cost import compute_cost
from app.calculations.water import compute_water
from app.calculations.yield_metrics import compute_yield
from app.schemas import CostResult, EnergyResult


# ---------- cost (Section 7) ----------


def test_cost_multiplies_energy_by_rate():
    result = compute_cost(energy_kwh=2.0, rate_per_kwh=10.0, currency="INR")
    assert result.total_cost == 20.0
    assert result.currency == "INR"
    assert result.rate_per_kwh == 10.0
    assert result.label == "CALCULATED"


def test_cost_zero_energy_is_zero_cost():
    result = compute_cost(energy_kwh=0.0, rate_per_kwh=10.0, currency="INR")
    assert result.total_cost == 0.0


def test_cost_respects_configurable_currency_and_rate():
    result = compute_cost(energy_kwh=1.5, rate_per_kwh=0.25, currency="USD")
    assert result.total_cost == pytest.approx(0.375)
    assert result.currency == "USD"


# ---------- carbon (Section 8) ----------


def test_carbon_multiplies_energy_by_intensity():
    result = compute_carbon(energy_kwh=2.0, carbon_intensity_kg_per_kwh=0.7)
    assert result.estimated_kg_co2e == pytest.approx(1.4)
    assert result.carbon_intensity_kg_per_kwh == 0.7
    assert result.label == "ESTIMATED"
    assert result.note  # must always explain the assumption, never silent


def test_carbon_zero_energy_is_zero():
    result = compute_carbon(energy_kwh=0.0, carbon_intensity_kg_per_kwh=0.7)
    assert result.estimated_kg_co2e == 0.0


# ---------- water (Section 9) ----------


def test_water_enabled_multiplies_energy_by_wue():
    result = compute_water(energy_kwh=2.0, wue_l_per_kwh=1.8, enabled=True)
    assert result.enabled is True
    assert result.estimated_liters == pytest.approx(3.6)
    assert result.label == "ESTIMATED"


def test_water_disabled_returns_none_not_zero():
    result = compute_water(energy_kwh=2.0, wue_l_per_kwh=1.8, enabled=False)
    assert result.enabled is False
    assert result.estimated_liters is None
    assert "disabled" in result.note.lower()


def test_water_missing_wue_treated_as_disabled_even_if_flag_true():
    result = compute_water(energy_kwh=2.0, wue_l_per_kwh=None, enabled=True)
    assert result.enabled is False
    assert result.estimated_liters is None


# ---------- yield / cost-per-output (Section 11) ----------


def _energy(total_wh: float) -> EnergyResult:
    return EnergyResult(
        total_energy_wh=total_wh,
        total_energy_kwh=total_wh / 1000,
        sample_count=2,
        runtime_seconds=10,
        intervals_used=1,
        intervals_skipped=0,
        coverage_seconds=10,
    )


def _cost(total: float) -> CostResult:
    return CostResult(currency="INR", rate_per_kwh=10.0, total_cost=total)


def test_yield_none_when_no_output_reported():
    assert compute_yield(_energy(100), _cost(1.0), None, None) is None
    assert compute_yield(_energy(100), _cost(1.0), 0, "images") is None


def test_yield_divides_energy_and_cost_by_output_count():
    result = compute_yield(_energy(100), _cost(1.0), 50, "images")
    assert result is not None
    assert result.useful_output_count == 50
    assert result.useful_output_unit == "images"
    assert result.energy_per_unit_wh == pytest.approx(2.0)
    assert result.cost_per_unit == pytest.approx(0.02)
    assert result.energy_per_1000_units_kwh == pytest.approx((100 / 1000 / 50) * 1000)
    assert result.cost_per_1000_units == pytest.approx((1.0 / 50) * 1000)


def test_yield_defaults_unit_label_when_missing():
    result = compute_yield(_energy(100), _cost(1.0), 10, None)
    assert result is not None
    assert result.useful_output_unit == "units"
