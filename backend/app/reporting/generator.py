"""Report generation (Section 16).

Renders a self-contained, printable HTML report for one completed session,
reusing the same repository/calculation/efficiency code paths as the API and
dashboard - a report can never disagree with the live UI about a number.
Intended to be exported to PDF via the browser's own print dialog; no PDF
library is introduced for this (Section 22/26: avoid unnecessary
infrastructure for a college prototype).
"""

import html
from datetime import datetime, timezone

from app.analysis.efficiency import analyze_efficiency
from app.analysis.stats import compute_telemetry_stats
from app.calculations.energy import compute_energy
from app.db import repository
from app.schemas import Recommendation, SessionCalculations, SessionDetail


def _fmt(value: float | None, decimals: int = 1, unit: str = "") -> str:
    if value is None:
        return "Metric unavailable on this hardware"
    return f"{value:.{decimals}f}{unit}"


def _esc(value: str | None) -> str:
    return html.escape(value) if value is not None else "n/a"


def _measured_badge(is_simulated: bool) -> str:
    """Section 24: a simulated session's hardware/GPU/power numbers are
    synthetic, not measured - swap the badge so a report can never present
    demo-mode data as if it came from real telemetry."""
    if is_simulated:
        return '<span class="badge badge-simulated">Simulated</span>'
    return '<span class="badge badge-measured">Measured</span>'


def generate_report_html(session_id: str) -> str | None:
    detail: SessionDetail | None = repository.get_session_detail(session_id)
    if detail is None:
        return None

    samples = repository.get_telemetry(session_id) or []
    stats = compute_telemetry_stats(samples)
    energy = compute_energy(samples)
    recommendations = analyze_efficiency(samples, detail.hardware, energy)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>VYBE Report - {_esc(detail.workload_name)}</title>
