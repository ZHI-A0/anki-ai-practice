from __future__ import annotations

from typing import Any

from aqt import mw as main_window

ADDON_PACKAGE = __name__.split(".")[0]

DEFAULT_CONFIG: dict[str, Any] = {
    # local_first: use existing note fields/examples + source graph first.
    # llm_first: let the LLM generate question stems/explanations, while the
    # plugin can still constrain options to the source graph.
    "generation_mode": "local_first",
    "question_type": "multiple_choice",
    "question_language": "source",
    "explanation_language": "zh-CN",
    "max_notes": 30,
    "recent_reviewed_limit": 30,
    "recent_reviewed_scan_cards": 300,
    "save_deck_name": "AI Practice::Generated",

    # Knowledge graph settings.
    "graph_max_notes": 5000,
    "graph_top_k": 5,
    "graph_term_fields": "英语单词,Front,正面,Expression,Term,单词,词条",
    "graph_meaning_fields": "中文释义,Meaning,Back,背面,释义,答案",
    "graph_example_fields": "英语例句,Example,Examples,Sentence,例句",

    # Local-first settings.
    "local_example_source": "example_field",
    "local_example_fields": "英语例句,Example,Examples,Sentence,例句",
    "local_target_fields": "英语单词,Front,正面,Expression,Term,单词,词条",
    "local_meaning_fields": "中文释义,Meaning,Back,背面,释义,答案",
    "local_translation_example_fields": "中文例句,Translation Example,Example Translation,译文,中文翻译",
    "local_graph_fields": "英语单词,Front,正面,Expression,Term,单词,词条",
    "local_option_source": "saved_graph",
    "local_option_graph_type": "meaning",
    "local_explanation_source": "meaning_and_translation_example",
    "use_existing_examples": True,

    # LLM settings.
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "llm_source_fields": "Front,正面,Question,问题,英语单词,中文释义,英语例句,中文例句,Back,背面",
    "llm_graph_fields": "英语单词,Front,正面,Expression,Term,单词,词条",

    # Shared source compression settings.
    "source_mode": "front",
    "preferred_fields": [
        "英语单词",
        "中文释义",
        "英语例句",
        "中文例句",
        "Front",
        "Back",
        "正面",
        "背面",
        "Expression",
        "Meaning",
        "Sentence",
    ],
    "ignored_field_keywords": [
        "发音",
        "音频",
        "sound",
        "柯林斯",
        "collins",
        "vocabulary扩展",
        "扩展",
        "图片",
        "image",
        "html",
        "css",
        "style",
    ],
    "max_field_chars": 280,
    "max_total_chars": 12000,
}


def split_fields(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


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
        saved = addon_manager.getConfig(ADDON_PACKAGE) or {}
        config.update(saved)
    return config


def save_config(window: Any, config: dict[str, Any]) -> None:
    mw = _main_window(window)
    addon_manager = getattr(mw, "addonManager", None)
    if addon_manager is not None:
        addon_manager.writeConfig(ADDON_PACKAGE, config)


def get_config_summary(window: Any = None) -> str:
    config = get_config(window)
    api_key = "configured" if config.get("api_key") else "missing"
    return "\n".join(
        [
            f"generation_mode: {config.get('generation_mode')}",
            f"question_type: {config.get('question_type')}",
            f"question_language: {config.get('question_language')}",
            f"explanation_language: {config.get('explanation_language')}",
            f"recent_reviewed_limit: {config.get('recent_reviewed_limit')}",
            f"graph_max_notes: {config.get('graph_max_notes')}",
            f"graph_top_k: {config.get('graph_top_k')}",
            f"local_option_source: {config.get('local_option_source')}",
            f"local_option_graph_type: {config.get('local_option_graph_type')}",
            f"local_example_source: {config.get('local_example_source')}",
            f"base_url: {config.get('base_url')}",
            f"model: {config.get('model')}",
            f"max_notes: {config.get('max_notes')}",
            f"api_key: {api_key}",
        ]
    )
