"""Carbon estimation (Section 8). ESTIMATED - never presented as measured."""

from app.schemas import CarbonResult

CARBON_NOTE = (
    "Estimated from energy consumed and a configurable grid carbon-intensity "
    "assumption. Real grid intensity varies by time of day, season, and energy "
    "mix, so this is a directional estimate, not a measurement."
)


def compute_carbon(energy_kwh: float, carbon_intensity_kg_per_kwh: float) -> CarbonResult:
    return CarbonResult(
        carbon_intensity_kg_per_kwh=carbon_intensity_kg_per_kwh,
        estimated_kg_co2e=energy_kwh * carbon_intensity_kg_per_kwh,
        note=CARBON_NOTE,
    )
