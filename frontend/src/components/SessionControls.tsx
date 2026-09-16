import { useState } from "react";
import type { SessionInfo } from "../types";

export function SessionControls({
  session,
  defaultInterval,
  onStart,
  onStop,
  busy,
}: {
  session: SessionInfo | null;
  defaultInterval: number;
  onStart: (workloadName: string, intervalSeconds: number) => Promise<void>;
  onStop: (outputCount?: number, outputUnit?: string) => Promise<void>;
  busy: boolean;
}) {
  const [workloadName, setWorkloadName] = useState("");
  const [interval, setInterval_] = useState(String(defaultInterval));
  const [outputCount, setOutputCount] = useState("");
  const [outputUnit, setOutputUnit] = useState("images");

  const running = session?.status === "running";

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <span className={`status-dot ${running ? "live" : "idle"}`} />
          Session Control
        </span>
      </div>

      {!running ? (
        <div className="controls-row">
          <div className="field" style={{ flex: 2 }}>
            <label>Workload name</label>
            <input
              type="text"
              placeholder="e.g. ResNet training"
              value={workloadName}
              onChange={(e) => setWorkloadName(e.target.value)}
            />
          </div>
          <div className="field" style={{ width: 110 }}>
            <label>Interval (s)</label>
            <input
              type="number"
              min="0.1"
              step="0.5"
              value={interval}
              onChange={(e) => setInterval_(e.target.value)}
            />
          </div>
          <button
            className="primary"
            disabled={busy || !workloadName.trim()}
            onClick={() => onStart(workloadName.trim(), Number(interval) || defaultInterval)}
          >
            Start Session
          </button>
        </div>
      ) : (
        <>
          <div className="metric-row">
            <span className="metric-row-label">Workload</span>
            <span className="metric-row-value">{session.workload_name}</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Samples collected</span>
            <span className="metric-row-value">{session.sample_count}</span>
          </div>
          <div className="controls-row" style={{ marginTop: 10 }}>
            <div className="field" style={{ width: 130 }}>
              <label>Output count (optional)</label>
              <input
                type="number"
                min="1"
                placeholder="e.g. 500"
                value={outputCount}
                onChange={(e) => setOutputCount(e.target.value)}
              />
            </div>
            <div className="field" style={{ width: 130 }}>
              <label>Unit</label>
              <input
                type="text"
                value={outputUnit}
                onChange={(e) => setOutputUnit(e.target.value)}
              />
            </div>
            <button
              className="danger"
              disabled={busy}
              onClick={() =>
                onStop(
                  outputCount ? Number(outputCount) : undefined,
                  outputCount ? outputUnit : undefined,
                )
              }
            >
              Stop Session
            </button>
          </div>
        </>
      )}
    </div>
  );
}
