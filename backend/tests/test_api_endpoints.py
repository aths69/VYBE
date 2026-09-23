"""Section 25: API endpoints - request validation and error handling
(Section 18/21), independent of session lifecycle."""


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_gpu_info_always_has_available_flag(client):
    # Must succeed and degrade gracefully whether or not this machine has an
    # NVIDIA GPU (Section 3/21) - the shape is what's under test, not a
    # specific hardware result.
    resp = client.get("/api/gpu/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "available" in body
    assert "source" in body


def test_system_info_shape(client):
    resp = client.get("/api/system/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "cpu" in body and "memory" in body and "os" in body


def test_detect_combines_gpu_and_system(client):
    resp = client.get("/api/detect")
    assert resp.status_code == 200
    body = resp.json()
    assert "gpu" in body and "system" in body


def test_config_reflects_env_defaults(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["currency"] == "INR"
    assert body["electricity_rate"] == 10.0
    assert body["carbon_intensity_kg_per_kwh"] == 0.7


def test_start_session_rejects_empty_workload_name(client):
    resp = client.post("/api/sessions/start", json={"workload_name": ""})
    assert resp.status_code == 422


def test_start_session_rejects_out_of_range_interval(client):
    resp = client.post(
        "/api/sessions/start", json={"workload_name": "x", "interval_seconds": 0}
    )
    assert resp.status_code == 422

    resp2 = client.post(
        "/api/sessions/start", json={"workload_name": "x", "interval_seconds": 61}
    )
    assert resp2.status_code == 422


def test_unknown_session_returns_404_across_endpoints(client):
    fake_id = "no-such-session-id"
    assert client.get(f"/api/sessions/{fake_id}").status_code == 404
    assert client.get(f"/api/sessions/{fake_id}/detail").status_code == 404
    assert client.get(f"/api/sessions/{fake_id}/telemetry").status_code == 404
    assert client.get(f"/api/sessions/{fake_id}/calculations").status_code == 404
    assert client.get(f"/api/sessions/{fake_id}/efficiency").status_code == 404
    assert client.get(f"/api/sessions/{fake_id}/report").status_code == 404
    assert client.delete(f"/api/sessions/{fake_id}").status_code == 404


def test_history_list_shape(client):
    resp = client.get("/api/sessions/history")
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body and "items" in body


def test_history_invalid_sort_by_rejected(client):
    resp = client.get("/api/sessions/history?sort_by=not_a_real_column")
    assert resp.status_code == 422


def test_compare_requires_at_least_two_ids(client):
    resp = client.get("/api/sessions/compare?session_ids=only-one")
    assert resp.status_code == 400


def test_compare_unknown_ids_returns_404_naming_them(client):
    resp = client.get("/api/sessions/compare?session_ids=a&session_ids=b")
    assert resp.status_code == 404
    assert "a" in resp.json()["detail"]
    assert "b" in resp.json()["detail"]
