import type { EfficiencyAnalysis } from "../types";
import { Badge } from "./Badge";

export function EfficiencyPanel({ analysis }: { analysis: EfficiencyAnalysis | null }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Efficiency Findings</span>
        <Badge kind="info">Heuristic</Badge>
      </div>
      {!analysis ? (
        <div className="panel-body-empty">No data yet</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {analysis.recommendations.map((rec, i) => (
            <div key={i} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
              <Badge kind={rec.severity === "warning" ? "warning" : "info"}>
                {rec.category.replaceAll("_", " ")}
              </Badge>
              <div style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 4 }}>
                {rec.message}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
