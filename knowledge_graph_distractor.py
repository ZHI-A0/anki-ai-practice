from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Any

from .source_compactor import clean_field_text

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']*|[\u4e00-\u9fff]+")

COMMON_FRONT_FIELDS = [
    "Front",
    "正面",
    "Question",
    "问题",
    "Prompt",
    "提示",
    "英语单词",
    "单词",
    "词条",
    "Expression",
    "Term",
]


def _normalize(text: str) -> str:
    return clean_field_text(text).strip().lower()


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _WORD_RE.findall(clean_field_text(text)) if len(token.strip()) > 1}


def _rough_stem(word: str) -> str:
    w = word.lower().strip()
    for suffix in (
        "ingly",
        "edly",
        "ing",
        "ed",
        "ly",
        "ies",
        "es",
        "s",
        "er",
        "est",
        "tion",
        "ion",
        "able",
        "ible",
        "al",
        "ive",
        "ous",
        "ful",
        "less",
        "ment",
    ):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            return w[: -len(suffix)]
    return w


def _looks_like_inflection(a: str, b: str) -> bool:
    a_norm = _normalize(a)
    b_norm = _normalize(b)
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    a_stem = _rough_stem(a_norm)
    b_stem = _rough_stem(b_norm)
    if len(a_stem) >= 4 and len(b_stem) >= 4 and a_stem == b_stem:
        return True
    shorter, longer = sorted((a_norm, b_norm), key=len)
    return len(shorter) >= 4 and longer.startswith(shorter) and len(longer) - len(shorter) <= 5


@dataclass(slots=True)
class ConceptNode:
    term: str
    note_id: int
    text: str
    tokens: set[str]


class SourceKnowledgeGraph:
    """A lightweight graph built only from selected/source notes."""

    def __init__(self, nodes: list[ConceptNode]) -> None:
        self.nodes = nodes
        self.by_norm = {_normalize(node.term): node for node in nodes}

    @classmethod
    def from_notes(cls, notes: list[Any]) -> "SourceKnowledgeGraph":
        nodes: list[ConceptNode] = []
        seen: set[str] = set()
        for note in notes:
            term = _extract_term(note)
            norm = _normalize(term)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            full_text = "\n".join(clean_field_text(value) for value in note.fields.values() if value)
            nodes.append(
                ConceptNode(
                    term=term,
                    note_id=int(getattr(note, "note_id", 0)),
                    text=full_text,
                    tokens=_tokens(full_text),
                )
            )
        return cls(nodes)

    def contains(self, term: str) -> bool:
        return _normalize(term) in self.by_norm

    def canonical_term(self, term: str) -> str:
        node = self.by_norm.get(_normalize(term))
        return node.term if node else term

    def distractors_for(self, answer: str, count: int = 3) -> list[str]:
        answer_norm = _normalize(answer)
        target = self.by_norm.get(answer_norm)
        if not target:
            return []

        candidates: list[tuple[float, str]] = []
        for node in self.nodes:
            term_norm = _normalize(node.term)
            if term_norm == answer_norm:
                continue
            if _looks_like_inflection(answer, node.term):
                continue
            score = _similarity_score(target, node)
            candidates.append((score, node.term))

        candidates.sort(key=lambda item: (-item[0], item[1].lower()))
        selected: list[str] = []
        seen: set[str] = {answer_norm}
        for _, term in candidates:
            norm = _normalize(term)
            if norm in seen:
                continue
            selected.append(term)
            seen.add(norm)
            if len(selected) >= count:
                break
        return selected


def _extract_term(note: Any) -> str:
    for field_name in COMMON_FRONT_FIELDS:
        if field_name in note.fields:
            value = clean_field_text(note.fields[field_name])
            if value:
                return value

    front_text = clean_field_text(getattr(note, "front_text", ""))
    if front_text:
        match = _WORD_RE.search(front_text)
        return match.group(0) if match else front_text

    for value in note.fields.values():
        cleaned = clean_field_text(value)
        if cleaned:
            return cleaned
    return ""


def _similarity_score(a: ConceptNode, b: ConceptNode) -> float:
    if not a.tokens or not b.tokens:
        return 0.0
    overlap = len(a.tokens & b.tokens)
    union = len(a.tokens | b.tokens)
    jaccard = overlap / union if union else 0.0
    length_score = 1.0 / (1.0 + abs(len(a.term) - len(b.term)))
    return jaccard * 3.0 + length_score * 0.25


def apply_source_graph_options(result: dict[str, Any], source_notes: list[Any]) -> dict[str, Any]:
    """Replace model options with source-graph options when possible.

    The model still writes question stems/explanations. The final choices are
    constrained to the selected/source note pool.
    """
    graph = SourceKnowledgeGraph.from_notes(source_notes)
    questions = result.get("questions") or []
    if not graph.nodes or not questions:
        return result

    for item in questions:
        answer = str(item.get("answer") or "").strip()
        if not graph.contains(answer):
            continue
        canonical_answer = graph.canonical_term(answer)
        distractors = graph.distractors_for(canonical_answer, 3)
        if len(distractors) < 3:
            continue
        options = [canonical_answer, *distractors[:3]]
        random.shuffle(options)
        item["answer"] = canonical_answer
        item["options"] = options
    return result
