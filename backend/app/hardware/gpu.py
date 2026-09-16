"""GPU detection and live metrics.

Detection order:
1. NVML (pynvml / nvidia-ml-py) - primary interface, works cross-platform.
2. `nvidia-smi` CLI, invoked with a fixed argument list (no shell, no user
   input) - fallback for the one field NVML does not reliably expose on this
   hardware (the enforced power cap), and for systems without NVML bindings.
3. Otherwise report the GPU as unavailable. Never invent values.

Verified quirk (see CLAUDE.md Section 0): both
`nvmlDeviceGetPowerManagementLimit` and the `power.limit` CSV query field are
unreliable/unsupported on this machine, even though the plain `nvidia-smi`
table shows a real enforced cap (e.g. "35 W"). That cap is only recoverable
by parsing the human-readable table's "Pwr:Usage/Cap" column.
"""

import re
import subprocess

from app.schemas import GPUInfo, GPUProcessInfo, GPUSample

try:
    import pynvml as nvml

    _NVML_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover - depends on install
    nvml = None
    _NVML_IMPORT_ERROR = str(exc)

_POWER_CAP_RE = re.compile(r"(\d+(?:\.\d+)?)\s*W\s*/\s*(\d+(?:\.\d+)?)\s*W")

_SUBPROCESS_TIMEOUT_S = 3


def _mib_to_mb(mib: float) -> float:
    return mib * 1024 * 1024 / 1_000_000


def _bytes_to_mb(value: float) -> float:
    return value / 1_000_000


def _decode_cuda_version(raw: int) -> str:
    major = raw // 1000
    minor = (raw % 1000) // 10
    return f"{major}.{minor}"


def _power_cap_from_nvidia_smi() -> tuple[float | None, str | None]:
    """Parse the enforced power cap out of the plain nvidia-smi table.

    Returns (cap_watts, note). Never raises - any failure yields (None, note).
    """
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_S,
            check=True,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ) as exc:
        return None, f"nvidia-smi table unavailable: {exc}"

    match = _POWER_CAP_RE.search(result.stdout)
    if not match:
        return None, "power cap not found in nvidia-smi table output"
    return float(match.group(2)), None


def _processes_via_nvml(handle) -> tuple[list[GPUProcessInfo], bool]:
    import psutil

    assert nvml is not None  # only called after the caller confirmed nvml is loaded

    procs_by_pid: dict[int, GPUProcessInfo] = {}

    for getter in (
        nvml.nvmlDeviceGetComputeRunningProcesses,
        nvml.nvmlDeviceGetGraphicsRunningProcesses,
    ):
        try:
            for p in getter(handle):
                mem_mb = _bytes_to_mb(p.usedGpuMemory) if p.usedGpuMemory else None
                procs_by_pid[p.pid] = GPUProcessInfo(
                    pid=p.pid,
                    gpu_memory_used_mb=mem_mb,
                )
        except nvml.NVMLError:
            continue

    utilization_available = False
    try:
        util_samples = nvml.nvmlDeviceGetProcessUtilization(handle, 0)
        for sample in util_samples:
            if sample.pid in procs_by_pid:
                procs_by_pid[sample.pid].gpu_utilization_percent = sample.smUtil
                procs_by_pid[sample.pid].utilization_available = True
        utilization_available = True
    except nvml.NVMLError:
        pass  # confirmed unreliable on this hardware; degrade gracefully

    for proc in procs_by_pid.values():
        try:
            proc.process_name = psutil.Process(proc.pid).name()
        except psutil.NoSuchProcess:
            proc.process_name = None

    return list(procs_by_pid.values()), utilization_available


