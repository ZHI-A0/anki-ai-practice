from __future__ import annotations

import html
from typing import Any

NOTE_TYPE_NAME = "AI Practice Multiple Choice"
DEFAULT_DECK_NAME = "AI Practice::Generated"

FIELDS = [
    "Question",
    "OptionA",
    "OptionB",
    "OptionC",
    "OptionD",
    "Answer",
    "Explanation",
    "Source",
]

QFMT = """
<div class="ai-practice-card" data-answer="{{text:Answer}}">
  <div class="question">{{Question}}</div>
  <div class="options">
    <button type="button" class="option-button" data-value="{{text:OptionA}}" onclick="aiPracticeChoose(this)">
      <span class="label">A</span><span class="option-text">{{OptionA}}</span>
    </button>
    <button type="button" class="option-button" data-value="{{text:OptionB}}" onclick="aiPracticeChoose(this)">
      <span class="label">B</span><span class="option-text">{{OptionB}}</span>
    </button>
    <button type="button" class="option-button" data-value="{{text:OptionC}}" onclick="aiPracticeChoose(this)">
      <span class="label">C</span><span class="option-text">{{OptionC}}</span>
    </button>
    <button type="button" class="option-button" data-value="{{text:OptionD}}" onclick="aiPracticeChoose(this)">
      <span class="label">D</span><span class="option-text">{{OptionD}}</span>
    </button>
  </div>
  <div class="choice-result" aria-live="polite"></div>
</div>

<script>
function aiPracticeEscapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function aiPracticeNormalize(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function aiPracticeChoose(button) {
  const card = button.closest(".ai-practice-card");
  if (!card) return;

  const answer = aiPracticeNormalize(card.dataset.answer);
  const chosen = aiPracticeNormalize(button.dataset.value);
  const result = card.querySelector(".choice-result");
  const buttons = card.querySelectorAll(".option-button");

  buttons.forEach((btn) => {
    const value = aiPracticeNormalize(btn.dataset.value);
    btn.disabled = true;
    btn.classList.remove("selected", "correct", "wrong");
    if (value === answer) {
      btn.classList.add("correct");
    }
  });

  button.classList.add("selected");

  if (chosen === answer) {
    result.innerHTML = "✅ Correct";
    result.className = "choice-result result-correct";
  } else {
    button.classList.add("wrong");
    result.innerHTML = "❌ Incorrect. Correct answer: <b>" + aiPracticeEscapeHtml(answer) + "</b>";
    result.className = "choice-result result-wrong";
  }
}
</script>
""".strip()

AFMT = """
{{FrontSide}}
<hr id="answer">
<div class="answer"><b>Answer:</b> {{Answer}}</div>
<div class="explanation"><b>Explanation:</b> {{Explanation}}</div>
<div class="source"><b>Source:</b><br>{{Source}}</div>
""".strip()

CSS = """
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
.option-button {
  width: 100%;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.option-button:hover:not(:disabled) {
  border-color: #999;
  background: #f7f7f7;
}
.option-button:disabled {
  cursor: default;
}
.option-button.correct {
  border-color: #2e7d32;
  background: #e8f5e9;
}
.option-button.wrong {
  border-color: #c62828;
  background: #ffebee;
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
.choice-result {
  min-height: 28px;
  margin-top: 16px;
  font-size: 20px;
  font-weight: bold;
}
.result-correct {
  color: #2e7d32;
}
.result-wrong {
  color: #c62828;
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


def _ensure_fields(models: Any, model: Any) -> None:
    existing = {field["name"] for field in model.get("flds", [])}
    for field_name in FIELDS:
        if field_name not in existing:
            models.add_field(model, models.new_field(field_name))


def _ensure_template(models: Any, model: Any) -> None:
    templates = model.get("tmpls", [])
    if templates:
        template = templates[0]
        template["name"] = "Interactive Multiple Choice"
        template["qfmt"] = QFMT
        template["afmt"] = AFMT
    else:
        template = models.new_template("Interactive Multiple Choice")
        template["qfmt"] = QFMT
        template["afmt"] = AFMT
        models.add_template(model, template)


def _get_or_create_note_type(col: Any) -> Any:
    models = col.models
    model = models.by_name(NOTE_TYPE_NAME)
    if model is None:
        model = models.new(NOTE_TYPE_NAME)

    _ensure_fields(models, model)
    _ensure_template(models, model)
    model["css"] = CSS
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
    if answer and answer not in options:
        options.insert(0, answer)
    while len(options) < 4:
        options.append("")
    return options[:4]


def save_practice_as_cards(
    mw: Any,
    result: dict[str, Any],
    source_notes: list[Any],
    deck_name: str = DEFAULT_DECK_NAME,
) -> int:
    """Persist generated interactive multiple-choice practice questions as real Anki cards."""
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
