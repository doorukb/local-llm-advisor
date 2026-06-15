from __future__ import annotations
import json
import os
from pathlib import Path
import google.generativeai as genai

GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
DEFAULT_CONFIG_PATH = Path("config.json")


# raised when no Gemini API key is available from env or config.json
class GeminiApiKeyNotFoundError(Exception):
    # Raised when no Gemini API key is available from env or config.json.
    pass

def load_api_key(config_path: Path = DEFAULT_CONFIG_PATH) -> str:
    env_key = os.environ.get(GEMINI_API_KEY_ENV)
    if env_key and env_key.strip():
        return env_key.strip()

    if config_path.is_file():
        raw = config_path.read_text(encoding="utf-8").strip()
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = None

            if isinstance(data, dict):
                api_key = data.get("api_key")
                if api_key and str(api_key).strip():
                    return str(api_key).strip()

    raise GeminiApiKeyNotFoundError("No Gemini API key found. Set GEMINI_API_KEY or add api_key to config.json.")

# generate a report using the Gemini API
def generate_report(system_prompt: str, user_prompt: str) -> str:
    genai.configure(api_key=load_api_key())
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=system_prompt)
    response = model.generate_content(user_prompt)

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text

if __name__ == "__main__":
    try:
        print("API key loaded:", bool(load_api_key()))
    except GeminiApiKeyNotFoundError as exc:
        print(exc)