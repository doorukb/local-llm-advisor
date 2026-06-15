from __future__ import annotations
import html
import re
from typing import TypedDict
import requests

# ollama library url and parameters

OLLAMA_LIBRARY_URL = "https://ollama.com/library"
OLLAMA_LIBRARY_PARAMS = {"sort": "popular"}
REQUEST_TIMEOUT = 30

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
    html_text = _fetch_ollama_library_html()
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

if __name__ == "__main__":
    ollama_models = fetch_ollama_models()
    print(f"{len(ollama_models)} models")
    if ollama_models:
        print(ollama_models[0])