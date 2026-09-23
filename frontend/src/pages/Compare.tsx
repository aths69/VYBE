import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Badge } from "../components/Badge";
import type { SessionComparisonItem } from "../types";

type MetricRow = {
  label: string;
  badge: "measured" | "calculated" | "estimated";
  unit?: string;
  decimals?: number;
  lowerIsBetter?: boolean;
  value: (s: SessionComparisonItem) => number | null;
};

const ROWS: MetricRow[] = [
  { label: "Runtime", badge: "measured", unit: "s", decimals: 1, value: (s) => s.runtime_seconds },
  {
    label: "Average GPU utilization",
    badge: "measured",
    unit: "%",
    decimals: 1,
    lowerIsBetter: false,
    value: (s) => s.stats.average_gpu_utilization_percent,
  },
  {
    label: "Peak GPU utilization",
    badge: "measured",
    unit: "%",
    decimals: 1,
    value: (s) => s.stats.peak_gpu_utilization_percent,
  },
  {
    label: "Average power",
    badge: "measured",
    unit: "W",
    decimals: 1,
    value: (s) => s.energy.average_power_w,
  },
  {
    label: "Total energy",
    badge: "calculated",
    unit: "Wh",
    decimals: 4,
    lowerIsBetter: true,
    value: (s) => s.energy.total_energy_wh,
  },
  {
    label: "Electricity cost",
    badge: "calculated",
    decimals: 5,
    lowerIsBetter: true,
    value: (s) => s.cost.total_cost,
  },
  {
    label: "Carbon estimate",
    badge: "estimated",
    unit: "g CO2e",
    decimals: 3,
    lowerIsBetter: true,
    value: (s) => s.carbon.estimated_kg_co2e * 1000,
  },
  {
    label: "Energy per useful output",
    badge: "calculated",
    unit: "Wh/unit",
    decimals: 6,
    lowerIsBetter: true,
    value: (s) => s.yield_metrics?.energy_per_unit_wh ?? null,
  },
  {
    label: "Cost per useful output",
    badge: "calculated",
    decimals: 7,
    lowerIsBetter: true,
    value: (s) => s.yield_metrics?.cost_per_unit ?? null,
  },
];

export function Compare() {
  const [params] = useSearchParams();
  const [sessions, setSessions] = useState<SessionComparisonItem[] | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const ids = (params.get("ids") ?? "").split(",").filter(Boolean);

  useEffect(() => {
    if (ids.length < 2) {
      setError("Select at least 2 sessions from History to compare.");
      return;
    }
    (async () => {
      try {
        const res = await api.compareSessions(ids);
        setSessions(res.sessions);
        setWarnings(res.warnings);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.get("ids")]);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Session Comparison</div>
          <div className="page-subtitle">
            <Link to="/history">&larr; back to history</Link>
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {warnings.map((w) => (
        <div className="simulation-banner" key={w}>
          ⚠ {w}
        </div>
      ))}
      {!error && !sessions && <div className="panel-body-empty">Loading...</div>}

      {sessions && (
        <div className="panel" style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                {sessions.map((s) => (
                  <th key={s.session_id}>
                    <Link to={`/history/${s.session_id}`}>{s.workload_name}</Link>
                    {s.is_simulated && (
                      <span style={{ marginLeft: 6 }}>
                        <Badge kind="simulated">Simulated</Badge>
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => {
                const values = sessions.map((s) => row.value(s));
                const numeric = values.filter((v): v is number => v !== null);
                const best =
                  row.lowerIsBetter !== undefined && numeric.length > 1
                    ? row.lowerIsBetter
                      ? Math.min(...numeric)
                      : Math.max(...numeric)
                    : null;

                return (
                  <tr key={row.label}>
                    <td>
                      {row.label} <Badge kind={row.badge}>{row.badge}</Badge>
                    </td>
                    {sessions.map((s, i) => {
                      const v = values[i];
                      const isBest = best !== null && v === best;
                      return (
                        <td
                          key={s.session_id}
                          style={isBest ? { color: "var(--green)", fontWeight: 700 } : undefined}
                        >
                          {v === null ? "n/a" : `${v.toFixed(row.decimals ?? 2)}${row.unit ? ` ${row.unit}` : ""}`}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="assumptions-note">
            Highlighted (green) values mark the better-performing session for that metric where a
            clear "better" direction applies. Carbon and cost-per-output figures depend on each
            session's configured rate/currency/carbon-intensity assumptions at the time it was
            recorded.
          </div>
        </div>
      )}
    </div>
  );
}
