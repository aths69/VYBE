"""Aggregate telemetry statistics shared by comparison (Section 13) and
report generation (Section 16).

Averages/peaks here are computed directly from already-MEASURED per-sample
fields (Section 2) - no cost/energy/carbon model involved - so the result
stays labeled MEASURED, distinct from energy.py's CALCULATED output.
"""

import statistics

from app.schemas import TelemetryStats, TelemetrySample


def compute_telemetry_stats(samples: list[TelemetrySample]) -> TelemetryStats:
    gpu_samples = [s for s in samples if s.gpu.available]

    utils = [
        s.gpu.gpu_utilization_percent
        for s in gpu_samples
        if s.gpu.gpu_utilization_percent is not None
    ]
    vram = [s.gpu.vram_used_mb for s in gpu_samples if s.gpu.vram_used_mb is not None]
    temps = [s.gpu.temperature_c for s in gpu_samples if s.gpu.temperature_c is not None]
    cpu = [s.cpu_utilization_percent for s in samples if s.cpu_utilization_percent is not None]
    ram = [s.ram_used_percent for s in samples if s.ram_used_percent is not None]

    return TelemetryStats(
        average_gpu_utilization_percent=statistics.mean(utils) if utils else None,
        peak_gpu_utilization_percent=max(utils) if utils else None,
        average_vram_used_mb=statistics.mean(vram) if vram else None,
        peak_vram_used_mb=max(vram) if vram else None,
        peak_temperature_c=max(temps) if temps else None,
        average_cpu_utilization_percent=statistics.mean(cpu) if cpu else None,
        average_ram_used_percent=statistics.mean(ram) if ram else None,
        peak_ram_used_percent=max(ram) if ram else None,
    )
