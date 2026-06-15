from __future__ import annotations
import html
import re
from typing import TypedDict
import requests

# ollama library url and parameters

OLLAMA_LIBRARY_URL = "https://ollama.com/library"
OLLAMA_LIBRARY_PARAMS = {"sort": "popular"}
REQUEST_TIMEOUT = 10

_ollama_fetch_available: bool = True
_huggingface_fetch_available: bool = True

_CARD_PATTERN = re.compile(r"<li x-test-model\b.*?</li>", re.DOTALL)
_TITLE_PATTERN = re.compile(r'x-test-model-title[^>]*\btitle="([^"]+)"')
_DESCRIPTION_PATTERN = re.compile(r'<p class="max-w-lg break-words text-neutral-800 text-md">(.*?)</p>', re.DOTALL)
_SIZE_PATTERN = re.compile(r"x-test-size[^>]*>([^<]+)</span>")
_CAPABILITY_PATTERN = re.compile(r"x-test-capability[^>]*>([^<]+)</span>")
_FAMILY_PATTERN = re.compile(r"^([a-zA-Z]+)")

# model entry for Local-LLM-Advisor
class OllamaModelEntry(TypedDict):
    name: str
    parameter_sizes: list[str]
    families: list[str]
    description: str

ModelEntry = OllamaModelEntry

class FetchResult(TypedDict):
    ollama: list[ModelEntry]
    huggingface: list[ModelEntry]
    ollama_available: bool
    huggingface_available: bool

def ollama_fetch_available() -> bool:
    return _ollama_fetch_available

def huggingface_fetch_available() -> bool:
    return _huggingface_fetch_available

HF_API_MODELS_URL = "https://huggingface.co/api/models"
HF_ARCHITECTURE_FAMILIES = ("llama", "mistral", "qwen", "phi", "gemma", "deepseek")
HF_MODELS_PER_FAMILY = 20
HF_USER_AGENT = "Local-LLM-Advisor/1.0"

_QUANT_PATTERN = re.compile(r"(?:IQ\d+_[A-Z0-9]+|UD-Q\d+_[A-Z0-9]+|Q\d+[_A-Z0-9]+)", re.IGNORECASE)
_PARAM_SIZE_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*[bB]\b")

class _ParsedOllamaCard(TypedDict):
    name: str
    parameter_sizes: list[str]
    families: list[str]
    description: str
    capabilities: list[str]

def _infer_families(name: str) -> list[str]:
    match = _FAMILY_PATTERN.match(name)
    return [match.group(1).lower()] if match else [name]

def _is_embedding_only(name: str, capabilities: list[str]) -> bool:
    caps = {capability.lower() for capability in capabilities}
    if caps == {"embedding"}:
        return True
    if not caps and "embed" in name.lower():
        return True
    return False

