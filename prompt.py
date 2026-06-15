from __future__ import annotations
from typing import TypedDict
from fetch import FetchResult, ModelEntry

OLLAMA_UNAVAILABLE_NOTE = (
    "Live Ollama library data could not be fetched (network error or timeout). "
    "Use your training knowledge of current popular Ollama models for Ollama recommendations."
)
HUGGINGFACE_UNAVAILABLE_NOTE = (
    "Live Hugging Face GGUF catalog data could not be fetched (network error or timeout). "
    "Use your training knowledge of popular GGUF models for llama.cpp / LM Studio recommendations."
)

class CpuInfo(TypedDict):
    model: str
    cores: int
    threads: int

class RamInfo(TypedDict):
    total_gb: float
    available_gb: float

class GpuInfo(TypedDict):
    model: str
    vram_gb: float
    vendor: str

class OsInfo(TypedDict):
    name: str
    version: str
    arch: str

class HardwareSnapshot(TypedDict):
    cpu: CpuInfo
    ram: RamInfo
    gpu: list[GpuInfo]
    os: OsInfo

class UserSelections(TypedDict):
    inference_engine: str
    primary_use_case: str
    context_length: str
    performance_priority: str

_VENDOR_LABELS = {
    "nvidia": "NVIDIA",
    "amd": "AMD",
    "apple": "Apple",
}

def _vendor_display(vendor: str) -> str:
    return _VENDOR_LABELS.get(vendor.lower(), "")

def _is_gpu_not_detected(gpu: GpuInfo) -> bool:
    return gpu["model"] == "not_detected"

def _format_gpu_line(gpu: GpuInfo) -> str:
    vendor_label = _vendor_display(gpu["vendor"])
    model = gpu["model"]
    prefix = f"{vendor_label} " if vendor_label else ""
    if "shared with system RAM" in model:
        return f"- {prefix}{model} ({gpu['vram_gb']} GB reported)"
    return f"- {prefix}{model} with {gpu['vram_gb']} GB VRAM"

def _format_gpu_section(gpus: list[GpuInfo]) -> str:
    if len(gpus) == 1 and _is_gpu_not_detected(gpus[0]):
        return (
            "Graphics: No discrete GPU was detected on this system. "
            "Recommendations should assume CPU-only inference using system RAM."
        )

    if len(gpus) == 1:
        gpu = gpus[0]
        vendor_label = _vendor_display(gpu["vendor"])
        model = gpu["model"]
        prefix = f"{vendor_label} " if vendor_label else ""
        if "shared with system RAM" in model:
            return f"Graphics: {prefix}{model} ({gpu['vram_gb']} GB reported)."
        return f"Graphics: {prefix}{model} with {gpu['vram_gb']} GB dedicated VRAM."

    lines = ["Graphics:"]
    lines.extend(_format_gpu_line(gpu) for gpu in gpus)
    return "\n".join(lines)

def _format_os_line(os_info: OsInfo) -> str | None:
    name = os_info["name"].strip()
    version = os_info["version"].strip()
    arch = os_info["arch"].strip()
    if not name and not version and not arch:
        return None

    parts = [part for part in (name, version) if part]
    platform_text = " ".join(parts)
    if arch:
        platform_text = f"{platform_text} ({arch})" if platform_text else f"({arch})"
    return f"Platform: {platform_text}."

def format_hardware_context(hardware: HardwareSnapshot) -> str:
    cpu = hardware["cpu"]
    ram = hardware["ram"]

    lines = ["## Detected Hardware", ""]

    os_line = _format_os_line(hardware["os"])
    if os_line:
        lines.append(os_line)

    lines.append(f"Processor: {cpu['model']} with {cpu['cores']} physical cores and {cpu['threads']} logical threads.")
    lines.append(f"System memory: {ram['total_gb']} GB total, {ram['available_gb']} GB currently available.")
    lines.append(_format_gpu_section(hardware["gpu"]))
    return "\n".join(lines)

def format_selections_context(selections: UserSelections) -> str:
    return "\n".join(
        [
            "## User Preferences",
            "",
            "The user selected the following fixed options (do not infer alternatives):",
            "",
            f"- Inference engine: {selections['inference_engine']}",
            f"- Primary use case: {selections['primary_use_case']}",
            f"- Context length preference: {selections['context_length']}",
            f"- Performance priority: {selections['performance_priority']}",
        ]
    )

def _format_model_list(title: str, models: list[ModelEntry]) -> str:
    lines = [title + ":"]
    for model in models:
        sizes = ", ".join(model["parameter_sizes"]) or "unknown"
        families = ", ".join(model["families"])
        lines.append(f"- {model['name']} | sizes: {sizes} | families: {families} | {model['description']}")
    return "\n".join(lines)

def format_live_model_context(fetch_result: FetchResult) -> str:
    sections: list[str] = []

    if not fetch_result["ollama_available"]:
        sections.append(OLLAMA_UNAVAILABLE_NOTE)
    elif fetch_result["ollama"]:
        sections.append(_format_model_list("Ollama library", fetch_result["ollama"]))

    if not fetch_result["huggingface_available"]:
        sections.append(HUGGINGFACE_UNAVAILABLE_NOTE)
    elif fetch_result["huggingface"]:
        sections.append(_format_model_list("Hugging Face GGUF", fetch_result["huggingface"]))

    return "\n\n".join(sections)

if __name__ == "__main__":
    from hardware import detect_hardware

    hardware = detect_hardware()
    selections: UserSelections = {
        "inference_engine": "Ollama",
        "primary_use_case": "Coding assistant",
        "context_length": "Medium (8K-16K)",
        "performance_priority": "Balanced",
    }
    print(format_hardware_context(hardware))
    print()
    print(format_selections_context(selections))