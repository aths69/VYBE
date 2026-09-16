"""Cost/energy per useful output (Section 11) - the "Yield" in VYBE.

Raw GPU utilization alone doesn't indicate whether a workload is efficient;
this normalizes energy/cost against a user-reported useful-output count
(images processed, tokens generated, epochs completed, ...), CALCULATED
directly from already-CALCULATED energy/cost - never a separate measurement.
"""

from app.schemas import CostResult, EnergyResult, YieldMetrics


def compute_yield(
    energy: EnergyResult,
    cost: CostResult,
    useful_output_count: int | None,
    useful_output_unit: str | None,
) -> YieldMetrics | None:
    if not useful_output_count or useful_output_count <= 0:
        return None

    unit = useful_output_unit or "units"
    return YieldMetrics(
        useful_output_count=useful_output_count,
        useful_output_unit=unit,
        energy_per_unit_wh=energy.total_energy_wh / useful_output_count,
        cost_per_unit=cost.total_cost / useful_output_count,
        energy_per_1000_units_kwh=(energy.total_energy_kwh / useful_output_count) * 1000,
        cost_per_1000_units=(cost.total_cost / useful_output_count) * 1000,
    )
