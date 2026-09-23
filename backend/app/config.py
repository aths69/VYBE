"""Central, environment-driven configuration (CLAUDE.md Sections 20 & 31).

All settings must have a sensible default but be overridable via environment
variables, so the same image/checkout runs unmodified on a laptop, a lab
server, or a container. Later phases (telemetry interval, electricity rate,
currency, carbon intensity, water-estimation assumptions) extend this same
Settings class rather than introducing ad-hoc config elsewhere.
"""

import os
from dataclasses import dataclass
from pathlib import Path


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # Bind to 0.0.0.0 by default so the API is reachable from other machines
    # on a network (lab server, GPU rack), not only from localhost.
    host: str = _env_str("VYBE_HOST", "0.0.0.0")
    port: int = _env_int("VYBE_PORT", 8000)

    # All persisted data (SQLite DB, generated reports) lives under this
    # directory so it maps cleanly onto a Docker volume later. Never hardcode
    # a file path outside of this directory.
    data_dir: Path = Path(_env_str("VYBE_DATA_DIR", "./data")).resolve()

    # Default polling interval for telemetry sessions (Section 4B/20).
    # Overridable per-session via the start-session API request body.
    telemetry_interval_seconds: float = _env_float(
        "VYBE_TELEMETRY_INTERVAL_SECONDS", 1.0
    )

    # Cost/carbon/water assumptions (Sections 7-9, 20). All overridable
    # per-request via the calculations API - these are just the defaults
    # shown when the caller doesn't supply their own.
    electricity_rate: float = _env_float("VYBE_ELECTRICITY_RATE", 10.0)
    currency: str = _env_str("VYBE_CURRENCY", "INR")
    carbon_intensity_kg_per_kwh: float = _env_float(
        "VYBE_CARBON_INTENSITY_KG_PER_KWH", 0.7
    )
    water_wue_l_per_kwh: float = _env_float("VYBE_WATER_WUE_L_PER_KWH", 1.8)
    water_estimation_enabled: bool = _env_bool("VYBE_WATER_ESTIMATION_ENABLED", True)

    # "*" by default so the dashboard works when opened from another machine
    # on the network (Section 31), not just localhost. No cookies/auth are in
    # play, so a permissive CORS policy carries no meaningful risk here
    # (Section 23: don't overengineer security for a college prototype).
    cors_origins: str = _env_str("VYBE_CORS_ORIGINS", "*")

    # Set only in the Docker image (Section 31): the built frontend's static
    # files, mounted by main.py so one container serves both the API and the
    # dashboard on one port. Empty/unset in local dev, where the frontend
    # runs separately via `npm run dev`.
    static_dir: str = _env_str("VYBE_STATIC_DIR", "")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
