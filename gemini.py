from __future__ import annotations
import socket
import google.generativeai as genai
import requests
from google.api_core import exceptions as google_api_exceptions
from google.generativeai.types import generation_types
from config import load_api_key

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.2
GEMINI_REQUEST_TIMEOUT = 120

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