# PROJECT NAME: VYBE — Virtual Yield & Benchmarking Engine

## GPU / DATA CENTER RESOURCE INTELLIGENCE PLATFORM

You are building this complete project from scratch.

This is a final-year MSBTE Diploma Computer Engineering capstone project focused on **GPU hardware monitoring, compute resource utilization, energy consumption, cost analysis, and data-center environmental impact**.

The goal is a working software platform that monitors an AI/ML workload while it runs and explains how efficiently the underlying hardware and infrastructure are being used.

IMPORTANT:
- Do NOT treat this as a generic AI dashboard.
- Do NOT make the project primarily about machine learning.
- The core focus is **GPU hardware, compute resources, telemetry, energy, cost, and infrastructure efficiency**.

---

# 0. VERIFIED DEVELOPMENT ENVIRONMENT

These facts were confirmed on the actual development machine. Do not assume otherwise; re-verify only if something breaks.

**Operating system:** Ubuntu Linux
**Python:** 3.12.3
**GPU:** NVIDIA GeForce RTX 4050 Laptop GPU
**Driver:** 595.84
**CUDA:** 13.2
**VRAM:** 6141 MiB (~6 GB)
**Power cap:** 35 W (shown in nvidia-smi table)
**Idle draw:** ~16 W

## Confirmed capabilities

- `nvidia-smi` works and reports the GPU correctly.
- **GPU power draw IS available** — `nvidia-smi --query-gpu=power.draw` returns live wattage (e.g. `16.77 W`). Energy calculation can therefore be based on real measured power, not a fallback estimate.
- **Per-process GPU memory attribution works** — the nvidia-smi process table lists PIDs with their GPU memory usage. Linux does not have the WDDM restrictions that limit this on Windows.

## Confirmed limitations

- `power.limit` returns `[N/A]` from the CSV query, even though the main nvidia-smi table shows a 35 W cap. Do not depend on the `power.limit` query field. If a power cap value is needed, parse it from the nvidia-smi table or treat it as unavailable and degrade gracefully.
- Per-process GPU **utilization** (as opposed to memory) may be unavailable or unreliable. Design workload attribution around memory-based attribution, and fall back gracefully if utilization-per-process cannot be obtained.
- Idle power is ~16 W of a 35 W envelope. A meaningful portion of measured power during a workload is not attributable to that workload. Consider capturing an idle baseline before a session and reporting it alongside the results.

---

# 1. CORE IDEA

A user runs an AI/ML workload on their computer. VYBE observes the workload and hardware while it runs.

It should answer:

- How much GPU was used?
- How much VRAM was used?
- How much CPU was used?
- How much RAM was used?
- How long did the workload run?
- How much GPU power was consumed?
- How much energy was consumed?
- Approximately how much electricity did it cost?
- What was the estimated carbon impact?
- What was the estimated water impact?
- Was the hardware being used efficiently?
- Where was the workload wasting resources?
- What could the user change to improve efficiency?

Pipeline:
---

# 2. MEASUREMENT HONESTY (CRITICAL)

Be scientifically honest about measurements. This distinction is a core feature of the project, not a footnote.

**DIRECTLY MEASURED / COLLECTED**
- GPU utilization
- GPU memory utilization
- GPU VRAM usage
- GPU temperature
- GPU power draw (confirmed available on this hardware)
- CPU utilization
- RAM utilization
- Runtime
- GPU model, CPU model, system information

**CALCULATED**
- GPU-hours
- Energy consumption
- kWh
- Electricity cost

**ESTIMATED**
- Carbon emissions
- Data-center overhead
- Water consumption
- Other environmental metrics

Never present estimated environmental values as exact measurements. Clearly label estimated values in both the UI and the report, and always show the assumptions used.

---

# 3. TARGET HARDWARE

Primary target is the NVIDIA RTX 4050 laptop GPU described in section 0.

Use available NVIDIA interfaces:
- NVIDIA NVML via `pynvml`
- `nvidia-smi` as a fallback
- CUDA information where useful

Do NOT require the user to purchase additional hardware.

Design the architecture so other NVIDIA GPUs work automatically where supported.

If a metric cannot be obtained on a particular GPU, report:

> "Metric unavailable on this hardware"

Never invent data to fill a gap.

---

# 4. MAIN FEATURES

## A. System detection

