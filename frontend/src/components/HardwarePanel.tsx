import type { GPUInfo, SystemInfo } from "../types";
import { Badge } from "./Badge";

export function HardwarePanel({
  gpu,
  system,
}: {
  gpu: GPUInfo | null;
  system: SystemInfo | null;
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Hardware</span>
        <Badge kind="measured">Measured</Badge>
      </div>

      {!gpu ? (
        <div className="panel-body-empty">Detecting GPU...</div>
      ) : !gpu.available ? (
        <div className="panel-body-empty">
          GPU unavailable{gpu.error ? `: ${gpu.error}` : ""}
        </div>
      ) : (
        <>
          <div className="metric-row">
            <span className="metric-row-label">GPU</span>
            <span className="metric-row-value">{gpu.name}</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Driver / CUDA</span>
            <span className="metric-row-value">
              {gpu.driver_version} / {gpu.cuda_version ?? "n/a"}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">VRAM</span>
            <span className="metric-row-value">
              {gpu.vram_used_mb?.toFixed(0)} / {gpu.vram_total_mb?.toFixed(0)} MB
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Temperature</span>
            <span className="metric-row-value">{gpu.temperature_c?.toFixed(0) ?? "n/a"} °C</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Power</span>
            <span className="metric-row-value">
              {gpu.power_draw_available ? `${gpu.power_draw_w?.toFixed(1)} W` : "unavailable"}
              {gpu.power_limit_available ? ` / ${gpu.power_limit_w?.toFixed(0)} W cap` : ""}
            </span>
          </div>
        </>
      )}

      {system && (
        <>
          <div className="metric-row">
            <span className="metric-row-label">CPU</span>
            <span className="metric-row-value">
              {system.cpu.model} ({system.cpu.physical_cores}c/{system.cpu.logical_cores}t)
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">RAM</span>
            <span className="metric-row-value">
              {(system.memory.used_mb / 1024).toFixed(1)} / {(system.memory.total_mb / 1024).toFixed(1)} GB
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">OS</span>
            <span className="metric-row-value">{system.os.pretty_name ?? system.os.system}</span>
          </div>
        </>
      )}
    </div>
  );
}
