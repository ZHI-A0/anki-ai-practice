from __future__ import annotations

import json
import os
from typing import Any

from .graph_manager import LocalGraphManager

GRAPH_STORAGE_DIR = os.path.join(os.path.expanduser('~'), '.anki_ai_practice_graphs')

if not os.path.exists(GRAPH_STORAGE_DIR):
    os.makedirs(GRAPH_STORAGE_DIR, exist_ok=True)


def save_graph(manager: LocalGraphManager, deck_name: str) -> str:
    """Save current local graph to a JSON file."""
    if manager.graph is None:
        raise ValueError('Graph is empty. Build it first.')

    path = os.path.join(GRAPH_STORAGE_DIR, f'{deck_name}.json')
    data = {
        'deck_name': deck_name,
        'nodes': [
            {
                'term': node.term,
                'note_id': node.note_id,
                'text': node.text,
            }
            for node in manager.graph.nodes
        ]
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_graph(deck_name: str) -> LocalGraphManager:
    path = os.path.join(GRAPH_STORAGE_DIR, f'{deck_name}.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f'Graph file {path} not found.')

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    manager = LocalGraphManager()
    nodes = []
    for n in data.get('nodes', []):
        from .knowledge_graph_distractor import ConceptNode
        nodes.append(ConceptNode(term=n['term'], note_id=n['note_id'], text=n['text'], tokens=set(n['text'].split())))
    from .knowledge_graph_distractor import SourceKnowledgeGraph
    manager.graph = SourceKnowledgeGraph(nodes)
    manager.nodes = nodes
    return manager