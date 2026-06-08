from __future__ import annotations

from typing import Any

from .config import split_fields
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
            term = _term_from_note(note, term_fields)
            norm = term.lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            full_text = "\n".join(clean_field_text(value) for value in note.fields.values() if value)
            nodes.append(
                ConceptNode(
                    term=term,
                    note_id=int(getattr(note, "note_id", 0)),
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
            rows.append((node.term, self.graph.distractors_for(node.term, 5)))
        return rows

    def get_graph(self) -> SourceKnowledgeGraph | None:
        return self.graph


def _term_from_note(note: Any, term_fields: list[str]) -> str:
    for field_name in term_fields:
        if field_name in note.fields:
            value = clean_field_text(note.fields[field_name])
            if value:
                return value
    return clean_field_text(getattr(note, "front_text", "") or note.first_field_text())
