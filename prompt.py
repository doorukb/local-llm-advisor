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

OLLAMA_ENGINE = "Ollama"  # must match gui.INFERENCE_ENGINES[0]

_OLLAMA_USE_CASE_GUIDANCE = {
    "General chat": "temperature 0.7, top_p 0.9; friendly conversational SYSTEM prompt",
    "Coding assistant": "temperature 0.2-0.3, top_p 0.95; SYSTEM prompt emphasizing precise, runnable code",
    "Document Q&A": "temperature 0.3, top_p 0.9; SYSTEM prompt for grounded, citation-style answers",
    "Creative writing": "temperature 0.8-0.9, top_p 0.95; SYSTEM prompt encouraging vivid prose",
    "Summarization": "temperature 0.3, top_p 0.85; SYSTEM prompt for concise, factual summaries",
}

_OLLAMA_CONTEXT_GUIDANCE = {
    "Short (2K-4K)": "Recommend num_ctx 2048-4096; note this minimizes VRAM use",
    "Medium (8K-16K)": "Recommend num_ctx 8192-16384; balance context vs VRAM",
    "Long (32K+)": "Recommend num_ctx 32768+ only when VRAM/RAM supports it; warn if hardware is insufficient",
}

LLAMA_CPP_ENGINE = "llama.cpp"  # must match gui.INFERENCE_ENGINES[1]

_LLAMA_CPP_USE_CASE_GUIDANCE = {
    "General chat": "--temp 0.7 --top-p 0.9; conversational system prompt",
    "Coding assistant": "--temp 0.2 --top-p 0.95; system prompt for precise, runnable code",
    "Document Q&A": "--temp 0.3 --top-p 0.9; system prompt for grounded answers",
    "Creative writing": "--temp 0.85 --top-p 0.95; system prompt for vivid prose",
    "Summarization": "--temp 0.3 --top-p 0.85; system prompt for concise summaries",
}

_LLAMA_CPP_CONTEXT_GUIDANCE = {
    "Short (2K-4K)": "Set -c 2048-4096; minimizes KV-cache VRAM",
    "Medium (8K-16K)": "Set -c 8192-16384; balance context vs VRAM",
    "Long (32K+)": "Set -c 32768+ only when VRAM/RAM supports it; reduce -c if OOM risk",
}

_LLAMA_CPP_PERFORMANCE_GUIDANCE = {
    "Speed (tokens/sec)": "Favor higher -ngl when VRAM allows, smaller quant (Q4), lower -c if needed",
    "Quality (best output at hardware limits)": "Favor higher quant (Q5/Q8) within VRAM; max sensible -ngl",
    "Balanced": "Balance -ngl, quant, and -c for stable throughput and quality",
}

LM_STUDIO_ENGINE = "LM Studio"  # must match gui.INFERENCE_ENGINES[2]

_LM_STUDIO_USE_CASE_GUIDANCE = {
    "General chat": "Temperature ~0.7, Top P ~0.9; friendly system prompt in Chat settings",
    "Coding assistant": "Temperature ~0.2, Top P ~0.95; system prompt for precise, runnable code",
    "Document Q&A": "Temperature ~0.3, Top P ~0.9; system prompt for grounded answers",
    "Creative writing": "Temperature ~0.85, Top P ~0.95; system prompt for vivid prose",
    "Summarization": "Temperature ~0.3, Top P ~0.85; system prompt for concise summaries",
}

_LM_STUDIO_CONTEXT_GUIDANCE = {
    "Short (2K-4K)": "Context Length 2048-4096; minimizes KV-cache VRAM in LM Studio",
    "Medium (8K-16K)": "Context Length 8192-16384; balance context vs VRAM",
    "Long (32K+)": "Context Length 32768+ only when VRAM/RAM supports it; reduce if load fails",
}

_LM_STUDIO_PERFORMANCE_GUIDANCE = {
    "Speed (tokens/sec)": "Maximize GPU offload layers when VRAM allows; prefer Q4 quant; lower context if needed",
    "Quality (best output at hardware limits)": "Prefer Q5/Q8 within VRAM; max sensible GPU layer offload",
    "Balanced": "Balance GPU layers, quant, and context for stable throughput and quality",
}

