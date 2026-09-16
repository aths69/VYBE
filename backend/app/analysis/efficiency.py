"""Efficiency heuristics (Section 10).

Every finding here is a HEURISTIC HYPOTHESIS about *why* a pattern in the
telemetry might exist, never a proven diagnosis - phrased with "may"/"could"/
"consider", per Section 10's explicit instruction. Thresholds are simple,
documented constants, deliberately conservative (a capstone-appropriate
heuristic engine, not a tuned production anomaly detector).

Idle-time and "poor consistency" checks reuse the same actual-Δt approach as
energy.py's integration, for the same reason: real sampling intervals jitter,
so summing real per-interval Δt is more accurate than counting samples and
assuming a fixed step.
"""

import statistics

from app.schemas import (
    EnergyResult,
    Recommendation,
    SessionHardwareSnapshot,
    TelemetrySample,
)

MIN_SAMPLES_FOR_ANALYSIS = 5

LOW_UTIL_THRESHOLD = 30.0
HIGH_POWER_RATIO_OF_PEAK = 0.7

VRAM_HIGH_RATIO = 0.90
VRAM_LOW_RATIO = 0.35

CPU_BOTTLENECK_THRESHOLD = 85.0
CPU_BOTTLENECK_GPU_CEILING = 70.0

RAM_BOTTLENECK_THRESHOLD = 90.0

IDLE_UTIL_THRESHOLD = 5.0
IDLE_FRACTION_THRESHOLD = 0.30

POWER_NEAR_LIMIT_RATIO = 0.90

UTIL_STDDEV_HIGH = 25.0


def analyze_efficiency(
    samples: list[TelemetrySample],
    hardware: SessionHardwareSnapshot | None,
    energy: EnergyResult,
) -> list[Recommendation]:
    gpu_samples = [s for s in samples if s.gpu.available]

    if len(gpu_samples) < MIN_SAMPLES_FOR_ANALYSIS:
        return [
            Recommendation(
                category="insufficient_data",
                severity="info",
                message=(
                    f"Only {len(gpu_samples)} sample(s) with GPU data were available. "
                    "Efficiency analysis needs more data to produce reliable findings."
                ),
            )
        ]

    findings: list[Recommendation] = []

    utils = [s.gpu.gpu_utilization_percent for s in gpu_samples if s.gpu.gpu_utilization_percent is not None]
    avg_util = statistics.mean(utils) if utils else None

    avg_power = energy.average_power_w
    peak_power = energy.peak_power_w

    _check_gpu_underutilization(findings, avg_util)
    _check_high_power_low_utilization(findings, avg_util, avg_power, peak_power)
    _check_vram_usage(findings, gpu_samples, hardware)
    _check_cpu_bottleneck(findings, samples, avg_util)
    _check_ram_bottleneck(findings, samples)
    _check_idle_periods(findings, gpu_samples)
    _check_power_near_limit(findings, peak_power, hardware)
    _check_utilization_consistency(findings, utils)

    if not findings:
        findings.append(
            Recommendation(
                category="no_issues_flagged",
                severity="info",
                message=(
                    "No heuristic issues were flagged for this session based on current "
                    "thresholds. This does not confirm optimal efficiency - only that none "
                    "of the implemented heuristics were triggered."
                ),
            )
        )

    return findings


def _check_gpu_underutilization(findings: list[Recommendation], avg_util: float | None) -> None:
    if avg_util is not None and avg_util < LOW_UTIL_THRESHOLD:
        findings.append(
            Recommendation(
                category="gpu_underutilization",
                severity="warning",
                message=(
                    f"GPU utilization averaged {avg_util:.1f}% for this session. The "
                    "workload may be bound by something other than the GPU (data loading, "
                    "CPU preprocessing, small batch size) - consider profiling the input "
                    "pipeline or increasing batch size if memory allows."
                ),
            )
        )


def _check_high_power_low_utilization(
    findings: list[Recommendation],
    avg_util: float | None,
    avg_power: float | None,
    peak_power: float | None,
) -> None:
    if (
        avg_util is not None
        and avg_power is not None
        and peak_power is not None
        and peak_power > 0
        and avg_util < LOW_UTIL_THRESHOLD
        and (avg_power / peak_power) >= HIGH_POWER_RATIO_OF_PEAK
    ):
        findings.append(
            Recommendation(
                category="high_power_low_utilization",
                severity="warning",
                message=(
                    f"GPU utilization averaged {avg_util:.1f}% while average power "
                    f"({avg_power:.1f} W) stayed close to the session's peak "
                    f"({peak_power:.1f} W). The GPU may be drawing power without doing "
                    "proportional compute work - possibly CPU/input-data bound."
                ),
            )
        )


