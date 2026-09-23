"""Section 25 edge cases, with a focus on Section 21's "unavailable GPU
metrics" and Section 3's "never invent data to fill a gap"."""

from datetime import datetime, timezone

import pytest

from app.db import repository
from app.hardware import gpu as gpu_module
from app.reporting.generator import generate_report_html
from app.schemas import SessionSummary
from tests.conftest import make_sample


# ---------- GPU detection degrades gracefully when hardware is absent ----------


def test_detect_gpu_reports_unavailable_when_nvml_and_nvidia_smi_both_missing(monkeypatch):
    monkeypatch.setattr(gpu_module, "nvml", None)

    def _raise(*args, **kwargs):
        raise FileNotFoundError("nvidia-smi: command not found")

    monkeypatch.setattr(gpu_module.subprocess, "run", _raise)

    info = gpu_module.detect_gpu()
    assert info.available is False
    assert info.source == "unavailable"
    assert info.error is not None


def test_power_cap_regex_parses_real_nvidia_smi_table_format():
    # A trimmed real nvidia-smi table snippet (Section 0's confirmed quirk:
    # the cap is only recoverable from this human-readable table, not the
    # power.limit CSV field).
    sample_output = (
        "| N/A   47C    P0             17W /   35W |    401MiB /   6141MiB |"
    )
    match = gpu_module._POWER_CAP_RE.search(sample_output)
    assert match is not None
    assert float(match.group(1)) == 17.0
    assert float(match.group(2)) == 35.0


def test_power_cap_from_nvidia_smi_never_raises_on_missing_binary(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(gpu_module.subprocess, "run", _raise)
    cap, note = gpu_module._power_cap_from_nvidia_smi()
    assert cap is None
    assert note is not None


# ---------- a fully persisted session with GPU unavailable throughout ----------


def _build_all_gpu_unavailable_session(session_id: str = "edge-case-no-gpu"):
    samples = [
        make_sample(i, seconds_offset=float(i), gpu_available=False)
        for i in range(3)
    ]
    summary = SessionSummary(
        session_id=session_id,
        workload_name="no GPU on this box",
        status="stopped",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2026, 1, 1, 0, 0, 3, tzinfo=timezone.utc),
        interval_seconds=1.0,
        sample_count=len(samples),
        gpu_available=False,
        is_simulated=False,
        runtime_seconds=3.0,
        useful_output_count=None,
        useful_output_unit=None,
    )
    repository.save_completed_session(summary, samples, hardware=None)
    return session_id


def test_session_with_gpu_never_available_persists_without_inventing_data():
    session_id = _build_all_gpu_unavailable_session()

    detail = repository.get_session_detail(session_id)
    assert detail is not None
    assert detail.hardware is None  # never fabricated when nothing was captured
    assert detail.calculations is not None
    assert detail.calculations.energy.total_energy_wh == 0.0
    assert detail.calculations.energy.warnings  # explains why, doesn't hide it

    repository.delete_session(session_id)


def test_report_renders_metric_unavailable_instead_of_fabricating(client):
    session_id = _build_all_gpu_unavailable_session("edge-case-report")
    try:
        html = generate_report_html(session_id)
        assert html is not None
        assert "Metric unavailable on this hardware" in html
        assert "No hardware snapshot recorded" in html
    finally:
        repository.delete_session(session_id)


def test_report_via_api_404_for_unknown_session(client):
    resp = client.get("/api/sessions/totally-unknown/report")
    assert resp.status_code == 404


def test_report_via_api_409_while_session_still_running(client):
    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "report while running", "interval_seconds": 0.05, "simulate": True},
    ).json()

    resp = client.get(f"/api/sessions/{started['session_id']}/report")
    assert resp.status_code == 409

    client.post(f"/api/sessions/{started['session_id']}/stop")

    resp2 = client.get(f"/api/sessions/{started['session_id']}/report")
    assert resp2.status_code == 200
    assert "text/html" in resp2.headers["content-type"]

    client.delete(f"/api/sessions/{started['session_id']}")


# ---------- calculations endpoint per-request overrides (Section 7/8/9/20) ----------


def test_calculations_endpoint_honors_overrides_not_just_defaults(client):
    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "override check", "interval_seconds": 0.05, "simulate": True},
    ).json()
    session_id = started["session_id"]

    import time

    time.sleep(0.3)
    client.post(f"/api/sessions/{session_id}/stop")

    default_calc = client.get(f"/api/sessions/{session_id}/calculations").json()
    overridden = client.get(
        f"/api/sessions/{session_id}/calculations"
        "?rate_per_kwh=99&currency=USD&carbon_intensity_kg_per_kwh=0&water_enabled=false"
    ).json()

    assert overridden["cost"]["currency"] == "USD"
    assert overridden["cost"]["rate_per_kwh"] == 99
    assert overridden["carbon"]["estimated_kg_co2e"] == 0.0
    assert overridden["water"]["enabled"] is False
    assert overridden["cost"]["total_cost"] != default_calc["cost"]["total_cost"]

    client.delete(f"/api/sessions/{session_id}")


# ---------- comparison mixing simulated and real sessions ----------


def test_compare_warns_when_mixing_simulated_and_real_sessions(client):
    real_id = _build_all_gpu_unavailable_session("edge-case-real-for-compare")

    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "sim for compare", "interval_seconds": 0.05, "simulate": True},
    ).json()
    client.post(f"/api/sessions/{started['session_id']}/stop")

    try:
        resp = client.get(
            f"/api/sessions/compare?session_ids={real_id}&session_ids={started['session_id']}"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["warnings"]
        assert "mixes simulated" in body["warnings"][0]
    finally:
        repository.delete_session(real_id)
        client.delete(f"/api/sessions/{started['session_id']}")
