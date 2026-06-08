from __future__ import annotations

import html
from typing import Any

NOTE_TYPE_NAME = "AI Practice Multiple Choice"
DEFAULT_DECK_NAME = "AI Practice::Generated"


def _get_or_create_note_type(col: Any) -> Any:
    models = col.models
    model = models.by_name(NOTE_TYPE_NAME)
    if model is not None:
        return model

    model = models.new(NOTE_TYPE_NAME)
    models.add_field(model, models.new_field("Question"))
    models.add_field(model, models.new_field("OptionA"))
    models.add_field(model, models.new_field("OptionB"))
    models.add_field(model, models.new_field("OptionC"))
    models.add_field(model, models.new_field("OptionD"))
    models.add_field(model, models.new_field("Answer"))
    models.add_field(model, models.new_field("Explanation"))
    models.add_field(model, models.new_field("Source"))

    template = models.new_template("Multiple Choice")
    template["qfmt"] = """
<div class="ai-practice-card">
  <div class="question">{{Question}}</div>
  <div class="options">
    <div class="option"><span class="label">A</span>{{OptionA}}</div>
    <div class="option"><span class="label">B</span>{{OptionB}}</div>
    <div class="option"><span class="label">C</span>{{OptionC}}</div>
    <div class="option"><span class="label">D</span>{{OptionD}}</div>
  </div>
</div>
""".strip()
    template["afmt"] = """
{{FrontSide}}
<hr id="answer">
<div class="answer"><b>Answer:</b> {{Answer}}</div>
<div class="explanation"><b>Explanation:</b> {{Explanation}}</div>
<div class="source"><b>Source:</b><br>{{Source}}</div>
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
  font-size: 21px;
  margin-bottom: 18px;
}
.options {
  display: grid;
  gap: 10px;
}
.option {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px 12px;
}
.label {
  display: inline-block;
  width: 26px;
  height: 26px;
  line-height: 26px;
  text-align: center;
  border-radius: 50%;
  border: 1px solid #999;
  margin-right: 10px;
  font-weight: bold;
}
.answer {
  margin-top: 16px;
  font-size: 20px;
}
.explanation, .source {
  margin-top: 12px;
  color: #555;
}
""".strip()

    models.save(model)
    return model


def _source_summary(source_notes: list[Any]) -> str:
    names: list[str] = []
    for note in source_notes[:10]:
        text = getattr(note, "front_text", "") or note.first_field_text()
        text = html.escape(str(text)[:80])
        if text:
            names.append(text)
    return "<br>".join(names)


def _normalized_options(raw_options: list[Any], answer: str) -> list[str]:
    options = [str(option).strip() for option in raw_options if str(option).strip()]
    # Ensure the answer is present.
    if answer and answer not in options:
        options.insert(0, answer)
    # Pad defensively; prompt asks for exactly 4 but model may fail.
    while len(options) < 4:
        options.append("")
    return options[:4]


def save_practice_as_cards(
    mw: Any,
    result: dict[str, Any],
    source_notes: list[Any],
    deck_name: str = DEFAULT_DECK_NAME,
) -> int:
    """Persist generated multiple-choice practice questions as real Anki cards."""
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

        options = _normalized_options(item.get("options") or [], answer)

        note = col.new_note(model)
        note["Question"] = html.escape(question).replace("\n", "<br>")
        note["OptionA"] = html.escape(options[0]).replace("\n", "<br>")
        note["OptionB"] = html.escape(options[1]).replace("\n", "<br>")
        note["OptionC"] = html.escape(options[2]).replace("\n", "<br>")
        note["OptionD"] = html.escape(options[3]).replace("\n", "<br>")
        note["Answer"] = html.escape(answer).replace("\n", "<br>")
        note["Explanation"] = html.escape(explanation).replace("\n", "<br>")
        note["Source"] = source
        note.tags.append("ai-practice")
        note.tags.append("ai-practice-multiple-choice")
        col.add_note(note, deck_id)
        added += 1

    if added:
        col.save()
        mw.reset()
    return added
