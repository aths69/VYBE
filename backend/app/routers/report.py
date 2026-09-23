"""Report generation endpoint (Section 16)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.reporting.generator import generate_report_html
from app.telemetry.manager import session_manager

router = APIRouter(prefix="/api/sessions", tags=["report"])


@router.get("/{session_id}/report", response_class=HTMLResponse)
def session_report(session_id: str) -> HTMLResponse:
    if session_manager.is_active(session_id):
        raise HTTPException(
            status_code=409,
            detail="Session is still running. Stop it before generating a report.",
        )

    html_content = generate_report_html(session_id)
    if html_content is None:
        raise HTTPException(
            status_code=404,
            detail=f"No completed session found with id '{session_id}'.",
        )
    return HTMLResponse(content=html_content)
