from __future__ import annotations

import random
from typing import Any

from .config import split_fields
from .knowledge_graph_distractor import SourceKnowledgeGraph
from .source_compactor import clean_field_text


def _first_field(note: Any, field_names: list[str]) -> str:
    for name in field_names:
        if name in note.fields:
            value = clean_field_text(note.fields[name])
            if value:
                return value
    return ""


def _fallback_front(note: Any) -> str:
    return clean_field_text(getattr(note, "front_text", "") or note.first_field_text())


def _first_sentence(text: str) -> str:
    cleaned = clean_field_text(text)
    if not cleaned:
        return ""
    # Keep this deliberately simple and language-agnostic.
    for sep in ("\n", ";", "。", "？", "！"):
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0]
    # For numbered example fields like "(1) ... (2) ...", keep the first example.
    if "(2)" in cleaned:
        cleaned = cleaned.split("(2)")[0]
    return cleaned.strip()


def _make_blank(sentence: str, answer: str) -> str:
    if not sentence:
        return f"_____: {answer}"
    if answer and answer.lower() in sentence.lower():
        idx = sentence.lower().find(answer.lower())
        return sentence[:idx] + "_____" + sentence[idx + len(answer):]
    return f"{sentence}\n\nChoose the best answer: _____"


def _meaning_explanation(answer: str, meaning: str, explanation_language: str) -> str:
    if meaning:
        if explanation_language.lower().startswith("zh"):
            return f"{answer}：{meaning}"
        return f"{answer}: {meaning}"
    if explanation_language.lower().startswith("zh"):
        return f"正确答案是 {answer}。"
    return f"The correct answer is {answer}."


def generate_local_practice(notes: list[Any], config: dict[str, Any]) -> dict[str, Any]:
    """Generate practice locally without calling any LLM API."""
    target_fields = split_fields(config.get("local_target_fields"))
    example_fields = split_fields(config.get("local_example_fields"))
    meaning_fields = split_fields(config.get("local_meaning_fields"))
    explanation_language = str(config.get("explanation_language") or "zh-CN")
    use_existing_examples = bool(config.get("use_existing_examples", True))

    graph = SourceKnowledgeGraph.from_notes(notes)
    questions: list[dict[str, Any]] = []

    for note in notes:
        answer = _first_field(note, target_fields) or _fallback_front(note)
        answer = clean_field_text(answer)
        if not answer:
            continue

        distractors = graph.distractors_for(answer, 3)
        if len(distractors) < 3:
            continue

        example = ""
        if use_existing_examples:
            example = _first_sentence(_first_field(note, example_fields))
        question = _make_blank(example, answer)

        meaning = _first_field(note, meaning_fields)
        explanation = _meaning_explanation(answer, meaning, explanation_language)

        options = [answer, *distractors[:3]]
        # Ensure unique options after normalization.
        unique_options: list[str] = []
        seen: set[str] = set()
        for option in options:
            norm = clean_field_text(option).lower()
            if norm and norm not in seen:
                unique_options.append(option)
                seen.add(norm)
        if len(unique_options) != 4:
            continue
        random.shuffle(unique_options)

        questions.append(
            {
                "question": question,
                "options": unique_options,
                "answer": answer,
                "explanation": explanation,
            }
        )

    return {
        "title": "Local Practice",
        "question_type": "multiple_choice",
        "questions": questions,
    }
