from __future__ import annotations

from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "language": "zh-CN",
    "default_question_type": "cloze",
    "max_notes": 30,
    "temperature": 0.7,
}


def get_config(mw: Any) -> dict[str, Any]:
    """Return add-on config merged with defaults."""
    config = dict(DEFAULT_CONFIG)
    if mw is not None and mw.addonManager is not None:
        saved = mw.addonManager.getConfig(__name__.split(".")[0]) or {}
        config.update(saved)
    return config


def get_config_summary(mw: Any) -> str:
    config = get_config(mw)
    api_key = "configured" if config.get("api_key") else "missing"
    return "\n".join(
        [
            f"base_url: {config.get('base_url')}",
            f"model: {config.get('model')}",
            f"language: {config.get('language')}",
            f"default_question_type: {config.get('default_question_type')}",
            f"max_notes: {config.get('max_notes')}",
            f"api_key: {api_key}",
        ]
    )