SYSTEM_PROMPT = """You are Local LLM Advisor, a hardware-aware expert that recommends local inference models and concrete setup steps. Reason only over the hardware, user preferences, and model catalog provided in the user message.

Your task is to produce exactly one structured report. Use live catalog data when present. Fall back to training knowledge only when the user message states that a catalog was unavailable.

## Required report format

Output markdown using exactly this structure:

# Local LLM Advisor Report

## Executive Summary
Write 2-4 sentences covering hardware constraints, the top recommendation, and the key tradeoff.

## Recommended Models
Rank models best to worst fit for this hardware and preferences. Include at least one recommendation if any model can run. Recommend 3-5 models when possible; recommend fewer if hardware is very limited. Never invent models not supported by the catalog or your training knowledge.

### 1. Model name (quantization)
- **Estimated speed:** tokens per second on this hardware
- **Memory:** VRAM and/or RAM estimate
- **Why this model:** hardware-grounded rationale tied to user preferences
- **Engine setup:** all fields required by the Output Requirements section in the user message

### 2. (repeat for each additional recommendation)

## Not Recommended
List models considered from the catalog but poor fits. One brief bullet per model with a hardware-based reason.

## Hardware Notes
Provide 1-3 bullets summarizing binding constraints from the detected hardware (VRAM ceiling, CPU-only operation, context limits).

For each model under **Engine setup**, include every item listed in the ## Ollama Output Requirements, ## llama.cpp Output Requirements, or ## LM Studio Output Requirements section of the user message (whichever is present).

## Output constraints

- Output only the report. No preamble, postamble, greetings, or sign-off.
- No conversational language or follow-up questions.
- No meta disclaimers. Do not mention being an AI, knowledge cutoffs, inability to browse, or uncertainty about your own capabilities.
- No content outside the headings defined above.
- Markdown report only. No JSON, XML, or other formats.
- Do not request more information from the user.
- If data is missing, state facts inside the report sections. Do not refuse or apologize."""

def get_system_prompt() -> str:
    return SYSTEM_PROMPT

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

def format_ollama_output_instructions(selections: UserSelections) -> str | None:
    if selections["inference_engine"] != OLLAMA_ENGINE:
        return None

    use_case = selections["primary_use_case"]
    context_pref = selections["context_length"]
    use_case_guidance = _OLLAMA_USE_CASE_GUIDANCE.get(use_case,
        "temperature 0.7, top_p 0.9; SYSTEM prompt suited to the selected use case",
    )
    context_guidance = _OLLAMA_CONTEXT_GUIDANCE.get(context_pref,
        "Recommend num_ctx appropriate for the user's context preference and hardware",
    )

    return "\n".join(
        [
            "## Ollama Output Requirements",
            "",
            "The user selected Ollama as their inference engine. For every model you recommend, "
            "include a dedicated subsection titled with the model name containing all three items below.",
            "",
            "### Per recommended model",
            "",
            "1. Pull command",
            "   - Provide the exact shell command: `ollama pull <model>:<tag>`",
            "   - Use model names/tags from the live Ollama library data when available.",
            "   - Present the command in a markdown code block in your report.",
            "",
            f"2. Modelfile configuration (use case: {use_case})",
            "   - Provide a Modelfile snippet or `ollama create -f Modelfile` workflow.",
            f"   - Include PARAMETER lines appropriate for this use case: {use_case_guidance}",
            "   - Include a SYSTEM block suited to the use case.",
            "   - Present the Modelfile in a markdown code block in your report.",
            "",
            f"3. Context window configuration (preference: {context_pref})",
            f"   - {context_guidance}",
            "   - Show how to set context via `PARAMETER num_ctx` in the Modelfile, the "
            "`OLLAMA_NUM_CTX` environment variable, or `ollama run` options.",
            "   - Tie the recommendation to the user's detected VRAM/RAM; reduce num_ctx if "
            "hardware cannot support the preference.",
            "",
            "Do not recommend models the hardware cannot run at the suggested context size. "
            "If a model fits only at a lower context, state the tradeoff explicitly.",
        ]
    )

def format_llama_cpp_output_instructions(selections: UserSelections) -> str | None:
    if selections["inference_engine"] != LLAMA_CPP_ENGINE:
        return None

    use_case = selections["primary_use_case"]
    context_pref = selections["context_length"]
    performance = selections["performance_priority"]
    use_case_guidance = _LLAMA_CPP_USE_CASE_GUIDANCE.get(use_case,
        "--temp 0.7 --top-p 0.9; system prompt suited to the selected use case",
    )
    context_guidance = _LLAMA_CPP_CONTEXT_GUIDANCE.get(context_pref,
        "Set -c appropriate for the user's context preference and hardware",
    )
    performance_guidance = _LLAMA_CPP_PERFORMANCE_GUIDANCE.get(performance,
        "Balance -ngl, quant, and -c for stable throughput and quality",
    )

    return "\n".join(
        [
            "## llama.cpp Output Requirements",
            "",
            "The user selected llama.cpp as their inference engine. For every model you recommend, "
            "include a dedicated subsection titled with the model name containing all items below. "
            "Use GGUF model paths/names from the Hugging Face catalog data when available.",
            "",
            "### Per recommended model",
            "",
            "1. Run command",
            "   - Provide a complete `./llama-cli` command (interactive) OR `./llama-server` command (API), "
            "including the path or filename of the recommended GGUF quantization.",
            "   - Include at minimum: -m, -ngl, -c, -t, and flags appropriate for the use case and hardware.",
            "   - Also consider when relevant: --mlock, -b, -n, --temp, --top-p, --repeat-penalty.",
            "   - Present the command in a markdown code block in your report.",
            "",
            f"2. Flag explanations (use case: {use_case}; performance: {performance})",
            "   - After the command, explain each flag in plain language tied to the user's detected CPU, "
            "RAM, and GPU/VRAM from the hardware section.",
            f"   - Sampling guidance for this use case: {use_case_guidance}",
            f"   - Performance tuning guidance: {performance_guidance}",
            "",
            f"3. Context window (preference: {context_pref})",
            f"   - {context_guidance}",
            "   - Explain how -c interacts with KV-cache memory on this hardware.",
            "",
            "4. n-gpu-layers (-ngl) tuning",
            "   - Recommend a specific -ngl value for the user's VRAM (or state -ngl 0 for CPU-only).",
            "   - Explain the tradeoff between raising -ngl (faster, more VRAM) and lowering it "
            "(slower, fits larger models/context).",
            "   - If no discrete GPU was detected, recommend CPU-only settings and realistic "
            "throughput expectations.",
            "",
            "Do not recommend GGUF quants the hardware cannot load. If only a lower quant or smaller -c "
            "fits, state the tradeoff explicitly.",
        ]
    )

