"""Persistence and query functions backing the history/detail API.

Session records are written once, in bulk, when a session stops (see
save_completed_session, called from telemetry/manager.py). Everything here
reads that same durable store, independent of in-memory state - so history
survives a server restart, satisfying Section 12's "users must be able to
view previous sessions" for real, not just for the current process lifetime.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.analysis.efficiency import analyze_efficiency
from app.analysis.stats import compute_telemetry_stats
from app.calculations.carbon import CARBON_NOTE, compute_carbon
from app.calculations.cost import compute_cost
from app.calculations.energy import compute_energy
from app.calculations.water import compute_water
from app.calculations.yield_metrics import compute_yield
from app.config import settings
from app.db.engine import SessionLocal
from app.db.models import (
    RecommendationRecord,
    SessionHardwareRecord,
    SessionMetricsRecord,
    SessionRecord,
    TelemetrySampleRecord,
)
from app.schemas import (
    CarbonResult,
    CostResult,
    EnergyResult,
    GPUProcessInfo,
    GPUSample,
    SessionCalculations,
    SessionComparisonItem,
    SessionDetail,
    SessionHardwareSnapshot,
    SessionListItem,
    SessionSummary,
    TelemetrySample,
)

_SORTABLE_COLUMNS = {
    "start_time": SessionRecord.start_time,
    "runtime_seconds": SessionRecord.runtime_seconds,
    "workload_name": SessionRecord.workload_name,
}


def save_completed_session(
    summary: SessionSummary,
    samples: list[TelemetrySample],
    hardware: SessionHardwareSnapshot | None,
) -> None:
    """Persist a just-stopped session: the session row, every sample, a
    hardware snapshot, and a default-assumption metrics snapshot."""
    energy = compute_energy(samples)
    cost = compute_cost(
        energy.total_energy_kwh, settings.electricity_rate, settings.currency
    )
    carbon = compute_carbon(energy.total_energy_kwh, settings.carbon_intensity_kg_per_kwh)
    water = compute_water(
        energy.total_energy_kwh,
        settings.water_wue_l_per_kwh,
        settings.water_estimation_enabled,
    )

    recommendations = analyze_efficiency(samples, hardware, energy)

    with SessionLocal() as db:
        db.add(
            SessionRecord(
                id=summary.session_id,
                workload_name=summary.workload_name,
                status=summary.status,
                start_time=summary.start_time,
                end_time=summary.end_time,
                interval_seconds=summary.interval_seconds,
                runtime_seconds=summary.runtime_seconds,
                sample_count=summary.sample_count,
                gpu_available=summary.gpu_available,
                is_simulated=summary.is_simulated,
                useful_output_count=summary.useful_output_count,
                useful_output_unit=summary.useful_output_unit,
            )
        )

        for s in samples:
            db.add(
                TelemetrySampleRecord(
                    session_id=summary.session_id,
                    sample_index=s.sample_index,
                    timestamp=s.timestamp,
                    gpu_available=s.gpu.available,
                    gpu_error=s.gpu.error,
                    gpu_utilization_percent=s.gpu.gpu_utilization_percent,
                    gpu_memory_utilization_percent=s.gpu.memory_utilization_percent,
                    vram_used_mb=s.gpu.vram_used_mb,
                    power_draw_w=s.gpu.power_draw_w,
                    temperature_c=s.gpu.temperature_c,
                    process_utilization_available=s.gpu.process_utilization_available,
                    processes_json=json.dumps([p.model_dump() for p in s.gpu.processes]),
                    cpu_utilization_percent=s.cpu_utilization_percent,
                    ram_used_percent=s.ram_used_percent,
                    ram_used_mb=s.ram_used_mb,
                )
            )

        if hardware is not None:
            db.add(
                SessionHardwareRecord(
                    session_id=summary.session_id, **hardware.model_dump()
                )
            )

        db.add(
            SessionMetricsRecord(
                session_id=summary.session_id,
                total_energy_wh=energy.total_energy_wh,
                total_energy_kwh=energy.total_energy_kwh,
                average_power_w=energy.average_power_w,
                peak_power_w=energy.peak_power_w,
                intervals_used=energy.intervals_used,
                intervals_skipped=energy.intervals_skipped,
                coverage_seconds=energy.coverage_seconds,
                currency=cost.currency,
                rate_per_kwh=cost.rate_per_kwh,
                total_cost=cost.total_cost,
                carbon_intensity_kg_per_kwh=carbon.carbon_intensity_kg_per_kwh,
                estimated_kg_co2e=carbon.estimated_kg_co2e,
                water_enabled=water.enabled,
                wue_l_per_kwh=water.wue_l_per_kwh,
                estimated_liters=water.estimated_liters,
                computed_at=datetime.now(timezone.utc),
            )
        )

        for rec in recommendations:
            db.add(
                RecommendationRecord(
                    session_id=summary.session_id,
                    category=rec.category,
                    severity=rec.severity,
                    message=rec.message,
                )
            )

        db.commit()


def list_sessions(
    limit: int = 50,
    offset: int = 0,
    workload_name_contains: str | None = None,
    status: str | None = None,
    sort_by: str = "start_time",
    sort_dir: str = "desc",
) -> tuple[list[SessionListItem], int]:
    column = _SORTABLE_COLUMNS.get(sort_by, SessionRecord.start_time)
    order = column.desc() if sort_dir == "desc" else column.asc()

    with SessionLocal() as db:
        stmt = select(SessionRecord)
        if workload_name_contains:
            stmt = stmt.where(
                SessionRecord.workload_name.ilike(f"%{workload_name_contains}%")
            )
        if status:
            stmt = stmt.where(SessionRecord.status == status)

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        rows = db.scalars(stmt.order_by(order).limit(limit).offset(offset)).all()

        items = []
        for row in rows:
            metrics = db.get(SessionMetricsRecord, row.id)
            items.append(
                SessionListItem(
                    session_id=row.id,
                    workload_name=row.workload_name,
                    status=row.status,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    runtime_seconds=row.runtime_seconds,
                    sample_count=row.sample_count,
                    gpu_available=row.gpu_available,
                    is_simulated=bool(row.is_simulated),
                    total_energy_kwh=metrics.total_energy_kwh if metrics else None,
                    total_cost=metrics.total_cost if metrics else None,
                    currency=metrics.currency if metrics else None,
                )
            )

    return items, total


def get_session_detail(session_id: str) -> SessionDetail | None:
    """Recomputes energy/cost/carbon/water fresh from raw telemetry_samples,
    like /calculations and the report generator do - not from the
    SessionMetricsRecord snapshot (that snapshot exists only to make
    list_sessions's history table fast; reusing it here previously dropped
    computed warnings, e.g. "GPU power unavailable", every time a session was
    revisited after the run that produced them)."""
    with SessionLocal() as db:
        row = db.get(SessionRecord, session_id)
        if row is None:
            return None

        hardware_row = db.get(SessionHardwareRecord, session_id)
        hardware = (
            SessionHardwareSnapshot(
                gpu_name=hardware_row.gpu_name,
                gpu_driver_version=hardware_row.gpu_driver_version,
                gpu_cuda_version=hardware_row.gpu_cuda_version,
                gpu_vram_total_mb=hardware_row.gpu_vram_total_mb,
                gpu_power_limit_w=hardware_row.gpu_power_limit_w,
                cpu_model=hardware_row.cpu_model,
                cpu_physical_cores=hardware_row.cpu_physical_cores,
                cpu_logical_cores=hardware_row.cpu_logical_cores,
                ram_total_mb=hardware_row.ram_total_mb,
                os_pretty_name=hardware_row.os_pretty_name,
            )
            if hardware_row
            else None
        )

    samples = get_telemetry(session_id) or []
    energy = compute_energy(samples)
    cost = compute_cost(energy.total_energy_kwh, settings.electricity_rate, settings.currency)
    carbon = compute_carbon(energy.total_energy_kwh, settings.carbon_intensity_kg_per_kwh)
    water = compute_water(
        energy.total_energy_kwh,
        settings.water_wue_l_per_kwh,
        settings.water_estimation_enabled,
    )
    calculations = SessionCalculations(
        session_id=session_id,
        energy=energy,
        cost=cost,
        carbon=carbon,
        water=water,
        yield_metrics=compute_yield(
            energy, cost, row.useful_output_count, row.useful_output_unit
        ),
    )

    return SessionDetail(
        session_id=row.id,
        workload_name=row.workload_name,
        status=row.status,
        start_time=row.start_time,
        end_time=row.end_time,
        interval_seconds=row.interval_seconds,
        runtime_seconds=row.runtime_seconds,
        sample_count=row.sample_count,
        gpu_available=row.gpu_available,
        is_simulated=bool(row.is_simulated),
        useful_output_count=row.useful_output_count,
        useful_output_unit=row.useful_output_unit,
        hardware=hardware,
        calculations=calculations,
    )


def get_comparison_item(session_id: str) -> SessionComparisonItem | None:
    """One session's row for Section 13 comparison.

    Only sessions that have finished and been persisted (i.e. have a
    SessionMetricsRecord) can be compared - a still-running session has no
    stored default-assumption snapshot yet.
    """
    with SessionLocal() as db:
        row = db.get(SessionRecord, session_id)
        if row is None:
            return None

        metrics_row = db.get(SessionMetricsRecord, session_id)
        if metrics_row is None:
            return None

        energy = EnergyResult(
            total_energy_wh=metrics_row.total_energy_wh,
            total_energy_kwh=metrics_row.total_energy_kwh,
            average_power_w=metrics_row.average_power_w,
            peak_power_w=metrics_row.peak_power_w,
            sample_count=row.sample_count,
            runtime_seconds=row.runtime_seconds,
            intervals_used=metrics_row.intervals_used,
            intervals_skipped=metrics_row.intervals_skipped,
            coverage_seconds=metrics_row.coverage_seconds,
            warnings=[],
        )
        cost = CostResult(
            currency=metrics_row.currency,
            rate_per_kwh=metrics_row.rate_per_kwh,
            total_cost=metrics_row.total_cost,
        )
        carbon = CarbonResult(
            carbon_intensity_kg_per_kwh=metrics_row.carbon_intensity_kg_per_kwh,
            estimated_kg_co2e=metrics_row.estimated_kg_co2e,
            note=CARBON_NOTE,
        )

        item = SessionComparisonItem(
            session_id=row.id,
            workload_name=row.workload_name,
            status=row.status,
            start_time=row.start_time,
            end_time=row.end_time,
            runtime_seconds=row.runtime_seconds,
            is_simulated=bool(row.is_simulated),
            useful_output_count=row.useful_output_count,
            useful_output_unit=row.useful_output_unit,
            stats=compute_telemetry_stats(get_telemetry(session_id) or []),
            energy=energy,
            cost=cost,
            carbon=carbon,
            yield_metrics=compute_yield(
                energy, cost, row.useful_output_count, row.useful_output_unit
            ),
        )

    return item


def get_hardware(session_id: str) -> SessionHardwareSnapshot | None:
    with SessionLocal() as db:
        row = db.get(SessionHardwareRecord, session_id)
        if row is None:
            return None
        return SessionHardwareSnapshot(
            gpu_name=row.gpu_name,
            gpu_driver_version=row.gpu_driver_version,
            gpu_cuda_version=row.gpu_cuda_version,
            gpu_vram_total_mb=row.gpu_vram_total_mb,
            gpu_power_limit_w=row.gpu_power_limit_w,
            cpu_model=row.cpu_model,
            cpu_physical_cores=row.cpu_physical_cores,
            cpu_logical_cores=row.cpu_logical_cores,
            ram_total_mb=row.ram_total_mb,
            os_pretty_name=row.os_pretty_name,
        )


def get_output_info(session_id: str) -> tuple[int | None, str | None]:
    """Lightweight lookup of a stored session's useful-output count/unit,
    without building the full SessionDetail (which also computes calculations)."""
    with SessionLocal() as db:
        row = db.get(SessionRecord, session_id)
        if row is None:
            return None, None
        return row.useful_output_count, row.useful_output_unit


def get_telemetry(session_id: str) -> list[TelemetrySample] | None:
    with SessionLocal() as db:
        if db.get(SessionRecord, session_id) is None:
            return None

        rows = db.scalars(
            select(TelemetrySampleRecord)
            .where(TelemetrySampleRecord.session_id == session_id)
            .order_by(TelemetrySampleRecord.sample_index)
        ).all()

        return [_row_to_sample(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with SessionLocal() as db:
        row = db.get(SessionRecord, session_id)
        if row is None:
            return False
        db.delete(row)  # cascades to samples/hardware/metrics/recommendations
        db.commit()
        return True


def _row_to_sample(row: TelemetrySampleRecord) -> TelemetrySample:
    processes = [GPUProcessInfo(**p) for p in json.loads(row.processes_json)]
    return TelemetrySample(
        sample_index=row.sample_index,
        timestamp=row.timestamp,
        gpu=GPUSample(
            available=row.gpu_available,
            error=row.gpu_error,
            gpu_utilization_percent=row.gpu_utilization_percent,
            memory_utilization_percent=row.gpu_memory_utilization_percent,
            vram_used_mb=row.vram_used_mb,
            power_draw_w=row.power_draw_w,
            temperature_c=row.temperature_c,
            processes=processes,
            process_utilization_available=row.process_utilization_available,
        ),
        cpu_utilization_percent=row.cpu_utilization_percent,
        ram_used_percent=row.ram_used_percent,
        ram_used_mb=row.ram_used_mb,
    )
