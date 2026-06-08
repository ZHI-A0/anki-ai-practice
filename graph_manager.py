from __future__ import annotations

from typing import Any

from .knowledge_graph_distractor import ConceptNode, SourceKnowledgeGraph
from .source_compactor import clean_field_text


class LocalGraphManager:
    """Build and hold a lightweight local knowledge graph from Anki notes."""

    def __init__(self) -> None:
        self.graph: SourceKnowledgeGraph | None = None
        self.nodes: list[ConceptNode] = []

    def build_graph_from_notes(self, notes: list[Any], term_fields: list[str] | None = None) -> None:
        term_fields = term_fields or ["Front", "正面", "英语单词", "Expression", "Term", "单词", "词条"]
        nodes: list[ConceptNode] = []
        seen: set[str] = set()

        for note in notes:
            field_map = _note_field_map(note)
            term = _term_from_field_map(field_map, term_fields)
            norm = term.lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            full_text = "\n".join(clean_field_text(value) for value in field_map.values() if value)
            nodes.append(
                ConceptNode(
                    term=term,
                    note_id=int(getattr(note, "id", 0) or getattr(note, "note_id", 0) or 0),
                    text=full_text,
                    tokens={token.lower() for token in full_text.split() if token.strip()},
                )
            )

        self.nodes = nodes
        self.graph = SourceKnowledgeGraph(nodes)

    def preview_rows(self, limit: int = 80) -> list[tuple[str, list[str]]]:
        if not self.graph:
            return []
        rows: list[tuple[str, list[str]]] = []
        for node in self.graph.nodes[:limit]:
            try:
                neighbors = self.graph.distractors_for(node.term, 5)
            except Exception:
                neighbors = []
            rows.append((node.term, neighbors))
        return rows

    def get_graph(self) -> SourceKnowledgeGraph | None:
        return self.graph


def _note_field_map(note: Any) -> dict[str, str]:
    """Return a field-name -> value map for both wrapped SourceNote and Anki Note."""
    fields = getattr(note, "fields", None)
    if isinstance(fields, dict):
        return {str(name): str(value or "") for name, value in fields.items()}

    keys: list[str] = []
    try:
        keys = [str(key) for key in note.keys()]
    except Exception:
        pass

    if isinstance(fields, list):
        if keys and len(keys) == len(fields):
            return {keys[index]: str(value or "") for index, value in enumerate(fields)}
        return {str(index): str(value or "") for index, value in enumerate(fields)}

    # Last-resort fallback for any object that supports mapping-like access.
    result: dict[str, str] = {}
    for key in keys:
        try:
            result[key] = str(note[key] or "")
        except Exception:
            continue
    return result


def _term_from_field_map(field_map: dict[str, str], term_fields: list[str]) -> str:
    for field_name in term_fields:
        value = clean_field_text(field_map.get(field_name, ""))
        if value:
            return value

    for value in field_map.values():
        cleaned = clean_field_text(value)
        if cleaned:
            return cleaned
    return ""
