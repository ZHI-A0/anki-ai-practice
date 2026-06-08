from __future__ import annotations

from .models import SourceNote


SCHEMA_INSTRUCTIONS = """
Return valid JSON only. Do not wrap it in Markdown.
Schema:
{
  "title": "string",
  "question_type": "cloze | qa",
  "questions": [
    {
      "question": "string",
      "options": ["string"],
      "answer": "string",
      "explanation": "string"
    }
  ]
}
""".strip()


def build_prompt(notes: list[SourceNote], question_type: str, language: str) -> list[dict[str, str]]:
    source_text = "\n\n---\n\n".join(note.compact_text() for note in notes)

    if question_type == "qa":
        task = (
            "Generate 3 to 5 short-answer practice questions from the user's Anki notes. "
            "Focus on recall, transfer, and understanding. Avoid asking for irrelevant metadata."
        )
    else:
        task = (
            "Generate one cloze passage or cloze-style practice set from the user's Anki notes. "
            "If the notes are vocabulary cards, create a natural passage and blank out key words. "
            "Include plausible options when useful. If the notes are not vocabulary, create fill-in-the-blank questions."
        )

    system = (
        "You are an assistant that creates high-quality learning practice for Anki users. "
        "Use only the information in the provided notes. "
        "Make the practice useful for memory consolidation, not trivia. "
        f"Respond in {language}. "
        + SCHEMA_INSTRUCTIONS
    )

    user = f"Task: {task}\n\nSource Anki notes:\n{source_text}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