Automatically detect and display clearly:
- GPU name
- GPU memory
- CUDA version if available
- Driver version
- CPU
- CPU cores
- System RAM
- Operating system

## B. Workload monitoring

Allow the user to run/monitor a workload. Collect telemetry periodically.

At minimum, per sample:
- timestamp
- GPU utilization
- GPU memory utilization
- VRAM used
- GPU power
- GPU temperature
- CPU utilization
- RAM utilization

Store measurements as time-series data. The monitoring interval must be configurable. Default: **1 second**.

---

# 5. WORKLOAD IDENTIFICATION

Attempt to identify which process is consuming GPU resources.

Capture at minimum:
- process ID
- process name
- GPU memory usage
- GPU utilization where available

Allow the user to associate a monitoring session with a named workload, e.g. "ResNet training", "YOLO inference", "Custom PyTorch workload".

Do not assume every GPU process is an AI workload.

Note: per-process memory attribution is confirmed working on this machine; per-process utilization may not be. Degrade gracefully.

---

# 6. ENERGY CALCULATION

Use measured GPU power. For variable power, integrate the power samples over time:
Convert to Wh and kWh.

Display:
- average power
- peak power
- total energy
- runtime

Do NOT calculate energy as `maximum power × runtime` unless explicitly presenting it as a labelled rough fallback estimate.

Document that 1-second sampling is a discrete approximation of a continuous signal and will miss sub-second spikes.

Document that this measures GPU chip power only — not CPU, RAM, storage, display, or PSU losses, and therefore not total system power.

---

# 7. ELECTRICITY COST

Allow the user to enter an electricity price, e.g. ₹10 / kWh.
Currency and rate must be configurable in the UI. Default currency: INR (₹).

Do not hardcode a claim that electricity always costs a particular amount.

---

# 8. CARBON ESTIMATION

Allow the user to configure grid carbon intensity (kg CO₂e / kWh).
Clearly label as an estimate. Show the carbon-intensity assumption in the report. Note that real grid intensity varies by time of day, season, and energy mix, so this is a directional estimate.

---

# 9. WATER ESTIMATION

Water consumption cannot be directly measured on this hardware.

Do NOT pretend the system measures water usage.

Implement an optional estimation model based on configurable assumptions such as water usage effectiveness (WUE), energy consumed, and infrastructure assumptions.

Display as:

> "Estimated associated water consumption"

Show the assumptions. Allow the user to disable this metric. Frame it in documentation as illustrative methodology rather than measurement.

---

# 10. EFFICIENCY ANALYSIS

One of the most important parts of the project. Do not build only a monitoring dashboard.

Analyse collected telemetry to identify:
- high power with low GPU utilization
- excessive VRAM usage
- CPU bottleneck
- RAM bottleneck
- GPU underutilization
- long idle periods
- unusually high power consumption
- poor utilization consistency
- inefficient workload periods

Generate understandable findings, for example:

> "GPU utilization averaged 42% while GPU power remained relatively high. The workload may be CPU/input-data bound."

> "VRAM usage remained below 35% for most of the run. Increasing batch size may improve GPU utilization if model and memory constraints allow."

These are heuristics and hypotheses, not diagnoses. Present them as recommendations, never as guaranteed solutions or proven causes.

---

# 11. PERFORMANCE VS RESOURCE EFFICIENCY

Where possible, allow the workload to report a useful-output metric: images processed, samples processed, predictions, tokens generated, training epochs, batches completed.

Then calculate:
- energy per inference
- cost per inference
- energy per 1,000 samples
- cost per 1,000 samples
- energy per training epoch

Raw GPU utilization alone does not indicate whether a workload is efficient. This is the "yield" in Virtual Yield & Benchmarking Engine.

---

# 12. SESSION SYSTEM

Every monitoring run creates a session, e.g. "YOLOv8 Benchmark".

Store:
- session name
- start time
- end time
- runtime
- hardware
- telemetry
- energy
- cost
- carbon estimate
- water estimate
- efficiency findings

Users must be able to view previous sessions.

---

# 13. COMPARISON

Allow comparison of two or more sessions — e.g. Model A vs Model B, or batch size 16 vs 32.

Show:
- runtime
- average GPU utilization
- peak GPU utilization
- average power
- total energy
- electricity cost
- carbon estimate
- energy per useful output

The goal is determining which configuration is more efficient.

---

# 14. DASHBOARD

