from __future__ import annotations
import platform
import subprocess
import psutil

# hardware decetion for Local-LLM-Advisor
# returns a fixed shape dictionary consumed by all downstream components
# GPU and OS decetion are stubbed until later phases

_GB = 1024**3
_GPU_NOT_DETECTED = {"model": "not_detected", "vram_gb": 0.0, "vendor": "unknown"}

def _detect_cpu() -> dict[str, int | str]:
    model = platform.processor().strip()
    if not model:
        model = _cpu_model_from_cpuinfo()

    threads = psutil.cpu_count(logical=True) or 1
    cores = psutil.cpu_count(logical=False) or threads

    return {"model": model, "cores": cores, "threads": threads}

def _cpu_model_from_cpuinfo() -> str:
    try:
        import cpuinfo

        info = cpuinfo.get_cpu_info()
        return info.get("brand_raw") or info.get("brand") or "Unknown"
    except Exception:
        return "Unknown"

def _detect_ram() -> dict[str, float]:
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / _GB, 2),
        "available_gb": round(mem.available / _GB, 2),
    }

def _detect_gpu_via_gputil() -> list[dict[str, float | str]]:
    try:
        import GPUtil

        gpus = GPUtil.getGPUs()
        if not gpus:
            return []
        return [
            {
                "model": gpu.name,
                "vram_gb": round(gpu.memoryTotal / 1024, 2),
                "vendor": "nvidia",
            }
            for gpu in gpus
        ]
    except Exception:
        return []

def _detect_gpu_via_nvidia_smi() -> list[dict[str, float | str]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    gpus: list[dict[str, float | str]] = []
    for line in result.stdout.strip().splitlines():
        parts = [part.strip() for part in line.split(",", 1)]
        if len(parts) != 2:
            continue
        name, vram_mib = parts
        try:
            vram_gb = round(float(vram_mib) / 1024, 2)
        except ValueError:
            continue
        gpus.append({"model": name, "vram_gb": vram_gb, "vendor": "nvidia"})
    return gpus

def _detect_gpu() -> list[dict[str, float | str]]:
    gpus = _detect_gpu_via_gputil()
    if gpus:
        return gpus
    gpus = _detect_gpu_via_nvidia_smi()
    if gpus:
        return gpus
    return [_GPU_NOT_DETECTED.copy()]

def detect_hardware() -> dict[str, object]:
    return {
        "cpu": _detect_cpu(),
        "ram": _detect_ram(),
        "gpu": _detect_gpu(),
        "os": {"name": "", "version": "", "arch": ""},
    }

if __name__ == "__main__":
    import json

    print(json.dumps(detect_hardware(), indent=2))