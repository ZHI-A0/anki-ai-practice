from __future__ import annotations

from typing import Any

from .config import get_config
from .models import SourceNote
from .source_compactor import clean_field_text


def _active_browser(mw: Any) -> Any | None:
    browser = getattr(mw, "browser", None)
    if browser is not None:
        return browser
    app = getattr(mw, "app", None)
    if app is None:
        return None
    widget = app.activeWindow()
    if widget and widget.__class__.__name__.lower().endswith("browser"):
        return widget
    return None


def _selected_note_ids(browser: Any) -> list[int]:
    # Modern Anki Browser exposes selectedNotes(). Older versions usually expose
    # selectedCards(), which we map back to note IDs.
    if hasattr(browser, "selectedNotes"):
        return [int(nid) for nid in browser.selectedNotes()]

    if hasattr(browser, "selectedCards"):
        note_ids: list[int] = []
        col = browser.mw.col
        for card_id in browser.selectedCards():
            card = col.get_card(card_id)
            nid = int(card.nid)
            if nid not in note_ids:
                note_ids.append(nid)
        return note_ids

    return []


def _front_text_for_note(note: Any) -> str:
    """Return the text Anki would show on the first card's front side when possible."""
    try:
        cards = note.cards()
        if cards:
            question = cards[0].question()
            cleaned = clean_field_text(question)
            if cleaned:
                return cleaned
    except Exception:
        pass

    for field_name in note.keys():
        value = clean_field_text(note[field_name])
        if value:
            return value
    return ""


def collect_notes_from_browser(browser: Any) -> list[SourceNote]:
    mw = browser.mw
    config = get_config(mw)
    max_notes = int(config.get("max_notes") or 30)
    note_ids = _selected_note_ids(browser)[:max_notes]
    col = mw.col

    notes: list[SourceNote] = []
    for note_id in note_ids:
        note = col.get_note(note_id)
        cards = note.cards()
        deck_name = ""
        if cards:
            deck = col.decks.get(cards[0].did)
            deck_name = deck.get("name", "") if deck else ""
        model = note.note_type() or {}
        model_name = model.get("name", "")
        fields = {field_name: note[field_name] for field_name in note.keys()}
        notes.append(
            SourceNote(
                note_id=int(note_id),
                model_name=model_name,
                deck_name=deck_name,
                fields=fields,
                tags=list(note.tags),
                front_text=_front_text_for_note(note),
            )
        )

    return notes


def collect_selected_notes(mw: Any) -> list[SourceNote]:
    browser = _active_browser(mw)
    if browser is None:
        return []
    return collect_notes_from_browser(browser)
