"""Demonstration / simulation mode (Section 24).

Generates realistic-looking but entirely synthetic telemetry, so VYBE can be
demonstrated on a machine with no working NVIDIA GPU (or for a controlled
demo run). This is a distinct, explicitly opted-into mode - never a silent
substitute for missing real data (that would violate Section 3's "never
invent data to fill a gap"). Every simulated session is tagged
`is_simulated=True` end-to-end (DB, API responses, reports, dashboard) so it
can never be mistaken for a real measurement.
"""

import random

from app.schemas import GPUProcessInfo, GPUSample, SessionHardwareSnapshot

SIMULATED_GPU_NAME = "Simulated NVIDIA GPU (Demo Mode)"
SIMULATED_VRAM_TOTAL_MB = 6144.0
SIMULATED_POWER_LIMIT_W = 35.0
SIMULATED_IDLE_POWER_W = 16.0
SIMULATED_RAM_TOTAL_MB = 16384.0


def simulated_hardware_snapshot() -> SessionHardwareSnapshot:
    return SessionHardwareSnapshot(
        gpu_name=SIMULATED_GPU_NAME,
        gpu_driver_version="simulated",
        gpu_cuda_version="simulated",
        gpu_vram_total_mb=SIMULATED_VRAM_TOTAL_MB,
        gpu_power_limit_w=SIMULATED_POWER_LIMIT_W,
        cpu_model="Simulated CPU (Demo Mode)",
        cpu_physical_cores=8,
        cpu_logical_cores=16,
        ram_total_mb=SIMULATED_RAM_TOTAL_MB,
        os_pretty_name="Simulated environment (Demo Mode)",
    )


class SimulatedWorkloadState:
    """Smoothly random-walks a plausible training-style workload profile.

    Held per-session so consecutive samples evolve continuously (ramp-up, a
    noisy plateau, occasional dips) instead of resampling independently each
    tick, which would look nothing like a real workload.
    """

    def __init__(self, seed: str) -> None:
        self._rng = random.Random(seed)
        self.gpu_utilization = 15.0
        self.vram_used_mb = 300.0
        self.temperature_c = 38.0
        self.cpu_utilization = 20.0
        self.ram_used_percent = 32.0

    def _walk(self, value: float, delta: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value + self._rng.uniform(-delta, delta)))

    def step(self) -> tuple[GPUSample, float, float, float]:
        rng = self._rng

        self.gpu_utilization = self._walk(self.gpu_utilization, 12.0, 8.0, 97.0)

        target_vram = 300.0 + (self.gpu_utilization / 100.0) * (SIMULATED_VRAM_TOTAL_MB * 0.55)
        self.vram_used_mb += (target_vram - self.vram_used_mb) * 0.2 + rng.uniform(-15.0, 15.0)
        self.vram_used_mb = max(250.0, min(SIMULATED_VRAM_TOTAL_MB * 0.9, self.vram_used_mb))

        target_temp = 38.0 + (self.gpu_utilization / 100.0) * 35.0
        self.temperature_c += (target_temp - self.temperature_c) * 0.15 + rng.uniform(-0.8, 0.8)
        self.temperature_c = max(32.0, min(83.0, self.temperature_c))

        util_fraction = self.gpu_utilization / 100.0
        power = SIMULATED_IDLE_POWER_W + util_fraction * (
            SIMULATED_POWER_LIMIT_W - SIMULATED_IDLE_POWER_W
        )
        power += rng.uniform(-0.6, 0.6)
        power = max(SIMULATED_IDLE_POWER_W * 0.9, min(SIMULATED_POWER_LIMIT_W, power))

        mem_util = max(0.0, min(100.0, self.gpu_utilization * 0.6 + rng.uniform(-5.0, 5.0)))

        self.cpu_utilization = self._walk(self.cpu_utilization, 10.0, 5.0, 95.0)
        self.ram_used_percent = self._walk(self.ram_used_percent, 3.0, 20.0, 85.0)
        ram_used_mb = (self.ram_used_percent / 100.0) * SIMULATED_RAM_TOTAL_MB

        sample = GPUSample(
            available=True,
            gpu_utilization_percent=round(self.gpu_utilization, 1),
            memory_utilization_percent=round(mem_util, 1),
            vram_used_mb=round(self.vram_used_mb, 1),
            power_draw_w=round(power, 2),
            temperature_c=round(self.temperature_c, 1),
            processes=[
                GPUProcessInfo(
                    pid=0,
                    process_name="simulated-workload",
                    gpu_memory_used_mb=round(self.vram_used_mb, 1),
                    utilization_available=False,
                )
            ],
            process_utilization_available=False,
        )
        return (
            sample,
            round(self.cpu_utilization, 1),
            round(self.ram_used_percent, 1),
            round(ram_used_mb, 1),
        )
