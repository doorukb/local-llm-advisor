from __future__ import annotations
from fetch import FetchResult, ModelEntry

OLLAMA_UNAVAILABLE_NOTE = (
    "Live Ollama library data could not be fetched (network error or timeout). "
    "Use your training knowledge of current popular Ollama models for Ollama recommendations."
)
HUGGINGFACE_UNAVAILABLE_NOTE = (
    "Live Hugging Face GGUF catalog data could not be fetched (network error or timeout). "
    "Use your training knowledge of popular GGUF models for llama.cpp / LM Studio recommendations."
)

def _format_model_list(title: str, models: list[ModelEntry]) -> str:
    lines = [title + ":"]
    for model in models:
        sizes = ", ".join(model["parameter_sizes"]) or "unknown"
        families = ", ".join(model["families"])
        lines.append(
            f"- {model['name']} | sizes: {sizes} | families: {families} | {model['description']}"
        )
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