"""Electricity cost (Section 7). CALCULATED from energy x a configurable rate."""

from app.schemas import CostResult


def compute_cost(energy_kwh: float, rate_per_kwh: float, currency: str) -> CostResult:
    return CostResult(
        currency=currency,
        rate_per_kwh=rate_per_kwh,
        total_cost=energy_kwh * rate_per_kwh,
    )