def format_lm_studio_output_instructions(selections: UserSelections) -> str | None:
    if selections["inference_engine"] != LM_STUDIO_ENGINE:
        return None

    use_case = selections["primary_use_case"]
    context_pref = selections["context_length"]
    performance = selections["performance_priority"]
    use_case_guidance = _LM_STUDIO_USE_CASE_GUIDANCE.get(
        use_case,
        "Temperature ~0.7, Top P ~0.9; system prompt suited to the selected use case",
    )
    context_guidance = _LM_STUDIO_CONTEXT_GUIDANCE.get(
        context_pref,
        "Set Context Length appropriate for the user's context preference and hardware",
    )
    performance_guidance = _LM_STUDIO_PERFORMANCE_GUIDANCE.get(
        performance,
        "Balance GPU layers, quant, and context for stable throughput and quality",
    )

    return "\n".join(
        [
            "## LM Studio Output Requirements",
            "",
            "The user selected LM Studio as their inference engine. For every model you recommend, "
            "include a dedicated subsection titled with the model name containing all items below. "
            "Use GGUF repo names and quant labels from the Hugging Face catalog data when available.",
            "",
            "### Per recommended model",
            "",
            "1. Model search terms",
            "   - Provide exact search strings for LM Studio's Discover / model search panel "
            "(e.g. Hugging Face repo id, model family name, parameter size, quantization such as Q4_K_M).",
            "   - List 2-4 alternative search terms if the primary name may not appear.",
            "",
            f"2. Loader settings (use case: {use_case}; performance: {performance})",
            "   - Recommend which GGUF quantization file to select when multiple are available.",
            "   - Specify loader options: GPU layers to offload, CPU thread count, batch size, and "
            "whether to enable flash attention / mmap when appropriate for this hardware.",
            f"   - Sampling guidance for this use case: {use_case_guidance}",
            f"   - Performance tuning guidance: {performance_guidance}",
            "   - Reference the user's detected CPU, RAM, and GPU/VRAM from the hardware section.",
            "",
            f"3. Context and GPU offload configuration (preference: {context_pref})",
            f"   - {context_guidance}",
            "   - Explain how to set Context Length in LM Studio's load or chat settings.",
            "   - Recommend GPU layer offload (or full CPU mode if no discrete GPU) for the user's VRAM.",
            "   - Describe the tradeoff between more GPU layers (faster, more VRAM) vs fewer layers "
            "(slower, fits larger models or longer context).",
            "",
            "Do not recommend GGUF quants the hardware cannot load. If only a lower quant, fewer GPU "
            "layers, or shorter context fits, state the tradeoff explicitly.",
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
    print()
    ollama_instructions = format_ollama_output_instructions(selections)
    if ollama_instructions:
        print(ollama_instructions)

    llama_cpp_selections: UserSelections = {
        **selections,
        "inference_engine": "llama.cpp",
    }
    assert format_ollama_output_instructions(llama_cpp_selections) is None

    print("--- llama.cpp engine demo ---")
    print(format_hardware_context(hardware))
    print()
    print(format_selections_context(llama_cpp_selections))
    print()
    llama_cpp_instructions = format_llama_cpp_output_instructions(llama_cpp_selections)
    if llama_cpp_instructions:
        print(llama_cpp_instructions)
    assert format_llama_cpp_output_instructions(selections) is None

    lm_studio_selections: UserSelections = {
        **selections,
        "inference_engine": "LM Studio",
    }
    assert format_lm_studio_output_instructions(lm_studio_selections) is not None
    assert format_lm_studio_output_instructions(selections) is None
    assert format_lm_studio_output_instructions(llama_cpp_selections) is None

    print("--- LM Studio engine demo ---")
    print(format_hardware_context(hardware))
    print()
    print(format_selections_context(lm_studio_selections))
    print()
    lm_studio_instructions = format_lm_studio_output_instructions(lm_studio_selections)
    if lm_studio_instructions:
        print(lm_studio_instructions)

    print("--- system prompt preview ---")
    system_prompt = get_system_prompt()
    assert len(system_prompt) > 500
    assert "Local LLM Advisor Report" in system_prompt
    assert "Recommended Models" in system_prompt
    assert "follow-up questions" in system_prompt.lower()
    assert "conversational" in system_prompt.lower()
    assert "disclaimer" in system_prompt.lower()
    print(system_prompt)