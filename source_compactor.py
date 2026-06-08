from __future__ import annotations

import html
import re
from typing import Any

from .models import SourceNote

_SOUND_RE = re.compile(r"\[sound:[^\]]+\]", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

DEFAULT_PREFERRED_FIELDS = [
    "英语单词",
    "中文释义",
    "英语例句",
    "中文例句",
    "Front",
    "Back",
    "正面",
    "背面",
    "Expression",
    "Meaning",
    "Sentence",
]

DEFAULT_IGNORED_FIELD_KEYWORDS = [
    "发音",
    "音频",
    "sound",
    "柯林斯",
    "collins",
    "vocabulary扩展",
    "扩展",
    "图片",
    "image",
    "html",
]


def clean_field_text(value: str) -> str:
    """Convert a note field into short plain text for LLM input."""
    text = html.unescape(value or "")
    text = _SOUND_RE.sub("", text)
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    text = _TAG_RE.sub("", text)
    text = _SPACE_RE.sub(" ", text)
    return text.strip()


def _field_allowed(name: str, value: str, preferred_fields: list[str], ignored_keywords: list[str]) -> bool:
    if not value.strip():
        return False

    lower_name = name.lower()
    if any(keyword.lower() in lower_name for keyword in ignored_keywords):
        return False

    # If a preferred list is configured, use matching fields first. Empty list means all non-ignored fields.
    if preferred_fields:
        return name in preferred_fields

    return True


def compact_notes_for_llm(notes: list[SourceNote], config: dict[str, Any]) -> str:
    source_mode = str(config.get("source_mode") or "front").lower()
    max_field_chars = int(config.get("max_field_chars") or 280)
    max_total_chars = int(config.get("max_total_chars") or 12000)

    if source_mode == "front":
        chunks: list[str] = []
        used_chars = 0
        for index, note in enumerate(notes, start=1):
            text = clean_field_text(note.front_text or note.first_field_text())
            if not text:
                continue
            if len(text) > max_field_chars:
                text = text[:max_field_chars].rstrip() + "..."
            chunk = f"Item {index}: {text}"
            if used_chars + len(chunk) > max_total_chars:
                break
            chunks.append(chunk)
            used_chars += len(chunk)
        return "\n".join(chunks)

    preferred_fields = list(config.get("preferred_fields") or DEFAULT_PREFERRED_FIELDS)
    ignored_keywords = list(config.get("ignored_field_keywords") or DEFAULT_IGNORED_FIELD_KEYWORDS)

    note_chunks: list[str] = []
    used_chars = 0

    for note in notes:
        lines: list[str] = []
        for field_name, raw_value in note.fields.items():
            cleaned = clean_field_text(raw_value)
            if not _field_allowed(field_name, cleaned, preferred_fields, ignored_keywords):
                continue
            if len(cleaned) > max_field_chars:
                cleaned = cleaned[:max_field_chars].rstrip() + "..."
            lines.append(f"{field_name}: {cleaned}")

        # Fallback: if preferred fields missed this note type, include a few short non-ignored fields.
        if not lines and preferred_fields:
            for field_name, raw_value in note.fields.items():
                cleaned = clean_field_text(raw_value)
                if not _field_allowed(field_name, cleaned, [], ignored_keywords):
                    continue
                if len(cleaned) > max_field_chars:
                    cleaned = cleaned[:max_field_chars].rstrip() + "..."
                lines.append(f"{field_name}: {cleaned}")
                if len(lines) >= 4:
                    break

        if not lines:
            continue

        chunk = "\n".join(lines)
        if used_chars + len(chunk) > max_total_chars:
            remaining = max_total_chars - used_chars
            if remaining > 200:
                note_chunks.append(chunk[:remaining].rstrip() + "...")
            break

        note_chunks.append(chunk)
        used_chars += len(chunk)

    return "\n\n---\n\n".join(note_chunks)
