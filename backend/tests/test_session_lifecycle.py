"""Section 25: session creation / lifecycle.

Uses simulate=True (Section 24) throughout so these tests exercise the real
start -> poll -> stop -> persist pipeline without depending on real NVIDIA
hardware being present on whatever machine runs the suite.
"""

import time


def test_start_session_returns_running_info(client):
    resp = client.post(
        "/api/sessions/start",
        json={"workload_name": "unit test workload", "interval_seconds": 0.05, "simulate": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"
    assert body["workload_name"] == "unit test workload"
    assert body["is_simulated"] is True
    assert body["gpu_available"] is True

    client.post(f"/api/sessions/{body['session_id']}/stop")


def test_cannot_start_second_session_while_one_running(client):
    first = client.post(
        "/api/sessions/start",
        json={"workload_name": "first", "interval_seconds": 0.05, "simulate": True},
    ).json()

    second = client.post(
        "/api/sessions/start",
        json={"workload_name": "second", "interval_seconds": 0.05, "simulate": True},
    )
    assert second.status_code == 409

    client.post(f"/api/sessions/{first['session_id']}/stop")


def test_stop_unknown_session_returns_404(client):
    resp = client.post("/api/sessions/does-not-exist/stop")
    assert resp.status_code == 404


def test_stop_persists_session_with_telemetry_and_calculations(client):
    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "lifecycle test", "interval_seconds": 0.05, "simulate": True},
    ).json()
    session_id = started["session_id"]

    time.sleep(0.3)  # let a handful of simulated samples accumulate

    stopped = client.post(
        f"/api/sessions/{session_id}/stop",
        json={"useful_output_count": 10, "useful_output_unit": "images"},
    )
    assert stopped.status_code == 200
    summary = stopped.json()
    assert summary["status"] == "stopped"
    assert summary["is_simulated"] is True
    assert summary["useful_output_count"] == 10
    assert summary["sample_count"] >= 1

    detail = client.get(f"/api/sessions/{session_id}/detail").json()
    assert detail["is_simulated"] is True
    assert detail["hardware"]["gpu_name"] == "Simulated NVIDIA GPU (Demo Mode)"
    assert detail["calculations"] is not None
    assert detail["calculations"]["energy"]["label"] == "CALCULATED"
    assert detail["calculations"]["yield_metrics"]["useful_output_count"] == 10

    telemetry = client.get(f"/api/sessions/{session_id}/telemetry?since_index=0").json()
    assert len(telemetry) == summary["sample_count"]
    assert all(sample["gpu"]["available"] for sample in telemetry)

    history = client.get("/api/sessions/history").json()
    assert any(item["session_id"] == session_id for item in history["items"])


def test_delete_running_session_is_rejected(client):
    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "cannot delete me yet", "interval_seconds": 0.05, "simulate": True},
    ).json()

    resp = client.delete(f"/api/sessions/{started['session_id']}")
    assert resp.status_code == 409

    client.post(f"/api/sessions/{started['session_id']}/stop")


def test_delete_completed_session_then_404_on_repeat(client):
    started = client.post(
        "/api/sessions/start",
        json={"workload_name": "delete me", "interval_seconds": 0.05, "simulate": True},
    ).json()
    client.post(f"/api/sessions/{started['session_id']}/stop")

    first_delete = client.delete(f"/api/sessions/{started['session_id']}")
    assert first_delete.status_code == 200
    assert first_delete.json()["deleted"] is True

    second_delete = client.delete(f"/api/sessions/{started['session_id']}")
    assert second_delete.status_code == 404
