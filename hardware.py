from __future__ import annotations
import json
import platform
import re
import subprocess
import psutil

# hardware decetion for Local-LLM-Advisor
# returns a fixed shape dictionary consumed by all downstream components
# CPU, RAM, NVIDIA, AMD, and macOS (Apple/integrated) GPU detection 

_GB = 1024**3
_APPLE_SILICON_RE = re.compile(r"Apple M\d", re.IGNORECASE)
_GPU_NOT_DETECTED = {"model": "not_detected", "vram_gb": 0.0, "vendor": "unknown"}
_VRAM_TOTAL_KEYS = frozenset({"memory_total", "total memory (b)", "vram total memory (b)"})

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

def _detect_nvidia_gpus() -> list[dict[str, float | str]]:
    gpus = _detect_gpu_via_gputil()
    if gpus:
        return gpus
    return _detect_gpu_via_nvidia_smi()

def _extract_vram_total_bytes(node: object) -> float | None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in _VRAM_TOTAL_KEYS:
                try:
                    total = float(value)
                except (TypeError, ValueError):
                    continue
                if total > 0:
                    return total
            found = _extract_vram_total_bytes(value)
            if found is not None:
                return found
    return None

def _detect_gpu_via_rocm_smi() -> list[dict[str, float | str]]:
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, dict):
        return []

    gpus: list[dict[str, float | str]] = []
    for device_id, device_data in data.items():
        if not isinstance(device_data, dict):
            continue
        vram_bytes = _extract_vram_total_bytes(device_data)
        if vram_bytes is None:
            continue
        gpus.append(
            {
                "model": device_id,
                "vram_gb": round(vram_bytes / _GB, 2),
                "vendor": "amd",
            }
        )
    return gpus

def _parse_memory_size_to_gb(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None

    match = re.search(r"([\d.]+)\s*(TB|GB|MB|G|M|T)?\b", text, re.IGNORECASE)
    if not match:
        return None

    try:
        value = float(match.group(1))
    except ValueError:
        return None

    unit = (match.group(2) or "MB").upper()
    if unit.startswith("T"):
        gb = value * 1024
    elif unit.startswith("G"):
        gb = value
    else:
        gb = value / 1024

    return round(gb, 2) if gb > 0 else None

def _is_apple_silicon_gpu(model: str) -> bool:
    return bool(_APPLE_SILICON_RE.search(model))

def _normalize_profiler_vendor(vendor: str, model: str) -> str:
    vendor = re.sub(r"\s*\(0x[0-9a-fA-F]+\)", "", vendor).strip()
    combined = f"{vendor} {model}".lower()
    if "apple" in combined or _is_apple_silicon_gpu(model):
        return "apple"
    if "intel" in combined:
        return "intel"
    if "amd" in combined or "radeon" in combined:
        return "amd"
    if "nvidia" in combined:
        return "nvidia"
    return "unknown"


def _build_profiler_gpu_entry(
    chipset_model: str, # the gpu model name
    vendor_raw: str, # the gpu vendor name
    vram_total_text: str, # the total vram size in text format
    vram_dynamic_text: str, # the dynamic vram size in text format
) -> dict[str, float | str]:

    if _is_apple_silicon_gpu(chipset_model):
        return {
            "model": f"{chipset_model} (unified memory)",
            "vram_gb": round(_detect_ram()["total_gb"] * 0.75, 2),
            "vendor": "apple",
        }

    has_dedicated_vram = bool(vram_total_text.strip())
    vram_gb: float | None = None
    if has_dedicated_vram:
        vram_gb = _parse_memory_size_to_gb(vram_total_text)
    elif vram_dynamic_text.strip():
        vram_gb = _parse_memory_size_to_gb(vram_dynamic_text)
    if vram_gb is None:
        vram_gb = _detect_ram()["total_gb"]

    if has_dedicated_vram:
        model = chipset_model
    else:
        model = f"{chipset_model} (VRAM shared with system RAM)"

    return {
        "model": model,
        "vram_gb": vram_gb,
        "vendor": _normalize_profiler_vendor(vendor_raw, chipset_model),
    }

def _detect_gpu_via_system_profiler() -> list[dict[str, float | str]]:
    try:
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    gpus: list[dict[str, float | str]] = []
    chipset_model = ""
    vendor_raw = ""
    vram_total_text = ""
    vram_dynamic_text = ""

    def flush() -> None:
        nonlocal chipset_model, vendor_raw, vram_total_text, vram_dynamic_text
        if chipset_model.strip():
            gpus.append(
                _build_profiler_gpu_entry(
                    chipset_model.strip(),
                    vendor_raw,
                    vram_total_text,
                    vram_dynamic_text,
                )
            )
        chipset_model = ""
        vendor_raw = ""
        vram_total_text = ""
        vram_dynamic_text = ""

    for line in result.stdout.splitlines():
        stripped = line.strip()
        chipset_match = re.match(r"Chipset Model:\s*(.*)", stripped)
        if chipset_match:
            flush()
            chipset_model = chipset_match.group(1)
            continue
        if not chipset_model:
            continue
        vendor_match = re.match(r"Vendor:\s*(.*)", stripped)
        if vendor_match:
            vendor_raw = vendor_match.group(1)
            continue
        vram_total_match = re.match(r"VRAM \(Total\):\s*(.*)", stripped)
        if vram_total_match:
            vram_total_text = vram_total_match.group(1)
            continue
        vram_dynamic_match = re.match(r"VRAM \(Dynamic, Max\):\s*(.*)", stripped)
        if vram_dynamic_match:
            vram_dynamic_text = vram_dynamic_match.group(1)

    flush()
    return gpus

def _detect_gpu() -> list[dict[str, float | str]]:
    gpus = _detect_nvidia_gpus()
    if gpus:
        return gpus
    gpus = _detect_gpu_via_rocm_smi()
    if gpus:
        return gpus
    if platform.system() == "Darwin":
        gpus = _detect_gpu_via_system_profiler()
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
    print(json.dumps(detect_hardware(), indent=2))