def _detect_via_nvml() -> GPUInfo:
    assert nvml is not None  # only called from detect_gpu() after checking this

    nvml.nvmlInit()
    try:
        handle = nvml.nvmlDeviceGetHandleByIndex(0)

        name = nvml.nvmlDeviceGetName(handle)
        driver_version = nvml.nvmlSystemGetDriverVersion()

        try:
            cuda_version = _decode_cuda_version(nvml.nvmlSystemGetCudaDriverVersion())
        except nvml.NVMLError:
            cuda_version = None

        mem = nvml.nvmlDeviceGetMemoryInfo(handle)

        try:
            power_draw_w = nvml.nvmlDeviceGetPowerUsage(handle) / 1000
            power_draw_available = True
        except nvml.NVMLError:
            power_draw_w = None
            power_draw_available = False

        # NVML's own power-limit query is unsupported on this hardware
        # (confirmed: nvmlDeviceGetPowerManagementLimit raises NotSupported).
        # Fall back to parsing the enforced cap out of the nvidia-smi table.
        # Deliberately NOT using nvmlDeviceGetPowerManagementDefaultLimit:
        # verified on this hardware to return 55W, the factory default,
        # not the 35W cap actually enforced - using it would misreport data.
        power_limit_w, power_limit_note = _power_cap_from_nvidia_smi()

        try:
            temperature_c = nvml.nvmlDeviceGetTemperature(
                handle, nvml.NVML_TEMPERATURE_GPU
            )
        except nvml.NVMLError:
            temperature_c = None

        try:
            util = nvml.nvmlDeviceGetUtilizationRates(handle)
            gpu_util: float | None = int(util.gpu)
            mem_util: float | None = int(util.memory)
        except nvml.NVMLError:
            gpu_util = None
            mem_util = None

        try:
            uuid = nvml.nvmlDeviceGetUUID(handle)
        except nvml.NVMLError:
            uuid = None

        processes, process_util_available = _processes_via_nvml(handle)

        return GPUInfo(
            available=True,
            source="nvml",
            name=name,
            driver_version=driver_version,
            cuda_version=cuda_version,
            uuid=uuid,
            vram_total_mb=_bytes_to_mb(int(mem.total)),
            vram_used_mb=_bytes_to_mb(int(mem.used)),
            vram_free_mb=_bytes_to_mb(int(mem.free)),
            gpu_utilization_percent=gpu_util,
            memory_utilization_percent=mem_util,
            power_draw_w=power_draw_w,
            power_draw_available=power_draw_available,
            power_limit_w=power_limit_w,
            power_limit_available=power_limit_w is not None,
            power_limit_note=power_limit_note,
            temperature_c=temperature_c,
            processes=processes,
            process_utilization_available=process_util_available,
        )
    finally:
        nvml.nvmlShutdown()


def _detect_via_nvidia_smi_csv() -> GPUInfo:
    """Fallback path when NVML bindings are unavailable entirely."""
    fields = [
        "name",
        "driver_version",
        "memory.total",
        "memory.used",
        "memory.free",
        "power.draw",
        "temperature.gpu",
        "utilization.gpu",
        "utilization.memory",
        "uuid",
    ]
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={','.join(fields)}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_S,
            check=True,
        )
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
    ) as exc:
        return GPUInfo(available=False, source="unavailable", error=str(exc))

    values = [v.strip() for v in result.stdout.strip().split(",")]
    if len(values) != len(fields):
        return GPUInfo(
            available=False,
            source="unavailable",
            error="unexpected nvidia-smi CSV output shape",
        )
    data = dict(zip(fields, values))

    def parse_float(raw: str) -> float | None:
        try:
            return float(raw)
        except ValueError:
            return None

    power_limit_w, power_limit_note = _power_cap_from_nvidia_smi()
    power_draw_w = parse_float(data["power.draw"])

    mem_total_mib = parse_float(data["memory.total"])
    mem_used_mib = parse_float(data["memory.used"])
    mem_free_mib = parse_float(data["memory.free"])

    return GPUInfo(
        available=True,
        source="nvidia-smi",
        name=data["name"] or None,
        driver_version=data["driver_version"] or None,
        cuda_version=None,  # not exposed via CSV query; needs table parse
        uuid=data["uuid"] or None,
        vram_total_mb=_mib_to_mb(mem_total_mib) if mem_total_mib is not None else None,
        vram_used_mb=_mib_to_mb(mem_used_mib) if mem_used_mib is not None else None,
        vram_free_mb=_mib_to_mb(mem_free_mib) if mem_free_mib is not None else None,
        gpu_utilization_percent=parse_float(data["utilization.gpu"]),
        memory_utilization_percent=parse_float(data["utilization.memory"]),
        power_draw_w=power_draw_w,
        power_draw_available=power_draw_w is not None,
        power_limit_w=power_limit_w,
        power_limit_available=power_limit_w is not None,
        power_limit_note=power_limit_note,
        temperature_c=parse_float(data["temperature.gpu"]),
        processes=[],
        process_utilization_available=False,
    )


