from __future__ import annotations

import json
from pathlib import Path

import google.generativeai as genai

GEMINI_MODEL = "gemini-1.5-flash"


def load_api_key(config_path: Path = Path("config.json")) -> str:
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Gemini API key not found at {config_path}. "
            "Run the advisor to save your key, or create config.json with an api_key field."
        )

    raw = config_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(
            f"{config_path} is empty. "
            "Run the advisor to save your key, or add {\"api_key\": \"YOUR_KEY\"}."
        )

    data = json.loads(raw)
    api_key = data.get("api_key")
    if not api_key or not str(api_key).strip():
        raise ValueError(
            f"No api_key in {config_path}. "
            "Run the advisor to save your key, or add {\"api_key\": \"YOUR_KEY\"}."
        )

    return str(api_key).strip()


def generate_report(system_prompt: str, user_prompt: str) -> str:
    genai.configure(api_key=load_api_key())
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=system_prompt)
    response = model.generate_content(user_prompt)

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
