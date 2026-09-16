from datetime import datetime

from pydantic import BaseModel, Field


class GPUProcessInfo(BaseModel):
    pid: int
    process_name: str | None = None
    gpu_memory_used_mb: float | None = None
    gpu_utilization_percent: float | None = None
    utilization_available: bool = False


class GPUInfo(BaseModel):
    available: bool
    source: str  # "nvml" | "nvidia-smi" | "unavailable"
    error: str | None = None

    name: str | None = None
    driver_version: str | None = None
    cuda_version: str | None = None
    uuid: str | None = None

    vram_total_mb: float | None = None
    vram_used_mb: float | None = None
    vram_free_mb: float | None = None

    gpu_utilization_percent: float | None = None
    memory_utilization_percent: float | None = None

    power_draw_w: float | None = None
    power_draw_available: bool = False

    power_limit_w: float | None = None
    power_limit_available: bool = False
    power_limit_note: str | None = None

    temperature_c: float | None = None

    processes: list[GPUProcessInfo] = []
    process_utilization_available: bool = False


class CPUInfo(BaseModel):
    model: str | None = None
    physical_cores: int | None = None
    logical_cores: int | None = None
    current_utilization_percent: float | None = None


class MemoryInfo(BaseModel):
    total_mb: float
    available_mb: float
    used_mb: float
    used_percent: float


class OSInfo(BaseModel):
    system: str
    release: str
    version: str
    pretty_name: str | None = None
    machine: str


class SystemInfo(BaseModel):
    os: OSInfo
    cpu: CPUInfo
    memory: MemoryInfo


class DetectionResponse(BaseModel):
    gpu: GPUInfo
    system: SystemInfo


class GPUSample(BaseModel):
    """Lightweight per-poll GPU reading used by the telemetry loop.

    Omits static fields (name, driver/cuda version, uuid, power cap) that
    don't change during a session and are already reported by /api/gpu/info.
    """

    available: bool
    error: str | None = None

    gpu_utilization_percent: float | None = None
    memory_utilization_percent: float | None = None
    vram_used_mb: float | None = None
    power_draw_w: float | None = None
    temperature_c: float | None = None

    processes: list[GPUProcessInfo] = []
    process_utilization_available: bool = False


class TelemetrySample(BaseModel):
    sample_index: int
    timestamp: datetime
    gpu: GPUSample
    cpu_utilization_percent: float | None = None
    ram_used_percent: float | None = None
    ram_used_mb: float | None = None


class StartSessionRequest(BaseModel):
    workload_name: str = Field(..., min_length=1, max_length=200)
    interval_seconds: float | None = Field(default=None, gt=0, le=60)


class StopSessionRequest(BaseModel):
    """Optional useful-output count for this run (Section 11's "yield").

    Only known once the workload finishes, so it's supplied at stop time,
    not start time - e.g. "processed 500 images" or "12 training epochs".
    """

    useful_output_count: int | None = Field(default=None, ge=1)
    useful_output_unit: str | None = Field(default=None, max_length=50)


class SessionInfo(BaseModel):
    session_id: str
    workload_name: str
    status: str  # "running" | "stopped"
    start_time: datetime
    end_time: datetime | None = None
    interval_seconds: float
    sample_count: int
    gpu_available: bool


class SessionSummary(SessionInfo):
    runtime_seconds: float
    useful_output_count: int | None = None
    useful_output_unit: str | None = None


class EnergyResult(BaseModel):
    label: str = "CALCULATED"

    total_energy_wh: float
    total_energy_kwh: float
    average_power_w: float | None = None
    peak_power_w: float | None = None

    sample_count: int
    runtime_seconds: float
    intervals_used: int
    intervals_skipped: int
    coverage_seconds: float
    warnings: list[str] = []


class CostResult(BaseModel):
    label: str = "CALCULATED"
    currency: str
    rate_per_kwh: float
    total_cost: float


class CarbonResult(BaseModel):
    label: str = "ESTIMATED"
    carbon_intensity_kg_per_kwh: float
    estimated_kg_co2e: float
    note: str


class WaterResult(BaseModel):
    label: str = "ESTIMATED"
    enabled: bool
    wue_l_per_kwh: float | None = None
    estimated_liters: float | None = None
    note: str


class YieldMetrics(BaseModel):
    """Cost/energy per useful output (Section 11) - the project's "yield"."""

    label: str = "CALCULATED"
    useful_output_count: int
    useful_output_unit: str
    energy_per_unit_wh: float
    cost_per_unit: float
    energy_per_1000_units_kwh: float
    cost_per_1000_units: float


class SessionCalculations(BaseModel):
    session_id: str
    energy: EnergyResult
    cost: CostResult
    carbon: CarbonResult
    water: WaterResult
    yield_metrics: YieldMetrics | None = None


class SessionHardwareSnapshot(BaseModel):
    """Static hardware facts captured once at session start (Section 19)."""

    gpu_name: str | None = None
    gpu_driver_version: str | None = None
    gpu_cuda_version: str | None = None
    gpu_vram_total_mb: float | None = None
    gpu_power_limit_w: float | None = None
    cpu_model: str | None = None
    cpu_physical_cores: int | None = None
    cpu_logical_cores: int | None = None
    ram_total_mb: float
    os_pretty_name: str | None = None


class SessionListItem(BaseModel):
    session_id: str
    workload_name: str
    status: str
    start_time: datetime
    end_time: datetime | None = None
    runtime_seconds: float
    sample_count: int
    gpu_available: bool
    total_energy_kwh: float | None = None
    total_cost: float | None = None
    currency: str | None = None


class SessionListResponse(BaseModel):
    total: int
    items: list[SessionListItem]


class SessionDetail(BaseModel):
    session_id: str
    workload_name: str
    status: str
    start_time: datetime
    end_time: datetime | None = None
    interval_seconds: float
    runtime_seconds: float
    sample_count: int
    gpu_available: bool
    useful_output_count: int | None = None
    useful_output_unit: str | None = None
    hardware: SessionHardwareSnapshot | None = None
    calculations: SessionCalculations | None = None


class ConfigResponse(BaseModel):
    """Current effective defaults (Section 20) - read-only. These come from
    environment variables, not this API, so there is no write endpoint; a
    per-request override (e.g. /calculations?rate_per_kwh=...) is how a
    caller changes them for one calculation without restarting the server.
    """

    telemetry_interval_seconds: float
    electricity_rate: float
    currency: str
    carbon_intensity_kg_per_kwh: float
    water_wue_l_per_kwh: float
    water_estimation_enabled: bool


class Recommendation(BaseModel):
    """A heuristic finding (Section 10) - a hypothesis, never a diagnosis."""

    category: str
    severity: str  # "info" | "warning"
    message: str


class EfficiencyAnalysis(BaseModel):
    session_id: str
    sample_count: int
    recommendations: list[Recommendation]
