from __future__ import annotations

import html
import math
from typing import Any

from aqt import mw
from aqt.qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)
from aqt.utils import showInfo, showWarning

from .config import get_config, split_fields
from .graph_manager import LocalGraphManager
from .graph_store import GRAPH_STORAGE_DIR, load_graph, save_graph
from .note_selector import collect_selected_notes


class GraphBuildDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.parent_window = parent or mw
        self.setWindowTitle("Build Knowledge Graph")
        self.resize(980, 720)

        self.deck_combo = QComboBox()
        self._load_decks()

        self.build_button = QPushButton("Build Dual Graphs from Deck")
        self.build_button.clicked.connect(self._build_from_deck)

        self.build_selection_button = QPushButton("Build Dual Graphs from Active Browser Selection")
        self.build_selection_button.clicked.connect(self._build_from_selection)

        top = QHBoxLayout()
        top.addWidget(QLabel("Deck:"))
        top.addWidget(self.deck_combo, 1)
        top.addWidget(self.build_button)
        top.addWidget(self.build_selection_button)

        self.output = QTextBrowser()
        config = get_config(mw)
        self.output.setHtml(
            "<h2>Build Knowledge Graph</h2>"
            "<p>This builds two graphs: <b>spelling</b> from word forms, and <b>meaning</b> from meaning fields.</p>"
            f"<p>graph_max_notes: <b>{html.escape(str(config.get('graph_max_notes')))}</b>; graph_top_k: <b>{html.escape(str(config.get('graph_top_k')))}</b></p>"
            "<p>The graph is saved as JSON in:</p>"
            f"<pre>{html.escape(GRAPH_STORAGE_DIR)}</pre>"
        )

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _load_decks(self) -> None:
        if mw is None or mw.col is None:
            return
        decks = sorted(mw.col.decks.all_names_and_ids(), key=lambda item: item.name.lower())
        for deck in decks:
            self.deck_combo.addItem(deck.name, int(deck.id))

    def _notes_for_deck(self, deck_name: str) -> list[Any]:
        query = f'deck:"{deck_name}"'
        note_ids = mw.col.find_notes(query)
        config = get_config(mw)
        graph_max_notes = int(config.get("graph_max_notes") or 5000)
        if graph_max_notes > 0:
            note_ids = note_ids[:graph_max_notes]
        return [mw.col.get_note(nid) for nid in note_ids]

    def _build_from_deck(self) -> None:
        deck_name = self.deck_combo.currentText()
        if not deck_name:
            showWarning("Choose a deck first.")
            return
        notes = self._notes_for_deck(deck_name)
        self._build_and_save(notes, deck_name)

    def _build_from_selection(self) -> None:
        try:
            notes = collect_selected_notes(mw)
        except Exception as exc:
            showWarning(f"Failed to collect selected notes:\n{exc}")
            return
        if not notes:
            showWarning("Open Browse, select notes/cards, then try again.")
            return
        deck_name = self.deck_combo.currentText() or "active_selection"
        self._build_and_save(notes, deck_name)

    def _build_and_save(self, notes: list[Any], deck_name: str) -> None:
        if not notes:
            showWarning("No notes found for this source.")
            return
        config = get_config(mw)
        term_fields = split_fields(config.get("graph_term_fields")) or split_fields(config.get("local_graph_fields"))
        meaning_fields = split_fields(config.get("graph_meaning_fields")) or split_fields(config.get("local_meaning_fields"))
        example_fields = split_fields(config.get("graph_example_fields")) or split_fields(config.get("local_example_fields"))
        top_k = int(config.get("graph_top_k") or 5)

        manager = LocalGraphManager()
        manager.build_graph_from_notes(notes, term_fields, meaning_fields, example_fields, top_k=top_k)
        path = save_graph(manager, _safe_graph_name(deck_name))
        self.output.setHtml(_render_graph_preview(deck_name, len(manager.nodes), path, manager, "spelling"))
        showInfo(
            f"Built dual graph with {len(manager.nodes)} nodes.\n"
            f"Spelling edges: {len(manager.graphs.get('spelling', []))}\n"
            f"Meaning edges: {len(manager.graphs.get('meaning', []))}"
        )


class GraphViewerDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle("View Knowledge Graph")
        self.resize(980, 720)

        self.deck_combo = QComboBox()
        self._load_decks()

        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItem("Spelling graph", "spelling")
        self.graph_type_combo.addItem("Meaning graph", "meaning")

        self.view_button = QPushButton("View Graph")
        self.view_button.clicked.connect(self._view_graph)

        top = QHBoxLayout()
        top.addWidget(QLabel("Graph:"))
        top.addWidget(self.deck_combo, 1)
        top.addWidget(QLabel("Type:"))
        top.addWidget(self.graph_type_combo)
        top.addWidget(self.view_button)

        self.output = QTextBrowser()
        self.output.setHtml(
            "<h2>View Knowledge Graph</h2>"
            "<p>Select a graph to preview nodes and edges. Rebuild the graph if you still see old empty data.</p>"
        )

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _load_decks(self) -> None:
        if mw is None or mw.col is None:
            return
        decks = sorted(mw.col.decks.all_names_and_ids(), key=lambda item: item.name.lower())
        for deck in decks:
            self.deck_combo.addItem(deck.name, _safe_graph_name(deck.name))

    def _view_graph(self) -> None:
        graph_name = self.deck_combo.currentData()
        deck_name = self.deck_combo.currentText()
        graph_type = str(self.graph_type_combo.currentData() or "spelling")
        try:
            manager = load_graph(str(graph_name))
        except Exception as exc:
            showWarning(f"Could not load graph:\n{exc}")
            return
        self.output.setHtml(_render_graph_preview(deck_name, len(manager.nodes), "", manager, graph_type))


def _safe_graph_name(deck_name: str) -> str:
    return deck_name.replace("/", "_").replace("\\", "_").replace(":", "__")


def _render_graph_preview(
    deck_name: str,
    source_count: int,
    path: str,
    manager: LocalGraphManager,
    graph_type: str,
) -> str:
    edges = manager.graphs.get(graph_type, [])
    rows = manager.preview_rows(graph_type, 120)
    body = [
        f"<h2>{html.escape(deck_name)} — {html.escape(graph_type)}</h2>",
        f"<p>Nodes: <b>{source_count}</b>; Edges: <b>{len(edges)}</b></p>",
    ]
    if path:
        body.append(f"<p>Saved to:</p><pre>{html.escape(path)}</pre>")
    body.append(_render_svg_graph(manager, graph_type))
    body.append("<h3>Nearest graph options</h3>")
    body.append("<table border='1' cellspacing='0' cellpadding='6'>")
    body.append("<tr><th>Node</th><th>Nearest graph options</th></tr>")
    for term, neighbors in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(term)}</td>"
            f"<td>{html.escape(', '.join(neighbors))}</td>"
            "</tr>"
        )
    body.append("</table>")
    return "".join(body)


def _render_svg_graph(manager: LocalGraphManager, graph_type: str, max_nodes: int = 80) -> str:
    nodes = manager.nodes[:max_nodes]
    if not nodes:
        return "<p>No graph nodes found. Rebuild the graph.</p>"
    node_ids = {node.id for node in nodes}
    edges = [edge for edge in manager.graphs.get(graph_type, []) if edge.source in node_ids and edge.target in node_ids][:240]
    width = 900
    height = 560
    cx = width / 2
    cy = height / 2
    radius = 230
    positions: dict[str, tuple[float, float]] = {}
    for index, node in enumerate(nodes):
        angle = 2 * math.pi * index / max(1, len(nodes))
        positions[node.id] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))

    parts = [
        "<div style='overflow:auto;border:1px solid #ddd;border-radius:10px;padding:8px;background:#fff;'>",
        f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}' xmlns='http://www.w3.org/2000/svg'>",
        "<rect width='100%' height='100%' fill='#fafafa'/>",
    ]
    for edge in edges:
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        opacity = max(0.15, min(0.85, edge.score))
        parts.append(
            f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' "
            f"stroke='#999' stroke-opacity='{opacity:.2f}' stroke-width='1'/>"
        )
    for node in nodes:
        x, y = positions[node.id]
        label = html.escape(node.term[:18])
        title = html.escape(f"{node.term}\n{node.meaning}\n{node.example}")
        parts.append(f"<g><title>{title}</title><circle cx='{x:.1f}' cy='{y:.1f}' r='8' fill='#4f6bed'/>")
        parts.append(f"<text x='{x + 10:.1f}' y='{y + 4:.1f}' font-size='11' fill='#222'>{label}</text></g>")
    parts.append("</svg></div>")
    parts.append("<p style='color:#666;'>SVG preview shows the first 80 nodes. Hover a node to see details. Drag/click interaction will be added with the WebView graph viewer next.</p>")
    return "".join(parts)
