from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .source_compactor import clean_field_text


@dataclass(slots=True)
class GraphNode:
    id: str
    term: str
    note_id: int
    meaning: str
    example: str
    text: str


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    score: float


class LocalGraphManager:
    """Build and hold two local graphs from Anki notes.

    - spelling graph: similarity based on the term spelling.
    - meaning graph: similarity based on meaning/definition fields.
    """

    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []
        self.graphs: dict[str, list[GraphEdge]] = {"spelling": [], "meaning": []}

    def build_graph_from_notes(
        self,
        notes: list[Any],
        term_fields: list[str] | None = None,
        meaning_fields: list[str] | None = None,
        example_fields: list[str] | None = None,
        top_k: int = 5,
    ) -> None:
        term_fields = term_fields or ["Front", "正面", "英语单词", "Expression", "Term", "单词", "词条"]
        meaning_fields = meaning_fields or ["中文释义", "Meaning", "Back", "背面", "释义", "答案"]
        example_fields = example_fields or ["英语例句", "Example", "Examples", "Sentence", "例句"]

        nodes: list[GraphNode] = []
        seen: set[str] = set()
        for note in notes:
            field_map = _note_field_map(note)
            term = _term_from_field_map(field_map, term_fields)
            norm = term.lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            meaning = _first_value(field_map, meaning_fields)
            example = _first_value(field_map, example_fields)
            full_text = "\n".join(clean_field_text(value) for value in field_map.values() if value)
            nodes.append(
                GraphNode(
                    id=norm,
                    term=term,
                    note_id=int(getattr(note, "id", 0) or getattr(note, "note_id", 0) or 0),
                    meaning=meaning,
                    example=example,
                    text=full_text,
                )
            )

        self.nodes = nodes
        self.graphs = {
            "spelling": _build_edges(nodes, "spelling", top_k),
            "meaning": _build_edges(nodes, "meaning", top_k),
        }

    def preview_rows(self, graph_type: str = "meaning", limit: int = 80) -> list[tuple[str, list[str]]]:
        node_by_id = {node.id: node for node in self.nodes}
        rows: list[tuple[str, list[str]]] = []
        edges_by_source: dict[str, list[GraphEdge]] = {}
        for edge in self.graphs.get(graph_type, []):
            edges_by_source.setdefault(edge.source, []).append(edge)

        for node in self.nodes[:limit]:
            edges = sorted(edges_by_source.get(node.id, []), key=lambda edge: edge.score, reverse=True)[:5]
            neighbors = [node_by_id[edge.target].term for edge in edges if edge.target in node_by_id]
            rows.append((node.term, neighbors))
        return rows

    def to_dict(self, deck_name: str) -> dict[str, Any]:
        return {
            "version": 2,
            "deck_name": deck_name,
            "nodes": [
                {
                    "id": node.id,
                    "term": node.term,
                    "note_id": node.note_id,
                    "meaning": node.meaning,
                    "example": node.example,
                    "text": node.text,
                }
                for node in self.nodes
            ],
            "graphs": {
                graph_type: [
                    {"source": edge.source, "target": edge.target, "score": round(edge.score, 6)}
                    for edge in edges
                ]
                for graph_type, edges in self.graphs.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalGraphManager":
        manager = cls()
        manager.nodes = [
            GraphNode(
                id=str(item.get("id") or str(item.get("term", "")).lower()),
                term=str(item.get("term") or ""),
                note_id=int(item.get("note_id") or 0),
                meaning=str(item.get("meaning") or ""),
                example=str(item.get("example") or ""),
                text=str(item.get("text") or ""),
            )
            for item in data.get("nodes", [])
        ]
        raw_graphs = data.get("graphs") or {}
        manager.graphs = {}
        for graph_type in ("spelling", "meaning"):
            manager.graphs[graph_type] = [
                GraphEdge(
                    source=str(edge.get("source") or ""),
                    target=str(edge.get("target") or ""),
                    score=float(edge.get("score") or 0),
                )
                for edge in raw_graphs.get(graph_type, [])
            ]
        return manager


def _build_edges(nodes: list[GraphNode], graph_type: str, top_k: int) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for source in nodes:
        scored: list[tuple[float, GraphNode]] = []
        for target in nodes:
            if source.id == target.id:
                continue
            if graph_type == "spelling":
                score = _spelling_similarity(source.term, target.term)
            else:
                score = _meaning_similarity(source.meaning or source.text, target.meaning or target.text)
            if score > 0:
                scored.append((score, target))
        scored.sort(key=lambda item: item[0], reverse=True)
        for score, target in scored[:top_k]:
            edges.append(GraphEdge(source=source.id, target=target.id, score=score))
    return edges


def _spelling_similarity(a: str, b: str) -> float:
    a_norm = clean_field_text(a).lower()
    b_norm = clean_field_text(b).lower()
    if not a_norm or not b_norm:
        return 0.0
    bigram_score = _jaccard(_char_ngrams(a_norm, 2), _char_ngrams(b_norm, 2))
    trigram_score = _jaccard(_char_ngrams(a_norm, 3), _char_ngrams(b_norm, 3))
    length_score = 1.0 / (1.0 + abs(len(a_norm) - len(b_norm)))
    prefix_score = _common_prefix_len(a_norm, b_norm) / max(len(a_norm), len(b_norm))
    return bigram_score * 0.45 + trigram_score * 0.30 + length_score * 0.15 + prefix_score * 0.10


def _meaning_similarity(a: str, b: str) -> float:
    a_norm = clean_field_text(a).lower()
    b_norm = clean_field_text(b).lower()
    if not a_norm or not b_norm:
        return 0.0
    token_score = _jaccard(_tokens(a_norm), _tokens(b_norm))
    char_score = _jaccard(_char_ngrams(a_norm, 2), _char_ngrams(b_norm, 2))
    return token_score * 0.55 + char_score * 0.45


def _tokens(text: str) -> set[str]:
    # For Chinese definitions without spaces, char bigrams are more useful;
    # this token layer still helps for English or mixed fields.
    return {part.strip() for part in text.replace("；", " ").replace(";", " ").replace("，", " ").replace(",", " ").split() if part.strip()}


def _char_ngrams(text: str, n: int) -> set[str]:
    compact = "".join(ch for ch in text if not ch.isspace())
    if len(compact) <= n:
        return {compact} if compact else set()
    return {compact[index : index + n] for index in range(len(compact) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _common_prefix_len(a: str, b: str) -> int:
    count = 0
    for x, y in zip(a, b):
        if x != y:
            break
        count += 1
    return count


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


def _first_value(field_map: dict[str, str], field_names: list[str]) -> str:
    for field_name in field_names:
        value = clean_field_text(field_map.get(field_name, ""))
        if value:
            return value
    return ""