def _dedupe_sizes(sizes: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for size in sizes:
        normalized = size.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique

def _fetch_ollama_library_html() -> str:
    response = requests.get(
        OLLAMA_LIBRARY_URL,
        params=OLLAMA_LIBRARY_PARAMS,
        headers={"HX-Request": "true", "User-Agent": "Local-LLM-Advisor/1.0"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.text

def _parse_ollama_library(html_text: str) -> list[_ParsedOllamaCard]:
    cards: list[_ParsedOllamaCard] = []

    for block in _CARD_PATTERN.findall(html_text):
        title_match = _TITLE_PATTERN.search(block)
        description_match = _DESCRIPTION_PATTERN.search(block)
        if not title_match or not description_match:
            continue

        name = title_match.group(1).strip()
        description = html.unescape(re.sub(r"\s+", " ", description_match.group(1))).strip()
        if not name or not description:
            continue

        parameter_sizes = _dedupe_sizes(_SIZE_PATTERN.findall(block))
        capabilities = [cap.strip().lower() for cap in _CAPABILITY_PATTERN.findall(block)]

        cards.append(
            {
                "name": name,
                "parameter_sizes": parameter_sizes,
                "families": _infer_families(name),
                "description": description,
                "capabilities": capabilities,
            }
        )

    return cards

def fetch_ollama_models() -> list[OllamaModelEntry]:
    global _ollama_fetch_available
    _ollama_fetch_available = True

    try:
        html_text = _fetch_ollama_library_html()
    except requests.RequestException:
        _ollama_fetch_available = False
        return []

    parsed = _parse_ollama_library(html_text)

    models: list[OllamaModelEntry] = []
    for card in parsed:
        if _is_embedding_only(card["name"], card["capabilities"]):
            continue
        models.append(
            {
                "name": card["name"],
                "parameter_sizes": card["parameter_sizes"],
                "families": card["families"],
                "description": card["description"],
            }
        )

    return models

def _list_gguf_filenames(siblings: list[dict]) -> list[str]:
    filenames: list[str] = []
    for sibling in siblings:
        filename = sibling.get("rfilename", "")
        if not filename.endswith(".gguf"):
            continue
        if filename.lower().startswith("mmproj-"):
            continue
        filenames.append(filename)
    return filenames

def _parse_quantizations(filenames: list[str]) -> list[str]:
    quants: list[str] = []
    seen: set[str] = set()
    for filename in filenames:
        for match in _QUANT_PATTERN.findall(filename):
            normalized = match.upper()
            if normalized not in seen:
                seen.add(normalized)
                quants.append(normalized)
    return quants

def _parse_parameter_sizes(repo_id: str, tags: list[str]) -> list[str]:
    sizes: list[str] = []
    for source in (repo_id, " ".join(tags)):
        for match in _PARAM_SIZE_PATTERN.findall(source):
            sizes.append(f"{match.lower()}b")
    return _dedupe_sizes(sizes)

def _matches_architecture_family(repo_id: str, tags: list[str], family: str) -> bool:
    haystack = f"{repo_id} {' '.join(tags)}".lower()
    return family in haystack

def _is_hf_embedding(pipeline_tag: str | None, tags: list[str]) -> bool:
    if pipeline_tag and "embed" in pipeline_tag.lower():
        return True
    return any("embed" in tag.lower() for tag in tags)

def _build_hf_description(downloads: int, quantizations: list[str], pipeline_tag: str | None) -> str:
    if len(quantizations) > 8:
        quant_summary = ", ".join(quantizations[:8]) + f", ... ({len(quantizations)} total)"
    else:
        quant_summary = ", ".join(quantizations)

    parts = [
        "GGUF on Hugging Face.",
        f"Downloads: {downloads:,}.",
        f"Quantizations: {quant_summary}.",
    ]
    if pipeline_tag:
        parts.append(f"Task: {pipeline_tag}.")
    return " ".join(parts)

def _fetch_hf_models_for_family(family: str) -> list[dict]:
    response = requests.get(
        HF_API_MODELS_URL,
        params={
            "search": family,
            "filter": "gguf",
            "sort": "downloads",
            "direction": "-1",
            "limit": HF_MODELS_PER_FAMILY,
            "full": "true",
        },
        headers={"User-Agent": HF_USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, list) else []

def _parse_hf_model(raw: dict, family: str) -> ModelEntry | None:
    repo_id = str(raw.get("id") or raw.get("modelId") or "").strip()
    if not repo_id:
        return None

    tags = [str(tag) for tag in raw.get("tags", [])]
    if not _matches_architecture_family(repo_id, tags, family):
        return None
    if _is_hf_embedding(raw.get("pipeline_tag"), tags):
        return None

    gguf_filenames = _list_gguf_filenames(raw.get("siblings", []))
    if not gguf_filenames:
        return None

    quantizations = _parse_quantizations(gguf_filenames)
    if not quantizations:
        return None

    downloads = int(raw.get("downloads") or 0)
    return {
        "name": repo_id,
        "parameter_sizes": _parse_parameter_sizes(repo_id, tags),
        "families": [family],
        "description": _build_hf_description(downloads, quantizations, raw.get("pipeline_tag")),
    }

def fetch_huggingface_models() -> list[ModelEntry]:
    global _huggingface_fetch_available
    _huggingface_fetch_available = True

    seen: set[str] = set()
    models: list[ModelEntry] = []

    for family in HF_ARCHITECTURE_FAMILIES:
        try:
            raw_models = _fetch_hf_models_for_family(family)
        except requests.RequestException:
            continue

        for raw in raw_models:
            repo_id = raw.get("id") or raw.get("modelId")
            if not repo_id or repo_id in seen:
                continue
            entry = _parse_hf_model(raw, family)
            if entry is None:
                continue
            seen.add(repo_id)
            models.append(entry)

    if not models:
        _huggingface_fetch_available = False
    return models

def fetch_all() -> FetchResult:
    ollama = fetch_ollama_models()
    huggingface = fetch_huggingface_models()
    return {
        "ollama": ollama,
        "huggingface": huggingface,
        "ollama_available": ollama_fetch_available(),
        "huggingface_available": huggingface_fetch_available(),
    }

if __name__ == "__main__":
    result = fetch_all()
    print(f"Ollama: {len(result['ollama'])} (available={result['ollama_available']})")
    print(f"Hugging Face: {len(result['huggingface'])} (available={result['huggingface_available']})")
    if result["ollama"]:
        print(result["ollama"][0])
    if result["huggingface"]:
        print(result["huggingface"][0])