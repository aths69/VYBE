from fastapi import APIRouter, HTTPException, Query

from app.calculations.carbon import compute_carbon
from app.calculations.cost import compute_cost
from app.calculations.energy import compute_energy
from app.calculations.water import compute_water
from app.calculations.yield_metrics import compute_yield
from app.config import settings
from app.db import repository
from app.schemas import SessionCalculations
from app.telemetry.manager import SessionNotFoundError, session_manager

router = APIRouter(prefix="/api/sessions", tags=["calculations"])


@router.get("/{session_id}/calculations", response_model=SessionCalculations)
def session_calculations(
    session_id: str,
    rate_per_kwh: float | None = Query(default=None, gt=0),
    currency: str | None = Query(default=None),
    carbon_intensity_kg_per_kwh: float | None = Query(default=None, ge=0),
    water_wue_l_per_kwh: float | None = Query(default=None, ge=0),
    water_enabled: bool | None = Query(default=None),
) -> SessionCalculations:
    """Energy/cost/carbon/water for a session's stored telemetry.

    Every assumption (rate, currency, carbon intensity, WUE) can be overridden
    per-request; anything not supplied falls back to the configured default
    (Section 20) rather than a value baked into the code.
    """
    try:
        samples = session_manager.get_telemetry(session_id)
    except SessionNotFoundError:
        db_samples = repository.get_telemetry(session_id)
        if db_samples is None:
            raise HTTPException(
                status_code=404, detail=f"No session found with id '{session_id}'."
            )
        samples = db_samples

    energy = compute_energy(samples)

    cost = compute_cost(
        energy.total_energy_kwh,
        rate_per_kwh if rate_per_kwh is not None else settings.electricity_rate,
        currency if currency is not None else settings.currency,
    )

    carbon = compute_carbon(
        energy.total_energy_kwh,
        carbon_intensity_kg_per_kwh
        if carbon_intensity_kg_per_kwh is not None
        else settings.carbon_intensity_kg_per_kwh,
    )

    water = compute_water(
        energy.total_energy_kwh,
        water_wue_l_per_kwh
        if water_wue_l_per_kwh is not None
        else settings.water_wue_l_per_kwh,
        water_enabled if water_enabled is not None else settings.water_estimation_enabled,
    )

    output_count, output_unit = repository.get_output_info(session_id)
    yield_metrics = compute_yield(energy, cost, output_count, output_unit)

    return SessionCalculations(
        session_id=session_id,
        energy=energy,
        cost=cost,
        carbon=carbon,
        water=water,
        yield_metrics=yield_metrics,
    )
