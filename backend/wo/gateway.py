"""PartPilot Runtime AI Gateway Adapter for 9router and Gemini models.
Provides safe, bounded, non-streaming completion calls with strict secret redaction.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
import httpx

GATEWAY_BASE_URL = os.environ.get("HERMES_9ROUTER_BASE_URL", "http://127.0.0.1:20128/v1")
DEFAULT_MODEL = "ag/gemini-3.8-flash-high"
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_OUTPUT_TOKENS = 4096

def runtime_timeout() -> float:
    """Keep each model call below the 90-second job lease, including demo override."""
    value=float(os.environ.get('PARTPILOT_GATEWAY_TIMEOUT_SECONDS','20'))
    if not 5 <= value <= 60:
        raise ValueError('Gateway timeout must be between 5 and 60 seconds')
    return value


def redact_secrets(text: str) -> str:
    """Strictly redact bearer tokens, API keys, and Authorization headers."""
    if not text:
        return ""
    # Redact Authorization header values
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}", r"\1[REDACTED]", text, flags=re.IGNORECASE)
    # Redact sk-... keys
    text = re.sub(r"(sk-[A-Za-z0-9_\-\.]{6,})", r"[REDACTED_API_KEY]", text)
    return text


def get_api_key() -> str:
    """Retrieve API key safely from environment."""
    return os.environ.get("HERMES_9ROUTER_API_KEY", "").strip()


def call_gateway_completion(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_tokens: int = MAX_OUTPUT_TOKENS,
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """Execute bounded chat completion against 9router with secret redaction.
    Returns:
      {
        'status': 'ok' | 'error',
        'model': str,
        'content': str,
        'parsed_json': Optional[Dict[str, Any]],
        'raw_response': Optional[Dict[str, Any]],
        'error': Optional[str],
        'retriable': bool
      }
    """
    api_key = get_api_key()
    if not api_key:
        return {
            "status": "error",
            "model": model,
            "content": "",
            "parsed_json": None,
            "error": "HERMES_9ROUTER_API_KEY not configured",
            "retriable": True,
        }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": min(max_tokens, MAX_OUTPUT_TOKENS),
        "temperature": temperature,
        "stream": False,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{GATEWAY_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )

        if resp.status_code != 200:
            safe_err = redact_secrets(resp.text[:300])
            return {
                "status": "error",
                "model": model,
                "content": "",
                "parsed_json": None,
                "error": f"Gateway HTTP {resp.status_code}: {safe_err}",
                "retriable": resp.status_code in (429, 500, 502, 503, 504),
            }

        data = resp.json()
        choices = data.get("choices", [])
        if not choices or "message" not in choices[0]:
            return {
                "status": "error",
                "model": model,
                "content": "",
                "parsed_json": None,
                "error": "No completion choices returned by gateway",
                "retriable": False,
            }

        raw_content = choices[0]["message"].get("content", "")
        reported_model = data.get("model", model)

        # Attempt to parse as JSON if structured
        parsed_json = None
        clean_content = raw_content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.split("```json", 1)[1].split("```", 1)[0].strip()
        elif clean_content.startswith("```"):
            clean_content = clean_content.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            parsed_json = json.loads(clean_content)
        except Exception:
            parsed_json = None

        return {
            "status": "ok",
            "model": reported_model,
            "content": raw_content,
            "parsed_json": parsed_json,
            "error": None,
            "retriable": False,
        }

    except httpx.TimeoutException as te:
        return {
            "status": "error",
            "model": model,
            "content": "",
            "parsed_json": None,
            "error": f"Gateway timeout after {timeout}s: {type(te).__name__}",
            "retriable": True,
        }
    except Exception as e:
        safe_msg = redact_secrets(str(e))
        return {
            "status": "error",
            "model": model,
            "content": "",
            "parsed_json": None,
            "error": f"Gateway call failed: {type(e).__name__}: {safe_msg}",
            "retriable": True,
        }


# Alias for compatibility
call_gateway = call_gateway_completion
