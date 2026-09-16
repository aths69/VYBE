from fastapi import APIRouter, HTTPException

from app.analysis.efficiency import analyze_efficiency
from app.calculations.energy import compute_energy
from app.db import repository
from app.schemas import EfficiencyAnalysis, SessionHardwareSnapshot
from app.telemetry.manager import SessionNotFoundError, session_manager

router = APIRouter(prefix="/api/sessions", tags=["efficiency"])


@router.get("/{session_id}/efficiency", response_model=EfficiencyAnalysis)
def session_efficiency(session_id: str) -> EfficiencyAnalysis:
    """Heuristic efficiency findings (Section 10), recomputed fresh from raw
    telemetry every call - same "derive from raw truth" approach as
    /calculations, so live and historical sessions use one code path."""
    hardware: SessionHardwareSnapshot | None
    try:
        samples = session_manager.get_telemetry(session_id)
        hardware = session_manager.get_hardware_snapshot(session_id)
    except SessionNotFoundError:
        db_samples = repository.get_telemetry(session_id)
        if db_samples is None:
            raise HTTPException(
                status_code=404, detail=f"No session found with id '{session_id}'."
            )
        samples = db_samples
        hardware = repository.get_hardware(session_id)

    energy = compute_energy(samples)
    recommendations = analyze_efficiency(samples, hardware, energy)

    return EfficiencyAnalysis(
        session_id=session_id,
        sample_count=len(samples),
        recommendations=recommendations,
    )
