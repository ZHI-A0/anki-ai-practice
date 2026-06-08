"""AI Practice add-on for Anki.

This module registers menu actions and wires together note selection,
LLM generation, and the practice dialog.
"""

from __future__ import annotations

from typing import Any

from aqt import gui_hooks, mw
from aqt.qt import QAction, qconnect
from aqt.utils import showInfo, showWarning

from .config import get_config_summary
from .note_selector import collect_notes_from_browser, collect_selected_notes
from .practice_dialog import PracticeDialog


def _open_practice_dialog(parent: Any, notes: list[Any]) -> None:
    if not notes:
        showInfo("Select some notes/cards in Anki's Browse window first.")
        return

    dialog = PracticeDialog(parent, notes)
    dialog.exec()


def _generate_from_active_browser() -> None:
    """Fallback action from the main window, useful when Browse is focused."""
    if mw is None:
        return

    try:
        notes = collect_selected_notes(mw)
    except Exception as exc:
        showWarning(f"Failed to collect selected notes:\n{exc}")
        return

    _open_practice_dialog(mw, notes)


def _show_recent_reviewed_placeholder() -> None:
    showInfo(
        "This global workflow is planned next.\n\n"
        "It will generate AI practice from recently reviewed or completed cards, "
        "without requiring you to select notes in the Browse window."
    )


def _show_save_as_cards_placeholder() -> None:
    showInfo(
        "Saving generated practice as new Anki cards is planned next.\n\n"
        "The current MVP displays generated questions in a dialog first."
    )


def _show_settings_help() -> None:
    summary = get_config_summary(mw)
    showInfo(
        "AI Practice settings\n\n"
        f"{summary}\n\n"
        "Configure this add-on from Tools → Add-ons → AI Practice → Config.\n\n"
        "Use an OpenAI-compatible endpoint. For example:\n"
        "base_url: https://api.openai.com/v1\n"
        "model: gpt-4o-mini\n\n"
        "Your API key is stored in Anki's local add-on config."
    )


def _setup_main_menu() -> None:
    if mw is None:
        return

    menu = mw.form.menuTools.addMenu("AI Practice")

    selected_action = QAction("Generate from Active Browser Selection", mw)
    qconnect(selected_action.triggered, _generate_from_active_browser)
    menu.addAction(selected_action)

    recent_action = QAction("Generate from Recently Reviewed (coming soon)", mw)
    qconnect(recent_action.triggered, _show_recent_reviewed_placeholder)
    menu.addAction(recent_action)

    save_action = QAction("Save Generated Practice as Cards (coming soon)", mw)
    qconnect(save_action.triggered, _show_save_as_cards_placeholder)
    menu.addAction(save_action)

    menu.addSeparator()

    settings_action = QAction("Settings Help", mw)
    qconnect(settings_action.triggered, _show_settings_help)
    menu.addAction(settings_action)


def _browser_generate_from_selection(browser: Any) -> None:
    try:
        notes = collect_notes_from_browser(browser)
    except Exception as exc:
        showWarning(f"Failed to collect selected notes:\n{exc}")
        return

    _open_practice_dialog(browser, notes)


def _add_browser_context_menu_item(browser: Any, menu: Any) -> None:
    action = QAction("AI Practice: Generate from Selection", browser)
    qconnect(action.triggered, lambda: _browser_generate_from_selection(browser))
    menu.addSeparator()
    menu.addAction(action)


def _add_browser_menu_item(browser: Any) -> None:
    # Different Anki versions expose Browser menus with slightly different names.
    # We try common locations and silently fall back to the context menu hook.
    action = QAction("AI Practice: Generate from Selection", browser)
    qconnect(action.triggered, lambda: _browser_generate_from_selection(browser))

    form = getattr(browser, "form", None)
    for attr in ("menuEdit", "menuCards", "menuNotes"):
        menu = getattr(form, attr, None) if form is not None else None
        if menu is not None:
            menu.addSeparator()
            menu.addAction(action)
            return


_setup_main_menu()

gui_hooks.browser_will_show_context_menu.append(_add_browser_context_menu_item)
gui_hooks.browser_did_init.append(_add_browser_menu_item)
