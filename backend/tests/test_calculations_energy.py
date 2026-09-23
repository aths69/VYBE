"""Section 25: energy calculation.

Energy is CALCULATED via trapezoidal integration of measured GPU power over
the *actual* elapsed time between samples (Section 6) - these tests verify
the arithmetic by hand, not just that it "runs".
"""

import pytest

from app.calculations.energy import compute_energy
from tests.conftest import make_sample


def test_empty_samples_returns_zero_with_warning():
    result = compute_energy([])
    assert result.total_energy_wh == 0.0
    assert result.total_energy_kwh == 0.0
    assert result.sample_count == 0
    assert result.average_power_w is None
    assert result.peak_power_w is None
    assert result.warnings


def test_single_sample_cannot_integrate():
    result = compute_energy([make_sample(0, power_w=20.0)])
    assert result.total_energy_wh == 0.0
    assert any("Fewer than 2 samples" in w for w in result.warnings)


def test_two_samples_known_trapezoidal_integration():
    # power 10W -> 20W over exactly 2 seconds: avg 15W * (2/3600)h = 1/120 Wh
    samples = [
        make_sample(0, seconds_offset=0.0, power_w=10.0),
        make_sample(1, seconds_offset=2.0, power_w=20.0),
    ]
    result = compute_energy(samples)
    assert result.total_energy_wh == pytest.approx(1 / 120)
    assert result.total_energy_kwh == pytest.approx(1 / 120 / 1000)
    assert result.average_power_w == 15.0
    assert result.peak_power_w == 20.0
    assert result.intervals_used == 1
    assert result.intervals_skipped == 0
    assert result.runtime_seconds == 2.0
    assert result.coverage_seconds == 2.0


def test_three_samples_sums_each_interval():
    samples = [
        make_sample(0, seconds_offset=0.0, power_w=10.0),
        make_sample(1, seconds_offset=1.0, power_w=30.0),
        make_sample(2, seconds_offset=2.0, power_w=10.0),
    ]
    result = compute_energy(samples)
    # interval 1: avg 20W * 1/3600 h ; interval 2: avg 20W * 1/3600 h
    expected_wh = (20 * 1 / 3600) + (20 * 1 / 3600)
    assert result.total_energy_wh == pytest.approx(expected_wh)
    assert result.intervals_used == 2
    assert result.peak_power_w == 30.0
    assert result.average_power_w == pytest.approx((10 + 30 + 10) / 3)


def test_gpu_unavailable_sample_skips_its_intervals():
    samples = [
        make_sample(0, seconds_offset=0.0, power_w=10.0),
        make_sample(1, seconds_offset=1.0, gpu_available=False),
        make_sample(2, seconds_offset=2.0, power_w=10.0),
    ]
    result = compute_energy(samples)
    # both intervals touch the unavailable sample -> both skipped
    assert result.intervals_used == 0
    assert result.intervals_skipped == 2
    assert result.total_energy_wh == 0.0
    assert any("excluded from the energy integration" in w for w in result.warnings)
    # average/peak power still computed from the one available reading
    assert result.average_power_w == 10.0
    assert result.peak_power_w == 10.0


def test_all_gpu_unavailable_reports_none_power():
    samples = [
        make_sample(0, seconds_offset=0.0, gpu_available=False),
        make_sample(1, seconds_offset=1.0, gpu_available=False),
    ]
    result = compute_energy(samples)
    assert result.average_power_w is None
    assert result.peak_power_w is None
    assert result.total_energy_wh == 0.0
    assert result.intervals_skipped == 1


def test_zero_or_negative_delta_t_is_skipped_not_divided_by_zero():
    samples = [
        make_sample(0, seconds_offset=5.0, power_w=10.0),
        make_sample(1, seconds_offset=5.0, power_w=20.0),  # duplicate timestamp
    ]
    result = compute_energy(samples)
    assert result.intervals_skipped == 1
    assert result.intervals_used == 0
    assert result.total_energy_wh == 0.0
