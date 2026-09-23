import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge } from "../components/Badge";
import { CostPanel, EnergyPanel, EnvironmentalPanel } from "../components/CalculationsPanels";
import { EfficiencyPanel } from "../components/EfficiencyPanel";
import type { EfficiencyAnalysis, SessionDetail } from "../types";

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [efficiency, setEfficiency] = useState<EfficiencyAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const [d, e] = await Promise.all([
          api.getSessionDetail(id),
          api.getSessionEfficiency(id),
        ]);
        setDetail(d);
        setEfficiency(e);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, [id]);

  async function handleDelete() {
    if (!id || !confirm("Delete this session permanently?")) return;
    try {
      await api.deleteSession(id);
      navigate("/history");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (error) return <div className="error-banner">{error}</div>;
  if (!detail) return <div className="panel-body-empty">Loading...</div>;

  return (
    <div>
      {detail.is_simulated && (
        <div className="simulation-banner">
          ⚠ Simulation mode - this session's telemetry is synthetically generated for
          demonstration and does not reflect real hardware behavior.
        </div>
      )}
      <div className="page-header">
        <div>
          <div className="page-title">
            {detail.workload_name}
            {detail.is_simulated && (
              <span style={{ marginLeft: 10 }}>
                <Badge kind="simulated">Simulated</Badge>
              </span>
            )}
          </div>
          <div className="page-subtitle">
            <Link to="/history">&larr; back to history</Link>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className="primary"
            onClick={() => window.open(api.getReportUrl(id!), "_blank")}
            disabled={detail.status !== "stopped"}
          >
            Generate Report
          </button>
          <button className="danger" onClick={handleDelete}>
            Delete Session
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2">
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Session</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Status</span>
            <span className="metric-row-value">{detail.status}</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Start</span>
            <span className="metric-row-value">
              {new Date(detail.start_time + "Z").toLocaleString()}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Runtime</span>
            <span className="metric-row-value">{detail.runtime_seconds.toFixed(1)} s</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Samples</span>
            <span className="metric-row-value">{detail.sample_count}</span>
          </div>
          {detail.useful_output_count && (
            <div className="metric-row">
              <span className="metric-row-label">Useful output</span>
              <span className="metric-row-value">
                {detail.useful_output_count} {detail.useful_output_unit}
              </span>
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Hardware Snapshot</span>
            <Badge kind={detail.is_simulated ? "simulated" : "measured"}>
              {detail.is_simulated ? "Simulated" : "Measured"}
            </Badge>
          </div>
          {!detail.hardware ? (
            <div className="panel-body-empty">No hardware snapshot recorded</div>
          ) : (
            <>
              <div className="metric-row">
                <span className="metric-row-label">GPU</span>
                <span className="metric-row-value">{detail.hardware.gpu_name ?? "n/a"}</span>
              </div>
              <div className="metric-row">
                <span className="metric-row-label">VRAM total</span>
                <span className="metric-row-value">
                  {detail.hardware.gpu_vram_total_mb?.toFixed(0) ?? "n/a"} MB
                </span>
              </div>
              <div className="metric-row">
                <span className="metric-row-label">CPU</span>
                <span className="metric-row-value">{detail.hardware.cpu_model ?? "n/a"}</span>
              </div>
              <div className="metric-row">
                <span className="metric-row-label">RAM total</span>
                <span className="metric-row-value">
                  {(detail.hardware.ram_total_mb / 1024).toFixed(1)} GB
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="page-subtitle" style={{ marginTop: 24, marginBottom: 8 }}>
        Energy, Cost &amp; Environmental Impact
      </div>
      <div className="grid grid-cols-3">
        <EnergyPanel calc={detail.calculations} />
        <CostPanel calc={detail.calculations} />
        <EnvironmentalPanel calc={detail.calculations} />
      </div>

      <div style={{ marginTop: 24 }}>
        <EfficiencyPanel analysis={efficiency} />
      </div>
    </div>
  );
}