A modern technical dashboard. It should NOT look like a generic admin panel.

Visual identity should evoke GPU infrastructure, data centers, compute hardware, monitoring, telemetry, and engineering.

Include:

**Hardware panel** — GPU, VRAM, temperature, power

**Live telemetry** — GPU utilization, VRAM, power, temperature, CPU, RAM, with live charts

**Current workload** — process/workload name, runtime, GPU utilization, power, energy

**Energy** — total energy, average power, peak power

**Cost** — electricity rate, estimated cost

**Environmental** — carbon estimate, water estimate

**Efficiency** — efficiency score/indicators, problems detected, recommendations

Clearly distinguish measured vs estimated metrics throughout the UI.

---

# 15. HISTORICAL DATA

A history page showing previous sessions, with search, filtering, sorting, detail view, deletion, and comparison.

---

# 16. REPORT GENERATION

Generate a report for a completed session containing:

1. Workload information
2. Hardware information
3. Runtime
4. GPU statistics
5. CPU/RAM statistics
6. Power statistics
7. Energy consumption
8. Electricity cost
9. Carbon estimate
10. Water estimate
11. Efficiency analysis
12. Recommendations
13. Assumptions

Make the report suitable for demonstrating the project to college faculty.

---

# 17. ARCHITECTURE
**Backend:** Python + FastAPI
**GPU monitoring:** pynvml / NVIDIA NVML, with nvidia-smi as fallback
**ML workload compatibility:** PyTorch
**Database:** SQLite
**Frontend:** React + modern UI
**Charts:** a suitable React charting library

Do not introduce unnecessary infrastructure. Docker may be added if useful, but do not let Docker complexity consume the project.

---

# 18. API DESIGN

Clean REST APIs for:
- system information
- GPU information
- starting a monitoring session
- stopping a session
- live telemetry
- session history
- session details
- calculations
- efficiency analysis
- recommendations
- comparison
- report generation
- configuration

Use proper validation and error handling.

---

# 19. DATABASE

Design appropriate models. Consider at minimum:
- users/settings (if authentication is implemented)
- sessions
- telemetry_samples
- workload information
- hardware information
- calculated_metrics
- recommendations

Avoid overengineering. SQLite is sufficient.

---

# 20. CONFIGURATION

Allow configuration of:
- telemetry interval
- electricity rate
- currency
- carbon intensity
- water estimation assumptions
- monitoring duration where applicable

Use environment variables for application configuration where appropriate.

---

# 21. ERROR HANDLING

Handle gracefully:
- NVIDIA GPU unavailable
- NVML unavailable
- nvidia-smi unavailable
- permission errors
- GPU metric unavailable
- workload process disappears
- monitoring stops unexpectedly
- database errors
- invalid configuration

Do not crash unnecessarily. Show understandable errors to the user.

---

# 22. PERFORMANCE

Monitoring must have low overhead. Do not perform expensive operations every second. Use efficient polling. Do not store unnecessarily large amounts of data. The application must remain usable while an ML workload is running.

---

# 23. SECURITY

This is a college prototype — do not overengineer enterprise security. However:
- validate API inputs
- do not execute arbitrary shell commands from user input
- avoid unsafe subprocess handling
- do not expose secrets
- use environment variables for sensitive configuration

---

# 24. DEMONSTRATION MODE

Create a simulated/demo mode for systems where NVIDIA telemetry is unavailable. This matters for college demonstrations.

Demo mode generates realistic-looking telemetry but MUST be clearly labelled:

**SIMULATION MODE**

Never mix simulated data with real measurements without clear indication.

---

# 25. TESTING

Create tests for:
- energy calculation
- cost calculation
- carbon calculation
- water estimation
- telemetry processing
- session creation
- API endpoints
- edge cases
- unavailable GPU metrics

Use realistic sample telemetry. Verify calculations are mathematically correct.

---

# 26. DOCUMENTATION

A good README containing:
- project overview
- architecture
- features
- requirements
- installation
- NVIDIA requirements
- how to run
- how to monitor a workload
- configuration
- formulas
- assumptions
- limitations
- demo mode
- screenshots if available
- future improvements

Explain clearly which values are MEASURED, CALCULATED, and ESTIMATED.

---

# 27. SCIENTIFIC LIMITATIONS

Do not make false claims. State plainly, in both the app and the docs:

