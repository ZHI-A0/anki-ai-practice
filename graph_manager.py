from __future__ import annotations

from typing import Any, List

from .knowledge_graph_distractor import ConceptNode, SourceKnowledgeGraph
from .source_compactor import clean_field_text

class LocalGraphManager:
    """
    Manages a persistent local knowledge graph built from selected notes.
    Provides optional visualization and selection for reverse problem generation.
    """
    def __init__(self):
        self.graph: SourceKnowledgeGraph | None = None
        self.nodes: List[ConceptNode] = []

    def build_graph_from_notes(self, notes: List[Any]) -> None:
        nodes: List[ConceptNode] = []
        seen: set[str] = set()
        for note in notes:
            term = clean_field_text(note.fields.get('Front', '') or note.first_field_text())
            norm = term.lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            full_text = '\n'.join(clean_field_text(value) for value in note.fields.values() if value)
            nodes.append(ConceptNode(term=term, note_id=int(getattr(note,'note_id',0)), text=full_text, tokens=set(full_text.split())))
        self.nodes = nodes
        self.graph = SourceKnowledgeGraph(nodes)

    def visualize_graph(self) -> None:
        if not self.graph:
            print('Graph is empty. Build it first.')
            return
        print('Nodes:')
        for node in self.graph.nodes:
            neighbors = self.graph.get_neighbors(node.term)
            print(f'{node.term} -> {neighbors}')

    def get_graph(self) -> SourceKnowledgeGraph | None:
        return self.graph
