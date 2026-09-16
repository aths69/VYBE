"""Energy integration (Section 6).

Energy is CALCULATED from measured GPU power - never presented as a direct
measurement. Integration uses the ACTUAL elapsed time between each pair of
consecutive samples (trapezoidal rule: average of the two endpoint power
readings times the real Δt), not an assumed fixed interval. Confirmed live:
even at a "1 second" setting, real gaps between samples jitter (~0.997s to
1.0012s) - using the true per-interval Δt instead of the nominal interval
avoids compounding that jitter into the energy total.

An interval is skipped (not counted as zero, not filled with a guess) when
GPU power is unavailable at either endpoint, keeping with Section 3: never
invent data to fill a gap. Skipped intervals are reported, not hidden.
"""

from app.schemas import EnergyResult, TelemetrySample


def compute_energy(samples: list[TelemetrySample]) -> EnergyResult:
    if not samples:
        return EnergyResult(
            total_energy_wh=0.0,
            total_energy_kwh=0.0,
            sample_count=0,
            runtime_seconds=0.0,
            intervals_used=0,
            intervals_skipped=0,
            coverage_seconds=0.0,
            warnings=["No telemetry samples available."],
        )

    ordered = sorted(samples, key=lambda s: s.sample_index)
    runtime_seconds = (ordered[-1].timestamp - ordered[0].timestamp).total_seconds()

    energy_wh = 0.0
    coverage_seconds = 0.0
    intervals_used = 0
    intervals_skipped = 0

    for prev, curr in zip(ordered, ordered[1:]):
        delta_t = (curr.timestamp - prev.timestamp).total_seconds()
        p_prev = prev.gpu.power_draw_w if prev.gpu.available else None
        p_curr = curr.gpu.power_draw_w if curr.gpu.available else None

        if delta_t <= 0 or p_prev is None or p_curr is None:
            intervals_skipped += 1
            continue

        avg_power_w = (p_prev + p_curr) / 2
        energy_wh += avg_power_w * (delta_t / 3600)
        coverage_seconds += delta_t
        intervals_used += 1

    powers_seen = [
        s.gpu.power_draw_w
        for s in ordered
        if s.gpu.available and s.gpu.power_draw_w is not None
    ]

    warnings = []
    if len(ordered) < 2:
        warnings.append("Fewer than 2 samples - energy cannot be integrated over time.")
    if intervals_skipped:
        warnings.append(
            f"{intervals_skipped} interval(s) excluded from the energy integration "
            "because GPU power was unavailable at one or both endpoints."
        )

    return EnergyResult(
        total_energy_wh=energy_wh,
        total_energy_kwh=energy_wh / 1000,
        average_power_w=(sum(powers_seen) / len(powers_seen)) if powers_seen else None,
        peak_power_w=max(powers_seen) if powers_seen else None,
        sample_count=len(ordered),
        runtime_seconds=runtime_seconds,
        intervals_used=intervals_used,
        intervals_skipped=intervals_skipped,
        coverage_seconds=coverage_seconds,
        warnings=warnings,
    )