<style>
  :root {{
    --bg: #ffffff; --panel: #f6f8fa; --border: #d8dee5;
    --text: #1a2230; --text-dim: #55647a; --text-faint: #8898ab;
    --cyan: #0e7c86; --green: #1a8f5c; --amber: #a5680a; --red: #b8342f; --purple: #7a3aab;
    padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px);
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px 40px 60px; background: var(--bg); color: var(--text);
    font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; font-size: 13px; line-height: 1.5;
  }}
  h1 {{ font-size: 22px; margin: 0 0 2px; }}
  h2 {{
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-dim);
    border-bottom: 1px solid var(--border); padding-bottom: 6px; margin: 28px 0 12px;
  }}
  .subtitle {{ color: var(--text-dim); font-size: 12px; }}
  .meta {{ color: var(--text-faint); font-size: 11px; margin-top: 4px; }}
  .section {{ break-inside: avoid; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
  .grid-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 12px 14px; }}
  .row {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid var(--border); font-size: 12px; }}
  .row:last-child {{ border-bottom: none; }}
  .row .label {{ color: var(--text-dim); }}
  .row .value {{ font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; }}
  .badge {{
    display: inline-block; font-size: 9px; font-weight: 700; letter-spacing: 0.05em;
    text-transform: uppercase; padding: 2px 6px; border-radius: 3px; margin-left: 8px;
    vertical-align: middle;
  }}
  .badge-measured {{ color: var(--green); background: rgba(26,143,92,0.1); border: 1px solid rgba(26,143,92,0.35); }}
  .badge-calculated {{ color: var(--cyan); background: rgba(14,124,134,0.1); border: 1px solid rgba(14,124,134,0.35); }}
  .badge-estimated {{ color: var(--amber); background: rgba(165,104,10,0.1); border: 1px solid rgba(165,104,10,0.35); }}
  .badge-simulated {{ color: var(--purple); background: rgba(122,58,171,0.1); border: 1px solid rgba(122,58,171,0.35); }}
  .simulation-banner {{
    background: rgba(122,58,171,0.08); border: 1px solid rgba(122,58,171,0.4); color: var(--purple);
    padding: 10px 14px; border-radius: 6px; font-size: 12px; font-weight: 700; margin: 14px 0 20px;
    text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .finding {{ border-bottom: 1px solid var(--border); padding: 8px 0; font-size: 12px; }}
  .finding:last-child {{ border-bottom: none; }}
  .finding .category {{ font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; }}
  .finding.warning .category {{ color: var(--red); }}
  .finding.info .category {{ color: var(--text-dim); }}
  .note {{ font-size: 11px; color: var(--text-faint); margin-top: 8px; line-height: 1.5; }}
  .assumptions li {{ margin-bottom: 6px; }}
  .print-hint {{ text-align: right; font-size: 11px; color: var(--text-faint); margin-bottom: 8px; }}
  @media print {{ .print-hint {{ display: none; }} body {{ padding: 0 24px; }} }}
</style>
</head>
<body>
  <div class="print-hint">Use your browser's Print (Ctrl/Cmd+P) to save this report as PDF.</div>

  <h1>VYBE Session Report</h1>
  <div class="subtitle">Virtual Yield &amp; Benchmarking Engine - GPU / data-center resource intelligence platform</div>
  <div class="meta">Generated {generated_at} &middot; Session ID: {_esc(detail.session_id)}</div>

  {'<div class="simulation-banner">⚠ SIMULATION MODE - this session used synthetically generated telemetry for demonstration purposes. It does not reflect real hardware behavior and must not be treated as a measurement.</div>' if detail.is_simulated else ""}

  <h2>1. Workload Information</h2>
  <div class="panel section">
    <div class="row"><span class="label">Workload name</span><span class="value">{_esc(detail.workload_name)}</span></div>
    <div class="row"><span class="label">Status</span><span class="value">{_esc(detail.status)}</span></div>
    <div class="row"><span class="label">Useful output</span><span class="value">{
        f"{detail.useful_output_count} {_esc(detail.useful_output_unit)}"
        if detail.useful_output_count else "Not reported"
    }</span></div>
  </div>

  <h2>2. Hardware Information {_measured_badge(detail.is_simulated)}</h2>
  <div class="panel section">
    {_hardware_rows(detail)}
  </div>

  <h2>3. Runtime</h2>
  <div class="panel section">
    <div class="row"><span class="label">Start time</span><span class="value">{detail.start_time.strftime("%Y-%m-%d %H:%M:%S UTC")}</span></div>
    <div class="row"><span class="label">End time</span><span class="value">{detail.end_time.strftime("%Y-%m-%d %H:%M:%S UTC") if detail.end_time else "n/a"}</span></div>
    <div class="row"><span class="label">Runtime</span><span class="value">{_fmt(detail.runtime_seconds, 1, " s")}</span></div>
    <div class="row"><span class="label">Telemetry samples collected</span><span class="value">{detail.sample_count}</span></div>
    <div class="row"><span class="label">Sampling interval</span><span class="value">{_fmt(detail.interval_seconds, 2, " s")}</span></div>
  </div>

  <h2>4. GPU Statistics {_measured_badge(detail.is_simulated)}</h2>
  <div class="panel section">
    <div class="row"><span class="label">Average GPU utilization</span><span class="value">{_fmt(stats.average_gpu_utilization_percent, 1, "%")}</span></div>
    <div class="row"><span class="label">Peak GPU utilization</span><span class="value">{_fmt(stats.peak_gpu_utilization_percent, 1, "%")}</span></div>
    <div class="row"><span class="label">Average VRAM used</span><span class="value">{_fmt(stats.average_vram_used_mb, 0, " MB")}</span></div>
    <div class="row"><span class="label">Peak VRAM used</span><span class="value">{_fmt(stats.peak_vram_used_mb, 0, " MB")}</span></div>
    <div class="row"><span class="label">Peak GPU temperature</span><span class="value">{_fmt(stats.peak_temperature_c, 1, " &deg;C")}</span></div>
  </div>

  <h2>5. CPU / RAM Statistics {_measured_badge(detail.is_simulated)}</h2>
  <div class="panel section">
    <div class="row"><span class="label">Average CPU utilization</span><span class="value">{_fmt(stats.average_cpu_utilization_percent, 1, "%")}</span></div>
    <div class="row"><span class="label">Average RAM used</span><span class="value">{_fmt(stats.average_ram_used_percent, 1, "%")}</span></div>
    <div class="row"><span class="label">Peak RAM used</span><span class="value">{_fmt(stats.peak_ram_used_percent, 1, "%")}</span></div>
  </div>

  <h2>6. Power Statistics {_measured_badge(detail.is_simulated)}</h2>
  <div class="panel section">
    <div class="row"><span class="label">Average GPU power draw</span><span class="value">{_fmt(energy.average_power_w, 1, " W")}</span></div>
    <div class="row"><span class="label">Peak GPU power draw</span><span class="value">{_fmt(energy.peak_power_w, 1, " W")}</span></div>
    <div class="note">GPU chip power only - not total system power (CPU, RAM, storage, display, PSU losses are excluded).</div>
  </div>

  {_calculations_sections(detail.calculations)}

  <h2>11-12. Efficiency Analysis &amp; Recommendations</h2>
  <div class="panel section">
    {_findings_html(recommendations)}
    <div class="note">These are heuristic hypotheses based on simple, documented thresholds - not proven diagnoses or guaranteed fixes.</div>
  </div>

  <h2>13. Assumptions &amp; Scientific Limitations</h2>
  <div class="panel section">
    <ul class="assumptions">
      {'<li><strong>This entire session was run in SIMULATION MODE (Section 24).</strong> All hardware, GPU, power, CPU, and RAM figures above are synthetically generated for demonstration and are not real measurements.</li>' if detail.is_simulated else ""}
      <li>1-second (or configured-interval) sampling is a discrete approximation of a continuous signal and will miss sub-second power/utilization spikes.</li>
      <li>Energy is CALCULATED by integrating measured GPU power over actual elapsed time between samples - it is not itself a direct measurement.</li>
      <li>GPU chip power is not total system power: CPU, RAM, storage, display, and PSU conversion losses are not included.</li>
      <li>Idle GPU draw is nonzero, so not all measured power during a session is attributable solely to the workload.</li>
      <li>Carbon and water figures are ESTIMATES, not measurements, based on the configurable assumptions shown above. Real grid carbon intensity varies by time of day, season, and energy mix.</li>
      <li>Data-center-scale environmental impact requires additional infrastructure assumptions (e.g. PUE/WUE) beyond this single GPU/session.</li>
      <li>GPU utilization is not the same as GPU power, and a laptop GPU's power draw is not representative of a full data-center rack.</li>
      <li>Efficiency findings are heuristics based on simple fixed thresholds, not a tuned diagnostic system.</li>
    </ul>
  </div>
</body>
</html>"""


def _hardware_rows(detail: SessionDetail) -> str:
    hw = detail.hardware
    if hw is None:
        return '<div class="note">No hardware snapshot recorded for this session.</div>'
    return f"""
    <div class="row"><span class="label">GPU</span><span class="value">{_esc(hw.gpu_name)}</span></div>
    <div class="row"><span class="label">Driver version</span><span class="value">{_esc(hw.gpu_driver_version)}</span></div>
    <div class="row"><span class="label">CUDA version</span><span class="value">{_esc(hw.gpu_cuda_version)}</span></div>
    <div class="row"><span class="label">VRAM total</span><span class="value">{_fmt(hw.gpu_vram_total_mb, 0, " MB")}</span></div>
    <div class="row"><span class="label">GPU power cap</span><span class="value">{_fmt(hw.gpu_power_limit_w, 0, " W") if hw.gpu_power_limit_w else "Metric unavailable on this hardware"}</span></div>
    <div class="row"><span class="label">CPU</span><span class="value">{_esc(hw.cpu_model)}</span></div>
    <div class="row"><span class="label">CPU cores</span><span class="value">{hw.cpu_physical_cores or "n/a"} physical / {hw.cpu_logical_cores or "n/a"} logical</span></div>
    <div class="row"><span class="label">System RAM</span><span class="value">{_fmt(hw.ram_total_mb / 1024, 1, " GB")}</span></div>
    <div class="row"><span class="label">Operating system</span><span class="value">{_esc(hw.os_pretty_name)}</span></div>
    """


def _calculations_sections(calc: SessionCalculations | None) -> str:
    if calc is None:
        return """
  <h2>7-10. Energy, Cost, Carbon &amp; Water</h2>
  <div class="panel section"><div class="note">No calculated metrics are available for this session.</div></div>
        """

    yield_row = ""
    if calc.yield_metrics is not None:
        y = calc.yield_metrics
        yield_row = f"""
    <div class="row"><span class="label">Energy per {_esc(y.useful_output_unit)}</span><span class="value">{_fmt(y.energy_per_unit_wh, 4, " Wh")}</span></div>
    <div class="row"><span class="label">Cost per {_esc(y.useful_output_unit)}</span><span class="value">{calc.cost.currency} {_fmt(y.cost_per_unit, 6)}</span></div>
    <div class="row"><span class="label">Energy per 1,000 {_esc(y.useful_output_unit)}</span><span class="value">{_fmt(y.energy_per_1000_units_kwh, 5, " kWh")}</span></div>
        """

    return f"""
  <h2>7. Energy Consumption <span class="badge badge-calculated">Calculated</span></h2>
  <div class="panel section">
    <div class="row"><span class="label">Total energy</span><span class="value">{_fmt(calc.energy.total_energy_wh, 3, " Wh")} ({_fmt(calc.energy.total_energy_kwh, 6, " kWh")})</span></div>
    <div class="row"><span class="label">Intervals used / skipped</span><span class="value">{calc.energy.intervals_used} / {calc.energy.intervals_skipped}</span></div>
    {f'<div class="note">{" ".join(calc.energy.warnings)}</div>' if calc.energy.warnings else ""}
  </div>

  <h2>8. Electricity Cost <span class="badge badge-calculated">Calculated</span></h2>
  <div class="panel section">
    <div class="row"><span class="label">Estimated cost</span><span class="value">{calc.cost.currency} {_fmt(calc.cost.total_cost, 4)}</span></div>
    <div class="row"><span class="label">Rate assumed</span><span class="value">{calc.cost.currency} {calc.cost.rate_per_kwh} / kWh</span></div>
    {yield_row}
  </div>

  <h2>9. Carbon Estimate <span class="badge badge-estimated">Estimated</span></h2>
  <div class="panel section">
    <div class="row"><span class="label">Estimated CO2e</span><span class="value">{_fmt(calc.carbon.estimated_kg_co2e * 1000, 2, " g")}</span></div>
    <div class="row"><span class="label">Grid intensity assumed</span><span class="value">{calc.carbon.carbon_intensity_kg_per_kwh} kg CO2e/kWh</span></div>
    <div class="note">{_esc(calc.carbon.note)}</div>
  </div>

  <h2>10. Water Estimate <span class="badge badge-estimated">Estimated</span></h2>
  <div class="panel section">
    <div class="row"><span class="label">Estimated water associated</span><span class="value">{
        _fmt(calc.water.estimated_liters, 4, " L") if calc.water.enabled else "Disabled by configuration"
    }</span></div>
    {f'<div class="row"><span class="label">WUE assumed</span><span class="value">{calc.water.wue_l_per_kwh} L/kWh</span></div>' if calc.water.enabled else ""}
    <div class="note">{_esc(calc.water.note)}</div>
  </div>
    """


def _findings_html(recommendations: list[Recommendation]) -> str:
    if not recommendations:
        return '<div class="note">No findings.</div>'
    return "\n".join(
        f"""<div class="finding {r.severity}">
              <div class="category">{_esc(r.category.replace('_', ' '))}</div>
              <div>{_esc(r.message)}</div>
            </div>"""
        for r in recommendations
    )
