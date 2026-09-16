import type { SessionCalculations } from "../types";
import { Badge } from "./Badge";

export function EnergyPanel({ calc }: { calc: SessionCalculations | null }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Energy</span>
        <Badge kind="calculated">Calculated</Badge>
      </div>
      {!calc ? (
        <div className="panel-body-empty">No data yet</div>
      ) : (
        <>
          <div className="metric-row">
            <span className="metric-row-label">Total energy</span>
            <span className="metric-row-value">{calc.energy.total_energy_wh.toFixed(3)} Wh</span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Average power</span>
            <span className="metric-row-value">
              {calc.energy.average_power_w?.toFixed(1) ?? "n/a"} W
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Peak power</span>
            <span className="metric-row-value">
              {calc.energy.peak_power_w?.toFixed(1) ?? "n/a"} W
            </span>
          </div>
          {calc.energy.warnings.length > 0 && (
            <div className="assumptions-note">{calc.energy.warnings.join(" ")}</div>
          )}
        </>
      )}
    </div>
  );
}

export function CostPanel({ calc }: { calc: SessionCalculations | null }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Cost</span>
        <Badge kind="calculated">Calculated</Badge>
      </div>
      {!calc ? (
        <div className="panel-body-empty">No data yet</div>
      ) : (
        <>
          <div className="metric">
            <span className="metric-label">Estimated cost</span>
            <span className="metric-value">
              {calc.cost.currency} {calc.cost.total_cost.toFixed(4)}
            </span>
          </div>
          <div className="assumptions-note">
            Assumes {calc.cost.currency} {calc.cost.rate_per_kwh}/kWh
          </div>
          {calc.yield_metrics && (
            <div className="metric-row" style={{ marginTop: 8 }}>
              <span className="metric-row-label">
                Cost per {calc.yield_metrics.useful_output_unit}
              </span>
              <span className="metric-row-value">
                {calc.cost.currency} {calc.yield_metrics.cost_per_unit.toFixed(6)}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function EnvironmentalPanel({ calc }: { calc: SessionCalculations | null }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Environmental</span>
        <Badge kind="estimated">Estimated</Badge>
      </div>
      {!calc ? (
        <div className="panel-body-empty">No data yet</div>
      ) : (
        <>
          <div className="metric-row">
            <span className="metric-row-label">Carbon (CO2e)</span>
            <span className="metric-row-value">
              {(calc.carbon.estimated_kg_co2e * 1000).toFixed(2)} g
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-row-label">Water</span>
            <span className="metric-row-value">
              {calc.water.enabled
                ? `${calc.water.estimated_liters?.toFixed(4)} L`
                : "disabled"}
            </span>
          </div>
          <div className="assumptions-note">
            Assumes {calc.carbon.carbon_intensity_kg_per_kwh} kg CO2e/kWh grid intensity
            {calc.water.enabled ? `, ${calc.water.wue_l_per_kwh} L/kWh WUE` : ""}. Directional
            estimates only - not measurements.
          </div>
        </>
      )}
    </div>
  );
}
