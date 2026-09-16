from fastapi import APIRouter, HTTPException, Query

from app.db import repository
from app.schemas import (
    SessionInfo,
    SessionSummary,
    StartSessionRequest,
    StopSessionRequest,
    TelemetrySample,
)
from app.telemetry.manager import (
    NoActiveSessionError,
    SessionAlreadyRunningError,
    SessionNotFoundError,
    session_manager,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionInfo)
def start_session(payload: StartSessionRequest) -> SessionInfo:
    try:
        return session_manager.start(payload.workload_name, payload.interval_seconds)
    except SessionAlreadyRunningError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{session_id}/stop", response_model=SessionSummary)
def stop_session(
    session_id: str, payload: StopSessionRequest | None = None
) -> SessionSummary:
    output_count = payload.useful_output_count if payload else None
    output_unit = payload.useful_output_unit if payload else None
    try:
        return session_manager.stop(session_id, output_count, output_unit)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/current", response_model=SessionInfo)
def current_session() -> SessionInfo:
    try:
        return session_manager.get_status()
    except NoActiveSessionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=SessionInfo)
def session_status(session_id: str) -> SessionInfo:
    try:
        return session_manager.get_status(session_id)
    except SessionNotFoundError:
        pass  # not the live session - fall through to durable storage below

    detail = repository.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(
            status_code=404, detail=f"No session found with id '{session_id}'."
        )
    return SessionInfo(
        session_id=detail.session_id,
        workload_name=detail.workload_name,
        status=detail.status,
        start_time=detail.start_time,
        end_time=detail.end_time,
        interval_seconds=detail.interval_seconds,
        sample_count=detail.sample_count,
        gpu_available=detail.gpu_available,
    )


@router.get("/{session_id}/telemetry", response_model=list[TelemetrySample])
def session_telemetry(
    session_id: str, since_index: int = Query(default=0, ge=0)
) -> list[TelemetrySample]:
    try:
        return session_manager.get_telemetry(session_id, since_index)
    except SessionNotFoundError:
        pass  # not the live session - fall through to durable storage below

    samples = repository.get_telemetry(session_id)
    if samples is None:
        raise HTTPException(
            status_code=404, detail=f"No session found with id '{session_id}'."
        )
    return [s for s in samples if s.sample_index >= since_index]
