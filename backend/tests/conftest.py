"""Shared test fixtures (Section 25).

The VYBE_DATA_DIR env var must be set to an isolated temp directory BEFORE
`app.config`/`app.db.engine`/`app.main` are imported anywhere - those modules
build a module-level Settings()/engine from it at import time, and we must
never let the test suite read or write the real dev database at
backend/data/vybe.db.
"""

import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="vybe-test-")
os.environ["VYBE_DATA_DIR"] = _TEST_DATA_DIR
os.environ.setdefault("VYBE_ELECTRICITY_RATE", "10.0")
os.environ.setdefault("VYBE_CURRENCY", "INR")
os.environ.setdefault("VYBE_CARBON_INTENSITY_KG_PER_KWH", "0.7")
os.environ.setdefault("VYBE_WATER_WUE_L_PER_KWH", "1.8")
os.environ.setdefault("VYBE_WATER_ESTIMATION_ENABLED", "true")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas import GPUSample, SessionHardwareSnapshot, TelemetrySample  # noqa: E402
from app.telemetry.manager import session_manager  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_TEST_DATA_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _no_leaked_session():
    """SessionManager is a process-wide singleton - stop anything left
    running after a test so the next test doesn't hit SessionAlreadyRunning."""
    yield
    active = session_manager._active  # test-only introspection, not public API
    if active is not None:
        try:
            session_manager.stop(active.id)
        except Exception:
            pass


def make_sample(
    index: int,
    *,
    seconds_offset: float = 0.0,
    gpu_available: bool = True,
    gpu_util: float | None = 50.0,
    mem_util: float | None = 30.0,
    vram_mb: float | None = 1000.0,
    power_w: float | None = 20.0,
    temp_c: float | None = 50.0,
    cpu_percent: float | None = 40.0,
    ram_percent: float | None = 35.0,
    ram_mb: float | None = 5000.0,
    base_time: datetime | None = None,
) -> TelemetrySample:
    """Build a TelemetrySample without needing real hardware - used to unit
    test calculations/analysis against known, hand-computable inputs."""
    base = base_time or datetime(2026, 1, 1, tzinfo=timezone.utc)
    return TelemetrySample(
        sample_index=index,
        timestamp=base + timedelta(seconds=seconds_offset),
        gpu=GPUSample(
            available=gpu_available,
            gpu_utilization_percent=gpu_util if gpu_available else None,
            memory_utilization_percent=mem_util if gpu_available else None,
            vram_used_mb=vram_mb if gpu_available else None,
            power_draw_w=power_w if gpu_available else None,
            temperature_c=temp_c if gpu_available else None,
        ),
        cpu_utilization_percent=cpu_percent,
        ram_used_percent=ram_percent,
        ram_used_mb=ram_mb,
    )


@pytest.fixture
def hardware_snapshot() -> SessionHardwareSnapshot:
    return SessionHardwareSnapshot(
        gpu_name="Test GPU",
        gpu_driver_version="000.00",
        gpu_cuda_version="0.0",
        gpu_vram_total_mb=6144.0,
        gpu_power_limit_w=35.0,
        cpu_model="Test CPU",
        cpu_physical_cores=8,
        cpu_logical_cores=16,
        ram_total_mb=16384.0,
        os_pretty_name="Test OS",
    )
