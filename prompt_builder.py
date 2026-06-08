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
- For multiple_choice, every question must have 4 options.
- The answer must exactly match one option.
- Do not include option letters in the option strings.
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
            "Generate a set of multiple-choice temporary practice cards from the user's Anki notes. "
            "Use cloze/fill-in-the-blank style when appropriate. "
            "Each question should test one selected learning item. "
            "Each question must have exactly 4 plausible options, with one correct answer. "
            "Question stems and options should follow the source item's language; explanations may be concise."
        )

    system = (
        "You are an assistant that creates high-quality Anki practice cards. "
        "Use only the compact source notes provided by the user. "
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
