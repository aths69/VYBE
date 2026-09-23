"""SQLAlchemy ORM models (Section 19).

Persistence happens once, in bulk, when a session stops (see
telemetry/manager.py) - not per-poll. Section 22 warns against expensive
per-second operations, and a 1Hz SQLite write during live polling would be
exactly that; batching the write to session-end keeps monitoring overhead low
while still making every session durable across a server restart.
"""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    workload_name: Mapped[str]
    status: Mapped[str]
    start_time: Mapped[datetime]
    end_time: Mapped[datetime | None]
    interval_seconds: Mapped[float]
    runtime_seconds: Mapped[float]
    sample_count: Mapped[int]
    gpu_available: Mapped[bool]
    is_simulated: Mapped[bool] = mapped_column(default=False)
    useful_output_count: Mapped[int | None]
    useful_output_unit: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    samples: Mapped[list["TelemetrySampleRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    hardware: Mapped["SessionHardwareRecord | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    metrics: Mapped["SessionMetricsRecord | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    recommendations: Mapped[list["RecommendationRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class TelemetrySampleRecord(Base):
    __tablename__ = "telemetry_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    sample_index: Mapped[int]
    timestamp: Mapped[datetime]

    gpu_available: Mapped[bool]
    gpu_error: Mapped[str | None]
    gpu_utilization_percent: Mapped[float | None]
    gpu_memory_utilization_percent: Mapped[float | None]
    vram_used_mb: Mapped[float | None]
    power_draw_w: Mapped[float | None]
    temperature_c: Mapped[float | None]
    process_utilization_available: Mapped[bool]
    processes_json: Mapped[str]  # JSON list of {pid, process_name, gpu_memory_used_mb, ...}

    cpu_utilization_percent: Mapped[float | None]
    ram_used_percent: Mapped[float | None]
    ram_used_mb: Mapped[float | None]

    session: Mapped["SessionRecord"] = relationship(back_populates="samples")


class SessionHardwareRecord(Base):
    __tablename__ = "session_hardware"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), primary_key=True)
    gpu_name: Mapped[str | None]
    gpu_driver_version: Mapped[str | None]
    gpu_cuda_version: Mapped[str | None]
    gpu_vram_total_mb: Mapped[float | None]
    gpu_power_limit_w: Mapped[float | None]
    cpu_model: Mapped[str | None]
    cpu_physical_cores: Mapped[int | None]
    cpu_logical_cores: Mapped[int | None]
    ram_total_mb: Mapped[float]
    os_pretty_name: Mapped[str | None]

    session: Mapped["SessionRecord"] = relationship(back_populates="hardware")


class SessionMetricsRecord(Base):
    """A default-assumption snapshot computed once at session-stop time.

    Used for fast history-list rendering. The detail/calculations endpoints
    still recompute from raw telemetry_samples on demand (Section 2: derived
    values must stay traceable to raw measurements, and recomputing lets
    callers override rate/currency/carbon-intensity/WUE after the fact).
    """

    __tablename__ = "session_metrics"

    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), primary_key=True)

    total_energy_wh: Mapped[float]
    total_energy_kwh: Mapped[float]
    average_power_w: Mapped[float | None]
    peak_power_w: Mapped[float | None]
    intervals_used: Mapped[int]
    intervals_skipped: Mapped[int]
    coverage_seconds: Mapped[float]

    currency: Mapped[str]
    rate_per_kwh: Mapped[float]
    total_cost: Mapped[float]

    carbon_intensity_kg_per_kwh: Mapped[float]
    estimated_kg_co2e: Mapped[float]

    water_enabled: Mapped[bool]
    wue_l_per_kwh: Mapped[float | None]
    estimated_liters: Mapped[float | None]

    computed_at: Mapped[datetime] = mapped_column(default=_utcnow)

    session: Mapped["SessionRecord"] = relationship(back_populates="metrics")


class RecommendationRecord(Base):
    """Schema in place now; populated by Phase 5's efficiency analysis engine."""

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    category: Mapped[str]
    severity: Mapped[str]
    message: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    session: Mapped["SessionRecord"] = relationship(back_populates="recommendations")
