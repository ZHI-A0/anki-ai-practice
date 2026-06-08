"""AI Practice add-on for Anki.

This module registers menu actions and wires together note selection,
LLM generation, and the practice dialog.
"""

from __future__ import annotations

from aqt import mw
from aqt.qt import QAction, qconnect
from aqt.utils import showInfo, showWarning

from .config import get_config_summary
from .note_selector import collect_selected_notes
from .practice_dialog import PracticeDialog


def _generate_from_selected_notes() -> None:
    if mw is None:
        return

    try:
        notes = collect_selected_notes(mw)
    except Exception as exc:
        showWarning(f"Failed to collect selected notes:\n{exc}")
        return

    if not notes:
        showInfo(
            "Open Anki's Browse window, select some notes/cards, and run "
            "Tools → AI Practice → Generate from Selected Notes."
        )
        return

    dialog = PracticeDialog(mw, notes)
    dialog.exec()


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


def _setup_menu() -> None:
    if mw is None:
        return

    menu = mw.form.menuTools.addMenu("AI Practice")

    selected_action = QAction("Generate from Selected Notes", mw)
    qconnect(selected_action.triggered, _generate_from_selected_notes)
    menu.addAction(selected_action)

    settings_action = QAction("Settings Help", mw)
    qconnect(settings_action.triggered, _show_settings_help)
    menu.addAction(settings_action)


_setup_menu()
