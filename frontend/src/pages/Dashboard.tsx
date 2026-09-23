import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { CostPanel, EnergyPanel, EnvironmentalPanel } from "../components/CalculationsPanels";
import { EfficiencyPanel } from "../components/EfficiencyPanel";
import { HardwarePanel } from "../components/HardwarePanel";
import { MetricChart } from "../components/MetricChart";
import { SessionControls } from "../components/SessionControls";
import type {
  ConfigResponse,
  EfficiencyAnalysis,
  GPUInfo,
  SessionCalculations,
  SessionInfo,
  SessionSummary,
  SystemInfo,
  TelemetrySample,
} from "../types";

const MAX_SAMPLES_KEPT = 180;
const TELEMETRY_POLL_MS = 1000;
const CALC_POLL_MS = 3000;
const STATUS_POLL_MS = 2000;
const HARDWARE_POLL_MS = 4000;

export function Dashboard() {
  const [gpu, setGpu] = useState<GPUInfo | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [config, setConfig] = useState<ConfigResponse | null>(null);

  const [session, setSession] = useState<SessionInfo | null>(null);
  const [finishedSummary, setFinishedSummary] = useState<SessionSummary | null>(null);
  const [samples, setSamples] = useState<TelemetrySample[]>([]);
  const [calc, setCalc] = useState<SessionCalculations | null>(null);
  const [efficiency, setEfficiency] = useState<EfficiencyAnalysis | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Initial load: static-ish hardware/config, and resume an already-running
  // session if one exists (e.g. the page was reloaded mid-session).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [g, s, c] = await Promise.all([
          api.getGpuInfo(),
          api.getSystemInfo(),
          api.getConfig(),
        ]);
        if (!cancelled) {
          setGpu(g);
          setSystem(s);
          setConfig(c);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
      try {
        const current = await api.getCurrentSession();
        if (!cancelled) setSession(current);
      } catch {
        // no active session - normal, not an error
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Hardware panel stays live regardless of whether a session is running.
  useEffect(() => {
    const id = window.setInterval(async () => {
      try {
        const [g, s] = await Promise.all([api.getGpuInfo(), api.getSystemInfo()]);
        setGpu(g);
        setSystem(s);
      } catch {
        // transient - keep showing the last good reading
      }
    }, HARDWARE_POLL_MS);
    return () => window.clearInterval(id);
  }, []);

  // Live telemetry + calculations + efficiency, only while a session runs.
  useEffect(() => {
    if (!session || session.status !== "running") return;
    const sid = session.session_id;
    let sinceIndex = 0;
    setSamples([]);

    const telemetryTimer = window.setInterval(async () => {
      try {
        const newSamples = await api.getSessionTelemetry(sid, sinceIndex);
        if (newSamples.length > 0) {
          sinceIndex = newSamples[newSamples.length - 1].sample_index + 1;
          setSamples((prev) => [...prev, ...newSamples].slice(-MAX_SAMPLES_KEPT));
        }
      } catch {
        // transient network hiccup - next tick will retry
      }
    }, TELEMETRY_POLL_MS);

    const calcTimer = window.setInterval(async () => {
      try {
        const [c, e] = await Promise.all([
          api.getSessionCalculations(sid),
          api.getSessionEfficiency(sid),
        ]);
        setCalc(c);
        setEfficiency(e);
      } catch {
        // transient
      }
    }, CALC_POLL_MS);

    const statusTimer = window.setInterval(async () => {
      try {
        setSession(await api.getSessionStatus(sid));
      } catch {
        // transient
      }
    }, STATUS_POLL_MS);

    return () => {
      window.clearInterval(telemetryTimer);
      window.clearInterval(calcTimer);
      window.clearInterval(statusTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.session_id, session?.status]);

  async function handleStart(workloadName: string, intervalSeconds: number, simulate: boolean) {
    setBusy(true);
    setError(null);
    try {
      const info = await api.startSession(workloadName, intervalSeconds, simulate);
      setSession(info);
      setSamples([]);
      setCalc(null);
      setEfficiency(null);
      setFinishedSummary(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleStop(outputCount?: number, outputUnit?: string) {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const summary = await api.stopSession(session.session_id, outputCount, outputUnit);
      setFinishedSummary(summary);
      setSession(null);
      const [c, e] = await Promise.all([
        api.getSessionCalculations(summary.session_id),
        api.getSessionEfficiency(summary.session_id),
      ]);
      setCalc(c);
      setEfficiency(e);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const series = (pick: (s: TelemetrySample) => number | null) =>
    samples.map((s) => ({ index: s.sample_index, value: pick(s) }));

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">Live GPU / workload monitoring</div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {session?.is_simulated && (
        <div className="simulation-banner">
          ⚠ Simulation mode - this session's telemetry is synthetically generated for
          demonstration and does not reflect real hardware behavior.
        </div>
      )}
      {finishedSummary?.is_simulated && !session && (
        <div className="simulation-banner">
          ⚠ Simulation mode - the last completed session used synthetic telemetry, not real
          measurements.
        </div>
      )}

      {finishedSummary && !session && (
        <div className="assumptions-note" style={{ marginBottom: 14 }}>
          Last completed: <strong>{finishedSummary.workload_name}</strong> —{" "}
          {finishedSummary.runtime_seconds.toFixed(1)}s, {finishedSummary.sample_count} samples.{" "}
          <Link to={`/history/${finishedSummary.session_id}`}>View in history &rarr;</Link>
        </div>
      )}

      <div className="grid grid-cols-2">
        <HardwarePanel gpu={gpu} system={system} />
        <SessionControls
          session={session}
          defaultInterval={config?.telemetry_interval_seconds ?? 1}
          gpu={gpu}
          onStart={handleStart}
          onStop={handleStop}
          busy={busy}
        />
      </div>

      <div className="page-subtitle" style={{ marginTop: 24, marginBottom: 8 }}>
        Live Telemetry
      </div>
      <div className="grid grid-cols-3">
        <MetricChart
          title="GPU Utilization"
          unit="%"
          data={series((s) => s.gpu.gpu_utilization_percent)}
          color="var(--cyan)"
          domain={[0, 100]}
        />
        <MetricChart
          title="GPU Power"
          unit="W"
          data={series((s) => s.gpu.power_draw_w)}
          color="var(--amber)"
        />
        <MetricChart
          title="GPU Temperature"
          unit="°C"
          data={series((s) => s.gpu.temperature_c)}
          color="var(--red)"
        />
        <MetricChart
          title="VRAM Used"
          unit="MB"
          data={series((s) => s.gpu.vram_used_mb)}
          color="var(--green)"
        />
        <MetricChart
          title="CPU Utilization"
          unit="%"
          data={series((s) => s.cpu_utilization_percent)}
          color="var(--cyan)"
          domain={[0, 100]}
        />
        <MetricChart
          title="RAM Used"
          unit="%"
          data={series((s) => s.ram_used_percent)}
          color="var(--green)"
          domain={[0, 100]}
        />
      </div>

      <div className="page-subtitle" style={{ marginTop: 24, marginBottom: 8 }}>
        Energy, Cost &amp; Environmental Impact
      </div>
      <div className="grid grid-cols-3">
        <EnergyPanel calc={calc} />
        <CostPanel calc={calc} />
        <EnvironmentalPanel calc={calc} />
      </div>

      <div style={{ marginTop: 24 }}>
        <EfficiencyPanel analysis={efficiency} />
      </div>
    </div>
  );
}
