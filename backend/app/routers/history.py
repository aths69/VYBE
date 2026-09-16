
from fastapi import APIRouter, HTTPException, Query

from app.db import repository
from app.schemas import SessionDetail, SessionListResponse
from app.telemetry.manager import session_manager

router = APIRouter(prefix="/api/sessions", tags=["history"])


@router.get("/history", response_model=SessionListResponse)
def session_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    workload_name: str | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(running|stopped)$"),
    sort_by: str = Query(
        default="start_time", pattern="^(start_time|runtime_seconds|workload_name)$"
    ),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> SessionListResponse:
    items, total = repository.list_sessions(
        limit=limit,
        offset=offset,
        workload_name_contains=workload_name,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return SessionListResponse(total=total, items=items)


@router.get("/{session_id}/detail", response_model=SessionDetail)
def session_detail(session_id: str) -> SessionDetail:
    detail = repository.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"No stored session found with id '{session_id}'.",
        )
    return detail


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict:
    if session_manager.is_active(session_id):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a currently running session; stop it first.",
        )
    if not repository.delete_session(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"No stored session found with id '{session_id}'.",
        )
    return {"deleted": True, "session_id": session_id}
