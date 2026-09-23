"""Session comparison (Section 13) - e.g. Model A vs Model B, batch 16 vs 32."""

from fastapi import APIRouter, HTTPException, Query

from app.db import repository
from app.schemas import SessionComparisonResponse

router = APIRouter(prefix="/api/sessions", tags=["comparison"])

MIN_SESSIONS = 2
MAX_SESSIONS = 8


@router.get("/compare", response_model=SessionComparisonResponse)
def compare_sessions(
    session_ids: list[str] = Query(default=[]),
) -> SessionComparisonResponse:
    if len(session_ids) < MIN_SESSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Provide at least {MIN_SESSIONS} session_ids to compare.",
        )
    if len(session_ids) > MAX_SESSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot compare more than {MAX_SESSIONS} sessions at once.",
        )

    items = []
    missing = []
    for session_id in session_ids:
        item = repository.get_comparison_item(session_id)
        if item is None:
            missing.append(session_id)
        else:
            items.append(item)

    if missing:
        raise HTTPException(
            status_code=404,
            detail=(
                "No completed session data found for: "
                f"{', '.join(missing)}. A session must be stopped before it "
                "can be compared."
            ),
        )

    warnings = []
    simulated_count = sum(1 for item in items if item.is_simulated)
    if 0 < simulated_count < len(items):
        # Section 24: never let simulated and real numbers sit side by side
        # without an explicit call-out.
        warnings.append(
            "This comparison mixes simulated (demo mode) and real sessions. "
            "Simulated telemetry is synthetic and does not reflect real "
            "hardware behavior - it is not directly comparable to a real "
            "measurement."
        )

    return SessionComparisonResponse(sessions=items, warnings=warnings)
