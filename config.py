from __future__ import annotations

from typing import Any

from aqt import mw as main_window

DEFAULT_CONFIG: dict[str, Any] = {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "language": "zh-CN",
    "default_question_type": "cloze",
    "max_notes": 30,
    "temperature": 0.7,
}


def _main_window(window: Any) -> Any:
    """Return Anki's main window from mw, Browser, Dialog, or fallback global mw."""
    if hasattr(window, "addonManager"):
        return window
    candidate = getattr(window, "mw", None)
    if candidate is not None and hasattr(candidate, "addonManager"):
        return candidate
    return main_window


def get_config(window: Any = None) -> dict[str, Any]:
    """Return add-on config merged with defaults."""
    config = dict(DEFAULT_CONFIG)
    mw = _main_window(window)
    addon_manager = getattr(mw, "addonManager", None)
    if addon_manager is not None:
        saved = addon_manager.getConfig(__name__.split(".")[0]) or {}
        config.update(saved)
    return config


def get_config_summary(window: Any = None) -> str:
    config = get_config(window)
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
