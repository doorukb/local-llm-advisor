"""Tests for prompt assembly and the Ollama library HTML parser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fetch import _parse_ollama_library  # noqa: E402
from src.prompt import (  # noqa: E402
    HUGGINGFACE_UNAVAILABLE_NOTE,
    OLLAMA_UNAVAILABLE_NOTE,
    build_prompt,
)


def _hardware():
    return {
        "cpu": {"model": "Ryzen 7 5800X", "cores": 8, "threads": 16},
        "ram": {"total_gb": 32.0, "available_gb": 24.5},
        "gpu": [{"model": "GeForce RTX 3080", "vram_gb": 10.0, "vendor": "nvidia"}],
        "os": {"name": "Windows", "version": "11", "arch": "AMD64"},
    }


def _selections(engine="Ollama"):
    return {
        "inference_engine": engine,
        "primary_use_case": "Coding assistant",
        "context_length": "Medium (8K-16K)",
        "performance_priority": "Balanced",
    }


def _fetch_result(ok=True):
    if ok:
        return {
            "ollama": [
                {
                    "name": "llama3.1",
                    "parameter_sizes": ["8b", "70b"],
                    "families": ["llama"],
                    "description": "Meta's flagship open model",
                }
            ],
            "huggingface": [],
            "ollama_available": True,
            "huggingface_available": False,
        }
    return {
        "ollama": [],
        "huggingface": [],
        "ollama_available": False,
        "huggingface_available": False,
    }


def test_prompt_includes_hardware_and_selections():
    system, user = build_prompt(_hardware(), _selections(), _fetch_result())
    combined = system + user
    assert "RTX 3080" in combined
    assert "Coding assistant" in combined
    assert "llama3.1" in combined


def test_prompt_notes_fetch_failures_instead_of_empty_lists():
    _, user = build_prompt(_hardware(), _selections(), _fetch_result(ok=False))
    assert OLLAMA_UNAVAILABLE_NOTE in user or HUGGINGFACE_UNAVAILABLE_NOTE in user


def test_parse_ollama_library_extracts_cards():
    html = '''
    <li x-test-model><h2><span x-test-model-title title="gemma3">gemma3</span></h2>
    <p class="max-w-lg break-words text-neutral-800 text-md">Google's lightweight model family</p>
    <span x-test-size>4b</span><span x-test-size>27b</span>
    <span x-test-capability>vision</span></li>
    '''
    cards = _parse_ollama_library(html)
    assert len(cards) == 1
    assert cards[0]["name"] == "gemma3"
    assert "4b" in cards[0]["parameter_sizes"]


def test_parse_ollama_library_handles_garbage():
    assert _parse_ollama_library("<html><body>nothing here</body></html>") == []
