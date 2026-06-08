from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class LLMError(RuntimeError):
    pass


def _clean_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def chat_completion(config: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        raise LLMError("API key is missing. Open Tools → Add-ons → AI Practice → Config and set api_key.")

    base_url = _clean_base_url(str(config.get("base_url") or "https://api.openai.com/v1"))
    model = str(config.get("model") or "gpt-4o-mini")
    temperature = float(config.get("temperature") or 0.7)

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"Failed to connect to LLM API: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM API returned invalid JSON: {exc}") from exc

    try:
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMError(f"Could not parse LLM response: {data}") from exc
