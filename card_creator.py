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

  <div class="feedback-panel" style="display:none;">
    <div class="choice-result" aria-live="polite"></div>
    <div class="inline-answer"><b>Answer:</b> <span class="inline-answer-value">{{Answer}}</span></div>
    <div class="inline-explanation"><b>Explanation:</b> {{Explanation}}</div>
  </div>
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
  const buttons = card.querySelectorAll(".option-button");
  const panel = card.querySelector(".feedback-panel");
  const result = card.querySelector(".choice-result");

  buttons.forEach((btn) => {
    const value = aiPracticeNormalize(btn.dataset.value);
    btn.disabled = true;
    btn.classList.remove("selected", "correct", "wrong");
    if (value === answer) {
      btn.classList.add("correct");
    }
  });

  button.classList.add("selected");
  if (panel) panel.style.display = "block";

  if (chosen === answer) {
    result.innerHTML = "✅ Correct";
    result.className = "choice-result result-correct";
  } else {
    button.classList.add("wrong");
    result.innerHTML = "❌ Incorrect";
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
  font-family: Arial, "Microsoft YaHei", sans-serif;
  font-size: 18px;
  text-align: left;
  line-height: 1.55;
  background: #fafafa;
  color: #222;
}
.ai-practice-card {
  max-width: 760px;
  margin: 0 auto;
  padding: 22px;
  border: 1px solid #e6e6e6;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
}
.question {
  font-size: 22px;
  font-weight: 650;
  margin-bottom: 22px;
}
.options {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.option-button {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1.5px solid #d9d9d9;
  border-radius: 14px;
  padding: 13px 15px;
  background: #fff;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 120ms ease, background 120ms ease, transform 80ms ease;
}
.option-button:hover:not(:disabled) {
  border-color: #6d8cff;
  background: #f5f7ff;
  transform: translateY(-1px);
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
  flex: 0 0 auto;
  display: inline-block;
  width: 30px;
  height: 30px;
  line-height: 30px;
  text-align: center;
  border-radius: 999px;
  border: 1px solid #a8a8a8;
  background: #f7f7f7;
  font-weight: bold;
}
.option-button.correct .label {
  border-color: #2e7d32;
  background: #2e7d32;
  color: #fff;
}
.option-button.wrong .label {
  border-color: #c62828;
  background: #c62828;
  color: #fff;
}
.option-text {
  flex: 1 1 auto;
}
.feedback-panel {
  margin-top: 18px;
  padding: 15px 16px;
  border-radius: 14px;
  background: #f6f6f6;
  border: 1px solid #e2e2e2;
}
.choice-result {
  margin-bottom: 10px;
  font-size: 21px;
  font-weight: bold;
}
.result-correct {
  color: #2e7d32;
}
.result-wrong {
  color: #c62828;
}
.inline-answer, .inline-explanation {
  margin-top: 8px;
}
.answer {
  margin-top: 16px;
  font-size: 20px;
}
.explanation, .source {
  margin-top: 12px;
  color: #555;
}
@media (min-width: 700px) {
  .options {
    grid-template-columns: 1fr 1fr;
  }
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
