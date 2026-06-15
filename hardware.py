"""Hardware detection for Local-LLM-Advisor.

Returns a fixed-shape dictionary consumed by all downstream components.
GPU and OS detection are stubbed until later phases.
"""

from __future__ import annotations
import platform
import psutil

# hardware decetion for Local-LLM-Advisor
# returns a fixed shape dictionary consumed by all downstream components
# GPU and OS decetion are stubbed until later phases

_GB = 1024**3

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

def detect_hardware() -> dict[str, object]:
    return {
        "cpu": _detect_cpu(),
        "ram": _detect_ram(),
        "gpu": [],
        "os": {"name": "", "version": "", "arch": ""},
    }

if __name__ == "__main__":
    import json

    print(json.dumps(detect_hardware(), indent=2))