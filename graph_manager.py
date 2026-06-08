from __future__ import annotations

from typing import Any, List

from .knowledge_graph_distractor import ConceptNode, SourceKnowledgeGraph
from .source_compactor import clean_field_text

class LocalGraphManager:
    """Build and hold a lightweight local knowledge graph from Anki notes."""

    def __init__(self) -> None:
        self.graph: SourceKnowledgeGraph | None = None
        self.nodes: List[ConceptNode] = []

    def build_graph_from_notes(self, notes: list[Any], term_fields: list[str] | None = None) -> None:
        term_fields = term_fields or ["Front", "正面", "英语单词", "Expression", "Term", "单词", "词条"]
        nodes: List[ConceptNode] = []
        seen: set[str] = set()

        for note in notes:
            term = _term_from_note(note, term_fields)
            norm = term.lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            full_text = "\n".join(clean_field_text(value) for value in note.fields.values() if value)
            nodes.append(ConceptNode(term=term, note_id=int(getattr(note,'note_id',0)), text=full_text, tokens=set(full_text.split())))

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


def _term_from_note(note: Any, term_fields: list[str]) -> str:
    for field_name in term_fields:
        if field_name in note.fields:
            value = clean_field_text(note.fields[field_name])
            if value:
                return value
    # Use first field in note.fields as fallback
    if note.fields:
        first_value = next(iter(note.fields.values()))
        return clean_field_text(first_value)
    # Fallback: return empty string if nothing found
    return ''