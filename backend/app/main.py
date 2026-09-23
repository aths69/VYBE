from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db.engine import create_tables
from app.hardware.gpu import detect_gpu
from app.hardware.system import detect_system
from app.routers.calculations import router as calculations_router
from app.routers.comparison import router as comparison_router
from app.routers.config import router as config_router
from app.routers.efficiency import router as efficiency_router
from app.routers.history import router as history_router
from app.routers.report import router as report_router
from app.routers.sessions import router as sessions_router
from app.schemas import DetectionResponse, GPUInfo, SystemInfo

app = FastAPI(
    title="VYBE - Virtual Yield & Benchmarking Engine",
    description="GPU / data-center resource intelligence platform",
    version="0.1.0",
)

_cors_origins = (
    ["*"] if settings.cors_origins == "*" else settings.cors_origins.split(",")
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()

# Route order matters here: history_router's literal "/api/sessions/history"
# and comparison_router's literal "/api/sessions/compare" must be registered
# before sessions_router's parameterized "/api/sessions/{session_id}", or
# FastAPI would match "history"/"compare" as a session_id and never reach
# those endpoints.
app.include_router(history_router)
app.include_router(comparison_router)
app.include_router(sessions_router)
app.include_router(calculations_router)
app.include_router(efficiency_router)
app.include_router(config_router)
app.include_router(report_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/gpu/info", response_model=GPUInfo)
def gpu_info() -> GPUInfo:
    return detect_gpu()


@app.get("/api/system/info", response_model=SystemInfo)
def system_info() -> SystemInfo:
    return detect_system()


@app.get("/api/detect", response_model=DetectionResponse)
def detect() -> DetectionResponse:
    return DetectionResponse(gpu=detect_gpu(), system=detect_system())


# Section 31 (Docker path): the built frontend, mounted last so it never
# shadows the /api/* routes above - Starlette dispatches to the first
# registered route that matches a path, and a root-level mount matches
# everything. Unset/absent in local dev, where the frontend runs separately
# via `npm run dev` (Vite on its own port).
if settings.static_dir and Path(settings.static_dir).is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")
