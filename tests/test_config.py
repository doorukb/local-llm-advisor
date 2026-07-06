"""Tests for API-key resolution and config handling."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    GEMINI_API_KEY_ENV,
    GeminiApiKeyNotFoundError,
    has_api_key,
    load_api_key,
    reset_config,
    resolve_config_path,
    save_api_key,
)


def test_resolve_prefers_explicit_path(tmp_path):
    p = tmp_path / "cfg.json"
    assert resolve_config_path(p) == p


def test_resolve_env_override(tmp_path, monkeypatch):
    p = tmp_path / "custom.json"
    monkeypatch.setenv("LLM_ADVISOR_CONFIG_PATH", str(p))
    assert resolve_config_path() == p


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)
    p = tmp_path / "cfg.json"
    save_api_key("test-key-123", p)
    assert has_api_key(p)
    assert load_api_key(p) == "test-key-123"


def test_env_var_wins_over_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv(GEMINI_API_KEY_ENV, "env-key")
    assert load_api_key(tmp_path / "nope.json") == "env-key"


def test_missing_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)
    with pytest.raises(GeminiApiKeyNotFoundError):
        load_api_key(tmp_path / "nope.json")


def test_corrupt_config_is_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)
    p = tmp_path / "cfg.json"
    p.write_text("{not json", encoding="utf-8")
    assert not has_api_key(p)


def test_reset_config_removes_file(tmp_path, monkeypatch):
    monkeypatch.delenv(GEMINI_API_KEY_ENV, raising=False)
    p = tmp_path / "cfg.json"
    save_api_key("k", p)
    assert reset_config(p) is True
    assert not p.exists()
