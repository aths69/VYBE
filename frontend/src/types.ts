// Mirrors backend/app/schemas.py. Kept to the fields the dashboard actually
// uses - not a 1:1 transcription of every backend field.

export interface GPUProcessInfo {
  pid: number;
  process_name: string | null;
  gpu_memory_used_mb: number | null;
  gpu_utilization_percent: number | null;
  utilization_available: boolean;
}

export interface GPUInfo {
  available: boolean;
  source: string;
  error: string | null;
  name: string | null;
  driver_version: string | null;
  cuda_version: string | null;
  vram_total_mb: number | null;
  vram_used_mb: number | null;
  gpu_utilization_percent: number | null;
  memory_utilization_percent: number | null;
  power_draw_w: number | null;
  power_draw_available: boolean;
  power_limit_w: number | null;
  power_limit_available: boolean;
  temperature_c: number | null;
  processes: GPUProcessInfo[];
  process_utilization_available: boolean;
}

export interface CPUInfo {
  model: string | null;
  physical_cores: number | null;
  logical_cores: number | null;
  current_utilization_percent: number | null;
}

export interface MemoryInfo {
  total_mb: number;
  available_mb: number;
  used_mb: number;
  used_percent: number;
}

export interface OSInfo {
  system: string;
  release: string;
  pretty_name: string | null;
  machine: string;
}

export interface SystemInfo {
  os: OSInfo;
  cpu: CPUInfo;
  memory: MemoryInfo;
}

export interface GPUSample {
  available: boolean;
  error: string | null;
  gpu_utilization_percent: number | null;
  memory_utilization_percent: number | null;
  vram_used_mb: number | null;
  power_draw_w: number | null;
  temperature_c: number | null;
  processes: GPUProcessInfo[];
  process_utilization_available: boolean;
}

export interface TelemetrySample {
  sample_index: number;
  timestamp: string;
  gpu: GPUSample;
  cpu_utilization_percent: number | null;
  ram_used_percent: number | null;
  ram_used_mb: number | null;
}

export type SessionStatus = "running" | "stopped";

export interface SessionInfo {
  session_id: string;
  workload_name: string;
  status: SessionStatus;
  start_time: string;
  end_time: string | null;
  interval_seconds: number;
  sample_count: number;
  gpu_available: boolean;
}

export interface SessionSummary extends SessionInfo {
  runtime_seconds: number;
  useful_output_count: number | null;
  useful_output_unit: string | null;
}

export interface EnergyResult {
  label: "CALCULATED";
  total_energy_wh: number;
  total_energy_kwh: number;
  average_power_w: number | null;
  peak_power_w: number | null;
  sample_count: number;
  runtime_seconds: number;
  intervals_used: number;
  intervals_skipped: number;
  coverage_seconds: number;
  warnings: string[];
}

export interface CostResult {
  label: "CALCULATED";
  currency: string;
  rate_per_kwh: number;
  total_cost: number;
}

export interface CarbonResult {
  label: "ESTIMATED";
  carbon_intensity_kg_per_kwh: number;
  estimated_kg_co2e: number;
  note: string;
}

export interface WaterResult {
  label: "ESTIMATED";
  enabled: boolean;
  wue_l_per_kwh: number | null;
  estimated_liters: number | null;
  note: string;
}

export interface YieldMetrics {
  label: "CALCULATED";
  useful_output_count: number;
  useful_output_unit: string;
  energy_per_unit_wh: number;
  cost_per_unit: number;
  energy_per_1000_units_kwh: number;
  cost_per_1000_units: number;
}

export interface SessionCalculations {
  session_id: string;
  energy: EnergyResult;
  cost: CostResult;
  carbon: CarbonResult;
  water: WaterResult;
  yield_metrics: YieldMetrics | null;
}

export interface SessionHardwareSnapshot {
  gpu_name: string | null;
  gpu_driver_version: string | null;
  gpu_cuda_version: string | null;
  gpu_vram_total_mb: number | null;
  gpu_power_limit_w: number | null;
  cpu_model: string | null;
  cpu_physical_cores: number | null;
  cpu_logical_cores: number | null;
  ram_total_mb: number;
  os_pretty_name: string | null;
}

export interface SessionListItem {
  session_id: string;
  workload_name: string;
  status: SessionStatus;
  start_time: string;
  end_time: string | null;
  runtime_seconds: number;
  sample_count: number;
  gpu_available: boolean;
  total_energy_kwh: number | null;
  total_cost: number | null;
  currency: string | null;
}

export interface SessionListResponse {
  total: number;
  items: SessionListItem[];
}

export interface SessionDetail {
  session_id: string;
  workload_name: string;
  status: SessionStatus;
  start_time: string;
  end_time: string | null;
  interval_seconds: number;
  runtime_seconds: number;
  sample_count: number;
  gpu_available: boolean;
  useful_output_count: number | null;
  useful_output_unit: string | null;
  hardware: SessionHardwareSnapshot | null;
  calculations: SessionCalculations | null;
}

export interface Recommendation {
  category: string;
  severity: "info" | "warning";
  message: string;
}

export interface EfficiencyAnalysis {
  session_id: string;
  sample_count: number;
  recommendations: Recommendation[];
}

export interface ConfigResponse {
  telemetry_interval_seconds: number;
  electricity_rate: number;
  currency: string;
  carbon_intensity_kg_per_kwh: number;
  water_wue_l_per_kwh: number;
  water_estimation_enabled: boolean;
}
