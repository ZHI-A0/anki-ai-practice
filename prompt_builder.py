from __future__ import annotations

from typing import Any

from .models import SourceNote
from .source_compactor import compact_notes_for_llm


SCHEMA_INSTRUCTIONS = """
Return valid JSON only. Do not wrap it in Markdown.
Schema:
{
  "title": "string",
  "question_type": "multiple_choice | qa",
  "questions": [
    {
      "question": "string",
      "options": ["string"],
      "answer": "string",
      "explanation": "string"
    }
  ]
}
Rules:
- For multiple_choice, every question must have exactly 4 options.
- The answer must exactly match one option.
- Do not include option letters in the option strings.
- The correct answer should come from the source learning items.
- Distractors may come from outside the source notes when needed.
- Distractors must be semantically, grammatically, and difficulty-level plausible.
- Avoid trivial distractors that share only the same prefix, spelling pattern, or first letter.
- Avoid making all 4 options start with the same letter/prefix unless the learning task specifically requires it.
- For vocabulary questions, prefer distractors with the same part of speech but different roots/prefixes and similar frequency.
""".strip()


def _language_instruction(language: str) -> str:
    normalized = (language or "auto").strip().lower()
    if normalized in {"auto", "source", "same", "same_as_source"}:
        return (
            "Write the question stem and options in the same language as the source learning items. "
            "Use the user's preferred explanation language only for explanations if needed. "
            "For example, if the source items are English words, generate English question stems and English options."
        )
    return f"Respond in {language}."


def build_prompt(
    notes: list[SourceNote],
    question_type: str,
    language: str,
    config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    config = config or {}
    source_text = compact_notes_for_llm(notes, config)

    if question_type == "qa":
        task = (
            "Generate 3 to 5 short-answer practice questions from the user's Anki notes. "
            "Focus on recall, transfer, and understanding. Avoid asking for irrelevant metadata."
        )
    else:
        task = (
            "Generate a set of professional multiple-choice Anki practice cards from the user's source items. "
            "Use cloze/fill-in-the-blank style when appropriate. "
            "Each question should test one selected learning item. "
            "Each question must have exactly 4 options: 1 correct answer and 3 strong distractors. "
            "Do not simply use neighboring selected items as distractors if they are visually similar or all share the same prefix. "
            "For English vocabulary, make distractors plausible in the sentence, same part of speech where possible, but not all starting with the same letter. "
            "Question stems and options should follow the source item's language; explanations may be concise."
        )

    system = (
        "You are an expert assessment designer creating high-quality Anki practice cards. "
        "Use the compact source notes to decide which learning items should be tested. "
        "You may use general language knowledge to create plausible distractors. "
        "Ignore note IDs, metadata, HTML artifacts, audio markers, and unrelated dictionary noise if present. "
        "Make the practice useful for memory consolidation, not trivia. "
        f"{_language_instruction(language)} "
        + SCHEMA_INSTRUCTIONS
    )

    user = f"Task: {task}\n\nCompact source Anki notes:\n{source_text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