def _check_vram_usage(
    findings: list[Recommendation],
    gpu_samples: list[TelemetrySample],
    hardware: SessionHardwareSnapshot | None,
) -> None:
    if hardware is None or not hardware.gpu_vram_total_mb:
        return

    vram_used = [s.gpu.vram_used_mb for s in gpu_samples if s.gpu.vram_used_mb is not None]
    if not vram_used:
        return

    avg_vram = statistics.mean(vram_used)
    ratio = avg_vram / hardware.gpu_vram_total_mb

    if ratio >= VRAM_HIGH_RATIO:
        findings.append(
            Recommendation(
                category="vram_high_usage",
                severity="warning",
                message=(
                    f"VRAM usage averaged {ratio * 100:.0f}% of the {hardware.gpu_vram_total_mb:.0f} MB "
                    "available. This session is close to running out of GPU memory - consider "
                    "reducing batch size to avoid an out-of-memory failure."
                ),
            )
        )
    elif ratio <= VRAM_LOW_RATIO:
        findings.append(
            Recommendation(
                category="vram_low_usage",
                severity="info",
                message=(
                    f"VRAM usage stayed below {VRAM_LOW_RATIO * 100:.0f}% of available memory for "
                    "most of the run. Increasing batch size may improve GPU utilization, if the "
                    "model and workload allow it."
                ),
            )
        )


def _check_cpu_bottleneck(
    findings: list[Recommendation], samples: list[TelemetrySample], avg_util: float | None
) -> None:
    cpu_utils = [s.cpu_utilization_percent for s in samples if s.cpu_utilization_percent is not None]
    if not cpu_utils:
        return

    avg_cpu = statistics.mean(cpu_utils)
    if avg_cpu >= CPU_BOTTLENECK_THRESHOLD and (avg_util is None or avg_util < CPU_BOTTLENECK_GPU_CEILING):
        findings.append(
            Recommendation(
                category="cpu_bottleneck",
                severity="warning",
                message=(
                    f"CPU utilization averaged {avg_cpu:.1f}% while the GPU was not saturated. "
                    "The GPU may be waiting on CPU-bound work such as data loading or "
                    "preprocessing."
                ),
            )
        )


def _check_ram_bottleneck(findings: list[Recommendation], samples: list[TelemetrySample]) -> None:
    ram_percents = [s.ram_used_percent for s in samples if s.ram_used_percent is not None]
    if not ram_percents:
        return

    avg_ram = statistics.mean(ram_percents)
    if avg_ram >= RAM_BOTTLENECK_THRESHOLD:
        findings.append(
            Recommendation(
                category="ram_bottleneck",
                severity="warning",
                message=(
                    f"System RAM usage averaged {avg_ram:.1f}%. Sustained high RAM usage can "
                    "cause swapping, which would slow down data loading and hurt overall "
                    "throughput."
                ),
            )
        )


def _check_idle_periods(findings: list[Recommendation], gpu_samples: list[TelemetrySample]) -> None:
    ordered = sorted(gpu_samples, key=lambda s: s.sample_index)
    if len(ordered) < 2:
        return

    idle_seconds = 0.0
    total_seconds = 0.0

    for prev, curr in zip(ordered, ordered[1:]):
        delta_t = (curr.timestamp - prev.timestamp).total_seconds()
        if delta_t <= 0:
            continue
        total_seconds += delta_t

        u_prev = prev.gpu.gpu_utilization_percent
        u_curr = curr.gpu.gpu_utilization_percent
        if u_prev is not None and u_curr is not None and u_prev <= IDLE_UTIL_THRESHOLD and u_curr <= IDLE_UTIL_THRESHOLD:
            idle_seconds += delta_t

    if total_seconds <= 0:
        return

    idle_fraction = idle_seconds / total_seconds
    if idle_fraction >= IDLE_FRACTION_THRESHOLD:
        findings.append(
            Recommendation(
                category="idle_periods",
                severity="info",
                message=(
                    f"The GPU was effectively idle (≤{IDLE_UTIL_THRESHOLD:.0f}% utilization) for "
                    f"about {idle_fraction * 100:.0f}% of the monitored time "
                    f"({idle_seconds:.1f}s of {total_seconds:.1f}s). This suggests the workload "
                    "wasn't continuously using the GPU during the session."
                ),
            )
        )


def _check_power_near_limit(
    findings: list[Recommendation],
    peak_power: float | None,
    hardware: SessionHardwareSnapshot | None,
) -> None:
    if peak_power is None or hardware is None or not hardware.gpu_power_limit_w:
        return

    ratio = peak_power / hardware.gpu_power_limit_w
    if ratio >= POWER_NEAR_LIMIT_RATIO:
        findings.append(
            Recommendation(
                category="high_power_near_limit",
                severity="info",
                message=(
                    f"Peak power draw ({peak_power:.1f} W) reached {ratio * 100:.0f}% of the "
                    f"GPU's {hardware.gpu_power_limit_w:.0f} W power cap. The GPU may be close to "
                    "power/thermal throttling under sustained load."
                ),
            )
        )


def _check_utilization_consistency(findings: list[Recommendation], utils: list[float]) -> None:
    if len(utils) < 2:
        return

    stdev = statistics.pstdev(utils)
    if stdev >= UTIL_STDDEV_HIGH:
        findings.append(
            Recommendation(
                category="utilization_inconsistency",
                severity="info",
                message=(
                    f"GPU utilization varied widely across the session (population standard "
                    f"deviation ≈{stdev:.1f} percentage points). Bursty utilization can indicate "
                    "an inconsistent data pipeline or periodic stalls rather than steady "
                    "compute work."
                ),
            )
        )
