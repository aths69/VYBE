# VYBE — Virtual Yield & Benchmarking Engine

**GPU / data-center resource intelligence platform.**

VYBE watches an AI/ML workload while it runs and explains how efficiently
the underlying GPU hardware and infrastructure are being used: GPU/CPU/RAM
utilization, VRAM, power draw, runtime, energy consumed, electricity cost,
estimated carbon and water impact, and where the workload is wasting
resources.

This is a final-year MSBTE Diploma Computer Engineering capstone project.
The focus is deliberately **GPU hardware, telemetry, energy, cost, and
infrastructure efficiency** — not a generic ML dashboard, and not a project
about the models being trained.

---

## Table of contents

- [Core idea](#core-idea)
- [Measured vs. Calculated vs. Estimated](#measured-vs-calculated-vs-estimated)
- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation — local (development)](#installation--local-development)
- [Installation — Docker (server / lab / rack)](#installation--docker-server--lab--rack)
- [How to run](#how-to-run)
- [How to monitor a workload](#how-to-monitor-a-workload)
- [Demonstration / simulation mode](#demonstration--simulation-mode)
- [Configuration](#configuration)
- [Formulas](#formulas)
- [Assumptions and scientific limitations](#assumptions-and-scientific-limitations)
- [Testing](#testing)
- [API overview](#api-overview)
- [Future improvements](#future-improvements)

---

## Core idea

> Understand what a compute workload is doing to the hardware, how much
> energy and money it consumes, and how efficiently that hardware is being
> used.

A session = one monitored run of a workload ("ResNet training", "YOLOv8
inference", a custom PyTorch script, or anything else using the GPU).
VYBE samples GPU/CPU/RAM telemetry every second (configurable) while it
runs, then turns that into energy, cost, carbon/water estimates, and
plain-language efficiency findings — and lets you compare sessions against
each other (e.g. batch size 16 vs. 32) and generate a report suitable for a
faculty demonstration.

## Measured vs. Calculated vs. Estimated

This distinction is a core feature of the project, not a footnote, and it's
labeled throughout the UI, the API responses, and generated reports with
green/cyan/amber badges.

| Label | Meaning | Examples |
|---|---|---|
| **MEASURED** | Read directly from hardware/OS | GPU utilization, VRAM usage, GPU temperature, GPU power draw, CPU utilization, RAM utilization, runtime, GPU/CPU model |
| **CALCULATED** | Deterministic arithmetic on measured values | GPU-hours, energy (Wh/kWh), electricity cost, energy/cost per useful output |
| **ESTIMATED** | Depends on a configurable assumption about the outside world | Carbon emissions (grid intensity), water consumption (WUE), efficiency findings (heuristic thresholds) |

VYBE never invents a value to fill a gap. If a metric can't be obtained on
the current hardware, the API and UI say **"Metric unavailable on this
hardware"** rather than guessing.

## Features

- **System detection** — GPU name/VRAM/driver/CUDA version, CPU model/cores,
  system RAM, OS, all auto-detected at startup and refreshed live.
- **Workload monitoring** — start/stop a named session; 1-second (default,
  configurable) telemetry polling with low overhead; per-process GPU memory
  attribution where available.
- **Energy, cost, carbon, water** — real trapezoidal integration of measured
  GPU power over actual elapsed time (not `samples × nominal interval`),
  converted to cost via a configurable electricity rate/currency, and to
  carbon/water via configurable, clearly-labeled assumptions.
- **Efficiency analysis** — eight heuristics (GPU underutilization,
  high-power/low-utilization, VRAM too high/too low, CPU bottleneck, RAM
  bottleneck, idle periods, power near the hardware's cap, inconsistent
  utilization) that produce plain-language, hedged findings — never
  presented as proven diagnoses.
- **Yield metrics** — energy/cost per useful output (per image, per
  epoch, per 1,000 samples, ...) when you report how much work a session
  actually did.
- **Session history** — every stopped session is persisted (SQLite);
  search, filter, sort, view detail, delete.
- **Comparison** — pick 2–8 completed sessions and compare runtime, GPU
  utilization, power, energy, cost, carbon, and yield side by side, with the
  better value per metric highlighted.
- **Report generation** — a self-contained, printable HTML report per
  session (13 sections: workload → hardware → runtime → GPU/CPU/RAM/power
  stats → energy/cost/carbon/water → efficiency findings → assumptions).
  Export to PDF via the browser's own print dialog.
- **Demonstration / simulation mode** — generates realistic synthetic
  telemetry so the whole platform can be demonstrated on a machine with no
  NVIDIA GPU. Always and unmistakably labeled as simulated, everywhere it
  appears — never mixed with real measurements without a visible warning.
- **Configurable everything** — telemetry interval, electricity rate,
  currency, carbon intensity, water assumptions, all via environment
  variables with sensible defaults, overridable per-request where it makes
  sense (e.g. recompute a session's cost at a different rate).

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│  React + Vite (SPA)  │  REST  │  FastAPI backend          │
│  Dashboard / History │◄──────►│  ├─ hardware/  (NVML,     │
│  / Compare / Reports │  JSON  │  │   nvidia-smi, psutil)  │
└─────────────────────┘        │  ├─ telemetry/ (poll loop) │
                                │  ├─ calculations/          │
                                │  │   (energy/cost/carbon/  │
                                │  │    water/yield)         │
                                │  ├─ analysis/ (efficiency  │
                                │  │   heuristics, stats)    │
                                │  ├─ reporting/ (HTML       │
                                │  │   report generator)     │
                                │  └─ db/ (SQLAlchemy ORM)   │
                                └────────────┬──────────────┘
                                             │
                                      ┌──────▼──────┐
                                      │   SQLite     │
                                      │  vybe.db     │
                                      └──────────────┘
```

- **Backend:** Python 3.12 + FastAPI, binds to `0.0.0.0` by default so it's
  reachable from other machines on a network, not just localhost.
- **GPU monitoring:** `pynvml`/NVML as the primary interface; falls back to
  parsing `nvidia-smi`'s own table for the one field NVML doesn't reliably
  expose on this hardware class (the enforced power cap — see
  [Assumptions](#assumptions-and-scientific-limitations)).
- **Database:** SQLite, one file, no server process — sufficient for a
  single-workstation/single-lab-node monitoring tool.
- **Frontend:** React 19 + Vite + `recharts` for live charts.
- **No unnecessary infrastructure**: no message queue, no auth system, no
  ORM migrations framework (an additive-column check handles schema growth
  on an existing SQLite file) — deliberately kept to what a capstone
  project actually needs.

## Requirements

**To run with real GPU telemetry:**
- Linux (developed and verified on Ubuntu 24.04) or any OS `pynvml`/
  `nvidia-smi` support
- An NVIDIA GPU with a recent driver (`nvidia-smi` working from a terminal)
- Python 3.10+ (developed on 3.12.3)
- Node.js 20+ (developed on 22.x) and npm, for the frontend

**To run in demonstration/simulation mode** (no real GPU required):
- Just Python 3.10+ and Node.js — see
  [Demonstration / simulation mode](#demonstration--simulation-mode).

**For the Docker path:**
- Docker and Docker Compose
- **NVIDIA Container Toolkit** on the host, if you want the container to
  see the real GPU (see [Installation — Docker](#installation--docker-server--lab--rack))

## Installation — local (development)

```bash
# 1. Backend
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # add -dev.txt instead to also get test deps
python run.py                     # serves on http://0.0.0.0:8000

# 2. Frontend (separate terminal)
cd frontend
npm install
npm run dev                       # serves on http://0.0.0.0:5173
```

Open `http://localhost:5173` (or `http://<machine-ip>:5173` from another
device on the same network). The frontend auto-targets the backend on the
same hostname at port 8000; override with `VITE_API_BASE_URL` if you're
running them on different hosts.

## Installation — Docker (server / lab / rack)

For running on a shared lab machine or a GPU node in a rack rather than a
developer's own laptop:

```bash
docker compose up --build
```

This builds and runs the backend (serving the API on port 8000) and the
frontend (served as static files, on port 8080) together, with the SQLite
database persisted in a named volume.

**NVIDIA Container Toolkit is a host-side prerequisite** if you want the
container to see a real GPU — Docker does **not** grant GPU access by
default. Install the toolkit on the host first
(https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html),
then either:

- run with `docker compose up` as-is — the compose file already requests
  GPU access via `deploy.resources.reservations.devices`, or
- run the backend container directly with `docker run --gpus all ...`.

Without the toolkit installed on the host, the container will start fine
but report no GPU (`available: false`) — at which point demonstration mode
is the way to show the platform working. See the comments in
`docker-compose.yml` for details.

## How to run

1. Start the backend (`python run.py` or `docker compose up`).
2. Start the frontend (`npm run dev`, or it's already served by the backend
   container in the Docker path).
3. Open the dashboard in a browser. The **Hardware** panel should show your
   detected GPU/CPU/RAM within a couple of seconds; if it says "GPU
   unavailable", either your machine has no NVIDIA GPU or the driver isn't
   installed — use [simulation mode](#demonstration--simulation-mode)
   instead.

## How to monitor a workload

1. On the Dashboard, enter a **workload name** (e.g. "ResNet-50 training,
   batch 32") and an optional sampling **interval** (default 1s).
2. Click **Start Session**.
3. Run your actual GPU workload (a PyTorch training script, an inference
   server, anything that touches the GPU) in whatever terminal/notebook you
   normally use — VYBE observes the machine, it doesn't need to launch the
   workload itself.
4. Watch live GPU/CPU/RAM/power/temperature charts and running
   energy/cost/carbon estimates update.
5. When the workload finishes, optionally enter a **useful output count**
   (e.g. "500" images, or "12" epochs) and its unit, then click **Stop
   Session** — this unlocks the "energy per useful output" yield metrics.
6. The session is now saved. View it any time from **History**, generate a
   **Report**, or select 2+ sessions there to **Compare** them.

## Demonstration / simulation mode

For a college demonstration on a machine without a working NVIDIA GPU (or
to show the platform's behavior without waiting on a real long-running
job), check **"Run in simulation mode (demo)"** before starting a session.
This generates smooth, realistic-looking synthetic telemetry instead of
querying real hardware.

A simulated session is labeled **everywhere**, unmistakably:

- A purple "⚠ SIMULATION MODE" banner on the Dashboard while it runs
- A purple "Simulated" badge next to the workload name, in History, on the
  session detail page, and in the generated report
- The report's hardware/GPU/power sections are badged "Simulated" instead
  of "Measured"
- Comparing a simulated session against a real one raises an explicit
  warning that the two aren't apples-to-apples

Simulated telemetry is never silently substituted for missing real data —
it's an explicit, visible choice, consistent with the project's
measurement-honesty principle.

## Configuration

All configuration is via environment variables (backend) with sensible
defaults; nothing is hardcoded that a real deployment would need to change.

| Variable | Default | Meaning |
|---|---|---|
| `VYBE_HOST` | `0.0.0.0` | Backend bind address |
| `VYBE_PORT` | `8000` | Backend port |
| `VYBE_DATA_DIR` | `./data` | Directory for the SQLite DB (and any generated files) — maps to a Docker volume |
| `VYBE_TELEMETRY_INTERVAL_SECONDS` | `1.0` | Default polling interval; overridable per session at start time |
| `VYBE_ELECTRICITY_RATE` | `10.0` | Electricity price per kWh, in `VYBE_CURRENCY` |
| `VYBE_CURRENCY` | `INR` | Currency label shown alongside cost figures |
| `VYBE_CARBON_INTENSITY_KG_PER_KWH` | `0.7` | Grid carbon intensity assumption for the carbon estimate |
| `VYBE_WATER_WUE_L_PER_KWH` | `1.8` | Water Usage Effectiveness assumption (liters per kWh) |
| `VYBE_WATER_ESTIMATION_ENABLED` | `true` | Whether to compute/show the water estimate at all |
| `VYBE_CORS_ORIGINS` | `*` | Comma-separated allowed origins, or `*` |

| Frontend variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | same hostname as the page, port 8000 | Override if the backend runs on a different host/port |

Electricity rate, currency, carbon intensity, and water settings can also
be overridden **per request** on the `/api/sessions/{id}/calculations`
endpoint, without restarting the server — useful for asking "what would
this session have cost at a different electricity rate?"

## Formulas

**Energy (CALCULATED)** — trapezoidal integration of measured power over
actual elapsed time between consecutive samples, not `peak_power × runtime`:

```
for each pair of consecutive samples (prev, curr) where both have power data:
    Δt_hours = (curr.timestamp - prev.timestamp).total_seconds() / 3600
    interval_Wh = (prev.power_w + curr.power_w) / 2 × Δt_hours
total_energy_Wh = Σ interval_Wh
total_energy_kWh = total_energy_Wh / 1000
```

An interval is **skipped** (not zero-filled, not guessed) whenever GPU
power is unavailable at either endpoint; skipped/used interval counts and a
warning are always reported alongside the total.

**Cost (CALCULATED)**
```
total_cost = total_energy_kWh × electricity_rate_per_kWh
```

**Carbon (ESTIMATED)**
```
estimated_kg_CO2e = total_energy_kWh × grid_carbon_intensity_kg_per_kWh
```

**Water (ESTIMATED, optional)**
```
estimated_liters = total_energy_kWh × water_usage_effectiveness_L_per_kWh
```

**Yield / cost-efficiency (CALCULATED, when a useful-output count is given)**
```
energy_per_unit_Wh = total_energy_Wh / useful_output_count
cost_per_unit = total_cost / useful_output_count
energy_per_1000_units_kWh = (total_energy_kWh / useful_output_count) × 1000
cost_per_1000_units = (total_cost / useful_output_count) × 1000
```

## Assumptions and scientific limitations

Stated plainly, in the app and here, per the project's measurement-honesty
principle:

- GPU utilization ≠ GPU power. A GPU can draw significant power while
  reporting low utilization (memory-bound or data-starved workloads).
- GPU power ≠ total system power. VYBE measures the GPU chip only — not
  CPU, RAM, storage, display, or PSU conversion losses.
- A laptop/workstation GPU's power draw is not representative of a
  data-center rack's power profile.
- 1-second (or whatever interval is configured) sampling is a discrete
  approximation of a continuous signal and will miss sub-second spikes.
- Idle GPU power draw is nonzero, so not all measured power during a
  session is attributable to the workload itself.
- Carbon emissions depend entirely on the configured grid carbon-intensity
  assumption; real grid intensity varies by time of day, season, and energy
  mix — this is a directional estimate, not a measurement.
- Water consumption is **never measured** — it's an illustrative estimate
  based on energy consumed and a configurable Water Usage Effectiveness
  assumption, and can be disabled entirely.
- Data-center-scale environmental impact would need additional
  infrastructure assumptions (e.g. PUE) beyond a single GPU/session.
- Efficiency findings are heuristics based on simple, documented, fixed
  thresholds — hypotheses about what *might* be happening, phrased with
  "may"/"could"/"consider", never proven diagnoses or guaranteed fixes.
- On the reference hardware (Section 0 of the project spec — an RTX 4050
  Laptop GPU), NVML's own power-limit query is unsupported; the enforced
  cap is recovered by parsing the plain `nvidia-smi` table instead. If
  neither source has it, the app reports "Metric unavailable on this
  hardware" rather than guessing.
- Per-process GPU utilization (as opposed to memory) may be unavailable or
  unreliable depending on the driver/hardware; VYBE degrades gracefully and
  attributes workloads by GPU memory instead.

## Testing

```bash
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

55 tests cover energy/cost/carbon/water calculations (verified against
hand-computed values), telemetry-processing/efficiency heuristics, the full
session start→poll→stop→persist lifecycle, API validation and error
handling, and edge cases including GPU-unavailable telemetry and degraded
hardware detection. Tests run against an isolated temporary database (via
`VYBE_DATA_DIR`) and never touch your real session history, and use
simulation mode for lifecycle tests so the suite doesn't require a real
NVIDIA GPU to run.

## API overview

All endpoints are under `/api`. Key groups:

| Area | Endpoints |
|---|---|
| System/GPU detection | `GET /api/gpu/info`, `GET /api/system/info`, `GET /api/detect` |
| Session control | `POST /api/sessions/start`, `POST /api/sessions/{id}/stop`, `GET /api/sessions/current`, `GET /api/sessions/{id}` |
| Live telemetry | `GET /api/sessions/{id}/telemetry?since_index=` |
| Calculations | `GET /api/sessions/{id}/calculations` (rate/currency/carbon/water all overridable via query params) |
| Efficiency | `GET /api/sessions/{id}/efficiency` |
| History | `GET /api/sessions/history`, `GET /api/sessions/{id}/detail`, `DELETE /api/sessions/{id}` |
| Comparison | `GET /api/sessions/compare?session_ids=...&session_ids=...` (2–8 ids) |
| Report | `GET /api/sessions/{id}/report` (printable HTML) |
| Configuration | `GET /api/config` |

Interactive OpenAPI docs are available at `/docs` on the running backend.

## Future improvements

- Multi-GPU support (currently reports GPU index 0)
- A real migration tool (Alembic) if the schema grows beyond additive
  columns
- Per-user authentication if this ever needs to run as a shared multi-user
  service rather than a single workstation/lab-node tool
- PDF export without relying on the browser's print dialog
- Long-running session pagination for very large telemetry sets