- GPU utilization ≠ GPU power.
- GPU power ≠ total system power.
- Laptop GPU power ≠ complete data-center power.
- Water consumption is an estimate.
- Carbon emissions depend on electricity source / grid carbon intensity.
- Data-center environmental impact requires infrastructure-level assumptions such as PUE/WUE.
- 1-second sampling is a discrete approximation and misses sub-second power spikes.
- Idle draw (~16 W here) means not all measured power is attributable to the workload.

---

# 28. DEVELOPMENT APPROACH

You have autonomy over implementation. Do not repeatedly ask which framework, library, or file structure to use when a reasonable engineering decision can be made independently.

Build incrementally in this order:

1. Working backend and system/GPU detection
2. Telemetry collection
3. Calculations (energy, cost, carbon, water)
4. Database and session management
5. Efficiency analysis
6. Frontend dashboard
7. Comparison and reporting
8. Demo mode
9. Testing and documentation

Each phase should be working and verifiable before moving to the next.

---

# 29. QUALITY BAR

The deliverable is a COMPLETE WORKING PROJECT.

Not:
- a mockup
- a static dashboard
- placeholder buttons
- fake backend APIs
- TODO comments everywhere
- hardcoded telemetry
- fake "AI recommendations"
- unfinished pages

Core functionality must actually work on the NVIDIA system described in section 0.

If something cannot be implemented due to hardware limitations, implement a graceful fallback and document the limitation.

---

# 30. FINAL GOAL

The user should be able to:

1. Start the application
2. Detect their NVIDIA GPU
3. Start a monitoring session
4. Run an actual PyTorch workload
5. Collect real GPU/CPU/RAM telemetry
6. Observe live resource usage
7. Stop the session
8. Calculate energy consumption
9. Calculate electricity cost
10. Estimate carbon impact
11. Estimate associated water consumption
12. Analyse resource efficiency
13. Receive optimization recommendations
14. Save the session
15. Compare it with another session
16. Generate a report

Core concept:

> **"Understand what a compute workload is doing to the hardware, how much energy and money it consumes, and how efficiently that hardware is being used."**

Build this as a serious engineering project suitable for a final-year college demonstration.

---

# 31. DEPLOYMENT TARGET: SERVER / RACK / LAPTOP, NOT JUST LOCALHOST

VYBE must be deployable on any machine with an NVIDIA GPU — a developer's laptop, 
a shared lab server, or a GPU node in a data center rack — not only the original 
development machine. This does not change the core engineering (Phases 1–5); it 
changes packaging and a few architectural defaults, established now so later 
phases don't require rework.

## Standing rules for ALL backend code, starting in Phase 1

- The FastAPI server must bind to `0.0.0.0`, not `localhost` or `127.0.0.1`, so 
  it is reachable from other machines on a network, not only from the host itself.
- All configuration (electricity rate, currency, carbon intensity, telemetry 
  interval, database path, water-estimation assumptions) must be driven by 
  environment variables with sensible defaults, per Section 20 — never hardcoded.
- No hardcoded file paths. The SQLite database path and any report/output files 
  must go through a configurable data directory (e.g. `VYBE_DATA_DIR`), so it maps 
  cleanly onto a Docker volume later.

## Phase 9 addition: containerized deployment

In Phase 9, alongside tests and documentation, add:

- A `Dockerfile` for the backend (Python + pynvml + FastAPI).
- A `Dockerfile` for the frontend, OR serve the built React app as static files 
  from the backend — pick whichever is simpler to containerize cleanly.
- A `docker-compose.yml` that runs both together and exposes the correct ports.
- GPU access inside the container requires the **NVIDIA Container Toolkit** on 
  the host machine, and the container must be run with GPU access enabled 
  (e.g. `--gpus all` or the Compose `deploy.resources.reservations.devices` 
  equivalent). Docker does not grant GPU access by default — this must be 
  explicit and documented.
- The README (Section 26) must clearly state that NVIDIA Container Toolkit is 
  a host-side prerequisite for the containerized deployment path, separate 
  from the plain local-run path.
- Provide both installation paths in the README: (a) plain local run via venv 
  + npm, for development, and (b) `docker compose up` for installing on a 
  server, lab machine, or GPU rack.

## Framing note for documentation/report

VYBE is designed to run identically whether monitoring a developer's laptop or 
a shared GPU node in a data center rack, since energy and cost accounting 
matter at both scales.
