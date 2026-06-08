from __future__ import annotations

import json
import os
from typing import Any

from .graph_manager import LocalGraphManager

GRAPH_STORAGE_DIR = os.path.join(os.path.expanduser("~"), ".anki_ai_practice_graphs")

if not os.path.exists(GRAPH_STORAGE_DIR):
    os.makedirs(GRAPH_STORAGE_DIR, exist_ok=True)


def save_graph(manager: LocalGraphManager, deck_name: str) -> str:
    """Save current local graph to a JSON file."""
    path = os.path.join(GRAPH_STORAGE_DIR, f"{deck_name}.json")
    data = manager.to_dict(deck_name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_graph(deck_name: str) -> LocalGraphManager:
    path = os.path.join(GRAPH_STORAGE_DIR, f"{deck_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Graph file {path} not found.")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Backward compatibility with the old single-graph format.
    if "graphs" not in data:
        manager = LocalGraphManager()
        from .knowledge_graph_distractor import ConceptNode
        from .knowledge_graph_distractor import SourceKnowledgeGraph

        legacy_nodes = []
        for item in data.get("nodes", []):
            legacy_nodes.append(
                ConceptNode(
                    term=item.get("term", ""),
                    note_id=int(item.get("note_id") or 0),
                    text=item.get("text", ""),
                    tokens=set(str(item.get("text", "")).split()),
                )
            )
        # Keep old files loadable, but users should rebuild for dual graphs.
        manager.nodes = []
        manager.graphs = {"spelling": [], "meaning": []}
        return manager

    return LocalGraphManager.from_dict(data)
