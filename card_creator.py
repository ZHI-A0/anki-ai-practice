from __future__ import annotations

import html
from typing import Any

NOTE_TYPE_NAME = "AI Practice Basic"
DEFAULT_DECK_NAME = "AI Practice::Generated"


def _get_or_create_note_type(col: Any) -> Any:
    models = col.models
    model = models.by_name(NOTE_TYPE_NAME)
    if model is not None:
        return model

    model = models.new(NOTE_TYPE_NAME)
    models.add_field(model, models.new_field("Question"))
    models.add_field(model, models.new_field("Options"))
    models.add_field(model, models.new_field("Answer"))
    models.add_field(model, models.new_field("Explanation"))
    models.add_field(model, models.new_field("Source"))

    template = models.new_template("Card 1")
    template["qfmt"] = """
<div class="ai-practice-card">
  <div class="question">{{Question}}</div>
  <hr>
  <div class="options">{{Options}}</div>
</div>
""".strip()
    template["afmt"] = """
{{FrontSide}}
<hr id="answer">
<div class="answer"><b>Answer:</b> {{Answer}}</div>
<div class="explanation"><b>Explanation:</b> {{Explanation}}</div>
<div class="source"><b>Source:</b> {{Source}}</div>
""".strip()
    models.add_template(model, template)

    model["css"] = """
.card {
  font-family: Arial, sans-serif;
  font-size: 18px;
  text-align: left;
  line-height: 1.5;
}
.question {
  font-size: 20px;
  margin-bottom: 12px;
}
.options ol {
  margin-top: 8px;
}
.answer {
  margin-top: 12px;
  font-size: 20px;
}
.explanation, .source {
  margin-top: 10px;
  color: #555;
}
""".strip()

    models.save(model)
    return model


def _options_html(options: list[Any]) -> str:
    if not options:
        return ""
    items = "".join(f"<li>{html.escape(str(option))}</li>" for option in options)
    return f"<ol type='A'>{items}</ol>"


def _source_summary(source_notes: list[Any]) -> str:
    names: list[str] = []
    for note in source_notes[:10]:
        text = getattr(note, "front_text", "") or note.first_field_text()
        text = html.escape(str(text)[:80])
        if text:
            names.append(text)
    return "<br>".join(names)


def save_practice_as_cards(
    mw: Any,
    result: dict[str, Any],
    source_notes: list[Any],
    deck_name: str = DEFAULT_DECK_NAME,
) -> int:
    """Persist generated practice questions as real Anki notes/cards."""
    col = mw.col
    deck_id = col.decks.id(deck_name)
    model = _get_or_create_note_type(col)
    questions = result.get("questions") or []
    source = _source_summary(source_notes)

    added = 0
    for item in questions:
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        if not question or not answer:
            continue

        note = col.new_note(model)
        note["Question"] = html.escape(question).replace("\n", "<br>")
        note["Options"] = _options_html(item.get("options") or [])
        note["Answer"] = html.escape(answer).replace("\n", "<br>")
        note["Explanation"] = html.escape(explanation).replace("\n", "<br>")
        note["Source"] = source
        note.tags.append("ai-practice")
        col.add_note(note, deck_id)
        added += 1

    if added:
        col.save()
        mw.reset()
    return added
