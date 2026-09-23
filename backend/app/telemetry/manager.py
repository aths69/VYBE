"""In-memory telemetry polling and session lifecycle (Phase 2), now backed by
durable storage (Phase 4).

This module owns only the LIVE, currently-running session: the poll loop and
its in-memory sample buffer. The moment a session stops, its samples, a
hardware snapshot, and default-assumption metrics are persisted in bulk to
SQLite (app.db.repository) and the in-memory copy is dropped - history for
any session that isn't the active one is served from the database (see
app/routers/sessions.py and app/routers/history.py), which is what makes it
durable across a server restart.

Only one session runs at a time: this targets a single workstation/GPU
monitoring its own workload, not concurrent multi-tenant monitoring - keeping
this simple avoids overengineering a use case the project doesn't need.
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from app.hardware.gpu import close_gpu_handle, detect_gpu, open_gpu_handle, sample_gpu
from app.hardware.simulator import SimulatedWorkloadState, simulated_hardware_snapshot
from app.hardware.system import cpu_ram_snapshot, detect_system
from app.schemas import (
    GPUSample,
    SessionHardwareSnapshot,
    SessionInfo,
    SessionSummary,
    TelemetrySample,
)


class SessionAlreadyRunningError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class NoActiveSessionError(Exception):
    pass


@dataclass
class _Session:
    id: str
    workload_name: str
    interval_seconds: float
    start_time: datetime
    end_time: datetime | None = None
    status: str = "running"
    gpu_handle: object = None
    gpu_available: bool = False
    simulate: bool = False
    sim_state: SimulatedWorkloadState | None = None
    hardware_snapshot: SessionHardwareSnapshot | None = None
    samples: list[TelemetrySample] = field(default_factory=list)
    samples_lock: threading.Lock = field(default_factory=threading.Lock)
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: _Session | None = None

    def start(
        self, workload_name: str, interval_seconds: float | None, simulate: bool = False
    ) -> SessionInfo:
        with self._lock:
            if self._active is not None:
                raise SessionAlreadyRunningError(
                    f"Session '{self._active.id}' is already running; stop it first."
                )

            interval = interval_seconds or settings.telemetry_interval_seconds
            session = _Session(
                id=uuid4().hex,
                workload_name=workload_name,
                interval_seconds=interval,
                start_time=datetime.now(timezone.utc),
                simulate=simulate,
            )
            if simulate:
                # Section 24: synthetic telemetry, never a real NVML handle -
                # gpu_available=True here means "this session has GPU-shaped
                # samples", distinct from is_simulated meaning "they're fake".
                session.gpu_available = True
                session.hardware_snapshot = simulated_hardware_snapshot()
                session.sim_state = SimulatedWorkloadState(seed=session.id)
            else:
                session.gpu_handle = open_gpu_handle()
                session.gpu_available = session.gpu_handle is not None
                session.hardware_snapshot = self._snapshot_hardware()

            session.thread = threading.Thread(
                target=self._poll_loop, args=(session,), daemon=True
            )
            self._active = session
            session.thread.start()
            return self._to_info(session)

    def stop(
        self,
        session_id: str,
        useful_output_count: int | None = None,
        useful_output_unit: str | None = None,
    ) -> SessionSummary:
        with self._lock:
            session = self._active
            if session is None or session.id != session_id:
                raise SessionNotFoundError(
                    f"No running session with id '{session_id}'."
                )
            session.stop_event.set()

        assert session.thread is not None  # always set in start() before this point
        session.thread.join(timeout=session.interval_seconds + 5)
        session.status = "stopped"
        session.end_time = session.end_time or datetime.now(timezone.utc)

        info = self._to_info(session)
        runtime = (session.end_time - session.start_time).total_seconds()
        summary = SessionSummary(
            **info.model_dump(),
            runtime_seconds=runtime,
            useful_output_count=useful_output_count,
            useful_output_unit=useful_output_unit,
        )

        with session.samples_lock:
            samples_snapshot = list(session.samples)

        from app.db.repository import save_completed_session  # avoid import cycle

        save_completed_session(summary, samples_snapshot, session.hardware_snapshot)

        with self._lock:
            self._active = None

        return summary

    def is_active(self, session_id: str) -> bool:
        with self._lock:
            return self._active is not None and self._active.id == session_id

    def get_hardware_snapshot(self, session_id: str) -> SessionHardwareSnapshot:
        session = self._find(session_id)
        if session.hardware_snapshot is None:
            raise SessionNotFoundError(f"No hardware snapshot for session '{session_id}'.")
        return session.hardware_snapshot

    def get_status(self, session_id: str | None = None) -> SessionInfo:
        session = self._find(session_id)
        return self._to_info(session)

    def get_telemetry(self, session_id: str, since_index: int = 0) -> list[TelemetrySample]:
        session = self._find(session_id)
        with session.samples_lock:
            return [s for s in session.samples if s.sample_index >= since_index]

    def _find(self, session_id: str | None) -> _Session:
        with self._lock:
            if session_id is None:
                if self._active is None:
                    raise NoActiveSessionError("No monitoring session is currently running.")
                return self._active
            if self._active is not None and self._active.id == session_id:
                return self._active
        raise SessionNotFoundError(f"No currently running session with id '{session_id}'.")

    @staticmethod
    def _snapshot_hardware() -> SessionHardwareSnapshot:
        gpu_info = detect_gpu()
        system_info = detect_system()
        return SessionHardwareSnapshot(
            gpu_name=gpu_info.name,
            gpu_driver_version=gpu_info.driver_version,
            gpu_cuda_version=gpu_info.cuda_version,
            gpu_vram_total_mb=gpu_info.vram_total_mb,
            gpu_power_limit_w=gpu_info.power_limit_w,
            cpu_model=system_info.cpu.model,
            cpu_physical_cores=system_info.cpu.physical_cores,
            cpu_logical_cores=system_info.cpu.logical_cores,
            ram_total_mb=system_info.memory.total_mb,
            os_pretty_name=system_info.os.pretty_name,
        )

    def _to_info(self, session: _Session) -> SessionInfo:
        with session.samples_lock:
            sample_count = len(session.samples)
        return SessionInfo(
            session_id=session.id,
            workload_name=session.workload_name,
            status=session.status,
            start_time=session.start_time,
            end_time=session.end_time,
            interval_seconds=session.interval_seconds,
            sample_count=sample_count,
            gpu_available=session.gpu_available,
            is_simulated=session.simulate,
        )

    def _poll_loop(self, session: _Session) -> None:
        next_tick = time.monotonic()
        idx = 0
        try:
            while not session.stop_event.is_set():
                sample = self._capture_sample(session, idx)
                with session.samples_lock:
                    session.samples.append(sample)
                idx += 1

                next_tick += session.interval_seconds
                wait_time = next_tick - time.monotonic()
                if wait_time > 0:
                    session.stop_event.wait(wait_time)
                else:
                    # Fell behind (slow sample or system hiccup) - resync
                    # instead of firing a burst of catch-up samples.
                    next_tick = time.monotonic()
        finally:
            close_gpu_handle(session.gpu_handle)

    @staticmethod
    def _capture_sample(session: _Session, idx: int) -> TelemetrySample:
        if session.simulate:
            assert session.sim_state is not None  # always set when simulate=True
            gpu_sample, cpu_percent, ram_percent, ram_used_mb = session.sim_state.step()
        else:
            try:
                gpu_sample = sample_gpu(session.gpu_handle)
            except Exception as exc:  # never let a bad poll kill the loop
                gpu_sample = GPUSample(available=False, error=str(exc))

            cpu_percent, ram_percent, ram_used_mb = cpu_ram_snapshot()

        return TelemetrySample(
            sample_index=idx,
            timestamp=datetime.now(timezone.utc),
            gpu=gpu_sample,
            cpu_utilization_percent=cpu_percent,
            ram_used_percent=ram_percent,
            ram_used_mb=ram_used_mb,
        )


session_manager = SessionManager()
