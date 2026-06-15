from __future__ import annotations
import json
import os
import socket
from pathlib import Path
import google.generativeai as genai
import requests
from google.api_core import exceptions as google_api_exceptions
from google.generativeai.types import generation_types

GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_TEMPERATURE = 0.2
GEMINI_REQUEST_TIMEOUT = 120
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
DEFAULT_CONFIG_PATH = Path("config.json")

ERROR_INVALID_API_KEY = (
    "Gemini API error: Invalid API key. "
    "Check GEMINI_API_KEY or the api_key field in config.json."
)
ERROR_QUOTA_EXCEEDED = (
    "Gemini API error: Quota exceeded or rate limit hit. "
    "Wait and retry, or check your Google AI Studio usage limits."
)
ERROR_NETWORK_TIMEOUT = (
    "Gemini API error: Network timeout while contacting Gemini. "
    "Check your internet connection and try again."
)
ERROR_UNEXPECTED_RESPONSE = (
    "Gemini API error: Unexpected response from Gemini. "
    "Try again; if it persists, retry with different selections."
)


# raised when no Gemini API key is available from env or config.json
class GeminiApiKeyNotFoundError(Exception):
    pass

# load the Gemini API key from env or config.json
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

def _exception_message(exc: BaseException) -> str:
    return str(exc).lower()

def _format_api_error(exc: BaseException) -> str:
    message = _exception_message(exc)

    if isinstance(exc, google_api_exceptions.Unauthenticated):
        return ERROR_INVALID_API_KEY

    if isinstance(exc, google_api_exceptions.PermissionDenied):
        if any(token in message for token in ("api key", "api_key", "auth", "credential")):
            return ERROR_INVALID_API_KEY

    if isinstance(exc, google_api_exceptions.InvalidArgument):
        if "api key" in message or "api_key" in message:
            return ERROR_INVALID_API_KEY

    if isinstance(exc, google_api_exceptions.ResourceExhausted):
        return ERROR_QUOTA_EXCEEDED

    if "429" in message or "quota" in message or "rate limit" in message:
        return ERROR_QUOTA_EXCEEDED

    if isinstance(exc,(
            google_api_exceptions.DeadlineExceeded,
            requests.exceptions.Timeout,
            TimeoutError,
            socket.timeout,
        )):
        return ERROR_NETWORK_TIMEOUT

    try:
        import urllib3

        if isinstance(exc, urllib3.exceptions.TimeoutError):
            return ERROR_NETWORK_TIMEOUT
    except ImportError:
        pass

    if isinstance(exc,(
        generation_types.BlockedPromptException,
        generation_types.BrokenResponseError,
        generation_types.StopCandidateException,
    )):
        return ERROR_UNEXPECTED_RESPONSE

    if isinstance(exc, google_api_exceptions.GoogleAPICallError):
        if any(token in message for token in ("timeout", "timed out", "connection", "network")):
            return ERROR_NETWORK_TIMEOUT
        return ERROR_UNEXPECTED_RESPONSE

    if any(token in message for token in ("timeout", "timed out", "connection refused", "network")):
        return ERROR_NETWORK_TIMEOUT

    return ERROR_UNEXPECTED_RESPONSE

def generate_report(system_prompt: str, user_prompt: str) -> str:
    genai.configure(api_key=load_api_key())
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(temperature=GEMINI_TEMPERATURE),
    )

    try:
        response = model.generate_content(
            user_prompt,
            request_options={"timeout": GEMINI_REQUEST_TIMEOUT},
        )
    except Exception as exc:
        return _format_api_error(exc)

    try:
        text = response.text
    except (ValueError, AttributeError):
        return ERROR_UNEXPECTED_RESPONSE

    if not text or not text.strip():
        return ERROR_UNEXPECTED_RESPONSE

    return text

if __name__ == "__main__":
    try:
        print("API key loaded:", bool(load_api_key()))
    except GeminiApiKeyNotFoundError as exc:
        print(exc)