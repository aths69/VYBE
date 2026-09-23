"""Section 25: telemetry processing.

Covers app/analysis/stats.py (aggregate MEASURED stats) and
app/analysis/efficiency.py (heuristic findings, Section 10) - both consume
raw TelemetrySample lists, so these are pure-function tests against
hand-built telemetry.
"""

import pytest

from app.analysis.efficiency import (
    LOW_UTIL_THRESHOLD,
    MIN_SAMPLES_FOR_ANALYSIS,
    analyze_efficiency,
)
from app.analysis.stats import compute_telemetry_stats
from app.calculations.energy import compute_energy
from tests.conftest import make_sample


# ---------- compute_telemetry_stats ----------


def test_stats_on_empty_samples_are_all_none():
    stats = compute_telemetry_stats([])
    assert stats.label == "MEASURED"
    assert stats.average_gpu_utilization_percent is None
    assert stats.peak_gpu_utilization_percent is None
    assert stats.average_cpu_utilization_percent is None


def test_stats_average_and_peak_over_available_gpu_samples():
    samples = [
        make_sample(0, gpu_util=20.0, vram_mb=500.0, temp_c=40.0, cpu_percent=10.0, ram_percent=20.0),
        make_sample(1, gpu_util=80.0, vram_mb=1500.0, temp_c=60.0, cpu_percent=30.0, ram_percent=40.0),
    ]
    stats = compute_telemetry_stats(samples)
    assert stats.average_gpu_utilization_percent == pytest.approx(50.0)
    assert stats.peak_gpu_utilization_percent == 80.0
    assert stats.average_vram_used_mb == pytest.approx(1000.0)
    assert stats.peak_vram_used_mb == 1500.0
    assert stats.peak_temperature_c == 60.0
    assert stats.average_cpu_utilization_percent == pytest.approx(20.0)
    assert stats.average_ram_used_percent == pytest.approx(30.0)
    assert stats.peak_ram_used_percent == 40.0


def test_stats_ignore_unavailable_gpu_samples_but_keep_cpu_ram():
    samples = [
        make_sample(0, gpu_available=False, cpu_percent=50.0, ram_percent=60.0),
        make_sample(1, gpu_util=90.0, cpu_percent=10.0, ram_percent=20.0),
    ]
    stats = compute_telemetry_stats(samples)
    # only the available GPU sample counts toward GPU stats
    assert stats.average_gpu_utilization_percent == 90.0
    assert stats.peak_gpu_utilization_percent == 90.0
    # CPU/RAM stats are independent of GPU availability
    assert stats.average_cpu_utilization_percent == pytest.approx(30.0)


# ---------- analyze_efficiency ----------


def test_insufficient_data_below_minimum_samples(hardware_snapshot):
    samples = [make_sample(i) for i in range(MIN_SAMPLES_FOR_ANALYSIS - 1)]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    assert len(findings) == 1
    assert findings[0].category == "insufficient_data"


def test_gpu_underutilization_flagged(hardware_snapshot):
    samples = [
        make_sample(i, gpu_util=LOW_UTIL_THRESHOLD - 5, power_w=5.0)
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 2)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    categories = {f.category for f in findings}
    assert "gpu_underutilization" in categories


def test_no_issues_flagged_when_healthy(hardware_snapshot):
    # Moderate, steady utilization; VRAM mid-range; CPU/RAM comfortable;
    # power well under cap - none of the heuristics should trip.
    samples = [
        make_sample(
            i,
            gpu_util=60.0,
            vram_mb=3000.0,  # ~49% of the 6144 MB snapshot - between the 35%/90% thresholds
            power_w=20.0,
            cpu_percent=40.0,
            ram_percent=50.0,
            temp_c=55.0,
        )
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 5)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    assert [f.category for f in findings] == ["no_issues_flagged"]


def test_vram_high_usage_flagged_near_capacity(hardware_snapshot):
    samples = [
        make_sample(i, gpu_util=60.0, vram_mb=6000.0)  # ~97% of 6144 MB
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 2)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    assert any(f.category == "vram_high_usage" for f in findings)


def test_cpu_bottleneck_flagged_when_cpu_saturated_gpu_idle(hardware_snapshot):
    samples = [
        make_sample(i, gpu_util=20.0, cpu_percent=95.0)
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 2)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    assert any(f.category == "cpu_bottleneck" for f in findings)


def test_ram_bottleneck_flagged(hardware_snapshot):
    samples = [
        make_sample(i, gpu_util=60.0, ram_percent=95.0)
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 2)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    assert any(f.category == "ram_bottleneck" for f in findings)


def test_idle_periods_flagged(hardware_snapshot):
    samples = [
        make_sample(i, seconds_offset=float(i), gpu_util=0.0)
        for i in range(MIN_SAMPLES_FOR_ANALYSIS + 2)
    ]
    energy = compute_energy(samples)
    findings = analyze_efficiency(samples, hardware_snapshot, energy)
    idle = [f for f in findings if f.category == "idle_periods"]
    assert idle
    assert "100%" in idle[0].message  # every sample was 0% util -> fully idle