def open_gpu_handle():
    """Initialize NVML once for a polling session and return a device handle.

    Returns None if NVML is unavailable - callers (the telemetry loop) must
    treat None as "GPU unavailable" for every sample rather than retrying
    nvmlInit() every second, which would be exactly the per-poll overhead
    Section 22 warns against.
    """
    if nvml is None:
        return None
    try:
        nvml.nvmlInit()
        return nvml.nvmlDeviceGetHandleByIndex(0)
    except nvml.NVMLError:
        return None


def close_gpu_handle(handle) -> None:
    if handle is not None:
        assert nvml is not None  # a non-None handle only ever came from nvml
        try:
            nvml.nvmlShutdown()
        except nvml.NVMLError:
            pass


def sample_gpu(handle) -> GPUSample:
    """Lightweight per-poll GPU reading for an already-open NVML handle.

    Deliberately skips static fields (name, driver/cuda version, uuid, power
    cap) that don't change during a session and are already reported once by
    /api/gpu/info - re-fetching them every second would be wasted work.
    Never raises: any NVML failure degrades to an unavailable sample.
    """
    if handle is None:
        return GPUSample(available=False, error="NVML not initialized for this session")

    assert nvml is not None  # a non-None handle only ever came from nvml

    try:
        mem = nvml.nvmlDeviceGetMemoryInfo(handle)
    except nvml.NVMLError as exc:
        return GPUSample(available=False, error=str(exc))

    try:
        power_draw_w = nvml.nvmlDeviceGetPowerUsage(handle) / 1000
    except nvml.NVMLError:
        power_draw_w = None

    try:
        temperature_c = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
    except nvml.NVMLError:
        temperature_c = None

    gpu_util: float | None
    mem_util: float | None
    try:
        util = nvml.nvmlDeviceGetUtilizationRates(handle)
        gpu_util, mem_util = int(util.gpu), int(util.memory)
    except nvml.NVMLError:
        gpu_util, mem_util = None, None

    processes, process_util_available = _processes_via_nvml(handle)

    return GPUSample(
        available=True,
        vram_used_mb=_bytes_to_mb(int(mem.used)),
        gpu_utilization_percent=gpu_util,
        memory_utilization_percent=mem_util,
        power_draw_w=power_draw_w,
        temperature_c=temperature_c,
        processes=processes,
        process_utilization_available=process_util_available,
    )


def detect_gpu() -> GPUInfo:
    """Detect the primary GPU and its current metrics.

    Never raises - any failure is reported as an unavailable/degraded
    GPUInfo so the rest of the app can handle it gracefully.
    """
    if nvml is not None:
        try:
            return _detect_via_nvml()
        except nvml.NVMLError as exc:
            return GPUInfo(available=False, source="unavailable", error=str(exc))
        except Exception as exc:  # unexpected - still degrade, never crash
            return GPUInfo(available=False, source="unavailable", error=str(exc))

    return _detect_via_nvidia_smi_csv()
