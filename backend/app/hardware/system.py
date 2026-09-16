"""CPU / RAM / OS detection via psutil and platform (no NVIDIA dependency)."""

import platform
import re

import psutil

from app.schemas import CPUInfo, MemoryInfo, OSInfo, SystemInfo


def _cpu_model_name() -> str | None:
    if platform.system() != "Linux":
        return platform.processor() or None
    try:
        with open("/proc/cpuinfo") as f:
            match = re.search(r"^model name\s*:\s*(.+)$", f.read(), re.MULTILINE)
        return match.group(1).strip() if match else platform.processor() or None
    except OSError:
        return platform.processor() or None


def _pretty_os_name() -> str | None:
    if platform.system() != "Linux":
        return None
    try:
        with open("/etc/os-release") as f:
            match = re.search(r'^PRETTY_NAME="(.+)"$', f.read(), re.MULTILINE)
        return match.group(1) if match else None
    except OSError:
        return None


def cpu_ram_snapshot() -> tuple[float | None, float | None, float | None]:
    """Cheap, non-blocking CPU/RAM reading for the telemetry polling loop.

    Unlike detect_system(), this skips static OS/CPU-model lookups (already
    reported once via /api/system/info) and uses psutil.cpu_percent(interval=
    None), which returns usage since the last call instead of blocking - safe
    to call every second without adding its own delay to the poll cadence.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
    except Exception:
        cpu_percent = None

    try:
        vm = psutil.virtual_memory()
        ram_percent = vm.percent
        ram_used_mb = vm.used / 1_000_000
    except Exception:
        ram_percent = None
        ram_used_mb = None

    return cpu_percent, ram_percent, ram_used_mb


def detect_system() -> SystemInfo:
    vm = psutil.virtual_memory()

    return SystemInfo(
        os=OSInfo(
            system=platform.system(),
            release=platform.release(),
            version=platform.version(),
            pretty_name=_pretty_os_name(),
            machine=platform.machine(),
        ),
        cpu=CPUInfo(
            model=_cpu_model_name(),
            physical_cores=psutil.cpu_count(logical=False),
            logical_cores=psutil.cpu_count(logical=True),
            current_utilization_percent=psutil.cpu_percent(interval=0.1),
        ),
        memory=MemoryInfo(
            total_mb=vm.total / 1_000_000,
            available_mb=vm.available / 1_000_000,
            used_mb=vm.used / 1_000_000,
            used_percent=vm.percent,
        ),
    )
