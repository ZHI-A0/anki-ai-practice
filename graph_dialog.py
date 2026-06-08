from __future__ import annotations

import html
import math
from typing import Any

from aqt import mw
from aqt.qt import (
    QColor,
    QBrush,
    QComboBox,
    QDialog,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPen,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    Qt,
)
from aqt.utils import showInfo, showWarning

from .config import get_config, split_fields
from .graph_manager import LocalGraphManager
from .graph_store import GRAPH_STORAGE_DIR, load_graph, save_graph
from .note_selector import collect_selected_notes


class GraphCanvas(QGraphicsView):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumHeight(420)

    def set_graph(self, manager: LocalGraphManager, graph_type: str, max_nodes: int = 160) -> None:
        self.scene.clear()
        nodes = manager.nodes[:max_nodes]
        if not nodes:
            self.scene.addText("No graph nodes found. Rebuild the graph first.")
            return

        node_ids = {node.id for node in nodes}
        edges = [
            edge
            for edge in manager.graphs.get(graph_type, [])
            if edge.source in node_ids and edge.target in node_ids
        ]
        edges = sorted(edges, key=lambda edge: edge.score, reverse=True)[: max_nodes * 5]

        width = 1100
        height = 760
        cx = width / 2
        cy = height / 2
        radius = min(width, height) * 0.38
        positions: dict[str, tuple[float, float]] = {}

        for index, node in enumerate(nodes):
            angle = 2 * math.pi * index / max(1, len(nodes))
            # Slight spiral avoids every label sitting on the exact same ring.
            local_radius = radius * (0.72 + 0.28 * ((index % 5) / 4))
            positions[node.id] = (cx + local_radius * math.cos(angle), cy + local_radius * math.sin(angle))

        edge_pen = QPen(QColor(150, 150, 150, 90))
        edge_pen.setWidth(1)
        for edge in edges:
            x1, y1 = positions[edge.source]
            x2, y2 = positions[edge.target]
            line = self.scene.addLine(x1, y1, x2, y2, edge_pen)
            line.setZValue(0)

        node_brush = QBrush(QColor(79, 107, 237))
        node_pen = QPen(QColor(255, 255, 255))
        node_pen.setWidth(1)
        text_color = QColor(30, 30, 30)

        for node in nodes:
            x, y = positions[node.id]
            tooltip = f"{node.term}\n\nMeaning: {node.meaning}\n\nExample: {node.example}"
            ellipse = self.scene.addEllipse(x - 8, y - 8, 16, 16, node_pen, node_brush)
            ellipse.setToolTip(tooltip)
            ellipse.setZValue(2)
            _make_movable(ellipse)

            text = self.scene.addText(node.term[:24])
            text.setDefaultTextColor(text_color)
            text.setPos(x + 10, y - 10)
            text.setToolTip(tooltip)
            text.setZValue(3)
            _make_movable(text)

        self.scene.setSceneRect(0, 0, width, height)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


def _make_movable(item: Any) -> None:
    try:
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
    except Exception:
        pass


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
            f"<p>graph_max_notes: <b>{html.escape(str(config.get('graph_max_notes')))}</b>; "
            f"graph_top_k: <b>{html.escape(str(config.get('graph_top_k')))}</b></p>"
            "<p>The graph is saved as JSON in:</p>"
            f"<pre>{html.escape(GRAPH_STORAGE_DIR)}</pre>"
            "<p>After building, open <b>Tools → AI Practice → View Knowledge Graph</b> for the interactive graph canvas.</p>"
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
        self.output.setHtml("<h2>Building...</h2><p>Anki may be busy while the graph is built. For large decks this can take a while.</p>")
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
        self.output.setHtml(_render_build_summary(deck_name, len(manager.nodes), path, manager))
        showInfo(
            f"Built dual graph with {len(manager.nodes)} nodes.\n"
            f"Spelling edges: {len(manager.graphs.get('spelling', []))}\n"
            f"Meaning edges: {len(manager.graphs.get('meaning', []))}"
        )


class GraphViewerDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle("View Knowledge Graph")
        self.resize(1180, 840)

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

        self.canvas = GraphCanvas(self)
        self.output = QTextBrowser()
        self.output.setHtml(
            "<h2>View Knowledge Graph</h2>"
            "<p>Select a graph and click View Graph. Nodes are draggable. Hover nodes to see details.</p>"
        )

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.output)
        splitter.setSizes([560, 260])

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(splitter)
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
        self.canvas.set_graph(manager, graph_type)
        self.output.setHtml(_render_graph_table(deck_name, len(manager.nodes), manager, graph_type))


def _safe_graph_name(deck_name: str) -> str:
    return deck_name.replace("/", "_").replace("\\", "_").replace(":", "__")


def _render_build_summary(deck_name: str, source_count: int, path: str, manager: LocalGraphManager) -> str:
    return (
        f"<h2>{html.escape(deck_name)}</h2>"
        f"<p>Nodes: <b>{source_count}</b></p>"
        f"<p>Spelling edges: <b>{len(manager.graphs.get('spelling', []))}</b></p>"
        f"<p>Meaning edges: <b>{len(manager.graphs.get('meaning', []))}</b></p>"
        f"<p>Saved to:</p><pre>{html.escape(path)}</pre>"
        "<p>Open <b>Tools → AI Practice → View Knowledge Graph</b> to see the interactive graph canvas.</p>"
        "<h3>Spelling preview</h3>"
        + _render_rows_table(manager.preview_rows("spelling", 40))
        + "<h3>Meaning preview</h3>"
        + _render_rows_table(manager.preview_rows("meaning", 40))
    )


def _render_graph_table(deck_name: str, source_count: int, manager: LocalGraphManager, graph_type: str) -> str:
    return (
        f"<h2>{html.escape(deck_name)} — {html.escape(graph_type)}</h2>"
        f"<p>Nodes: <b>{source_count}</b>; Edges: <b>{len(manager.graphs.get(graph_type, []))}</b></p>"
        "<p>The canvas above shows the first 160 nodes. Drag nodes to inspect dense regions; hover for meaning/example.</p>"
        + _render_rows_table(manager.preview_rows(graph_type, 160))
    )


def _render_rows_table(rows: list[tuple[str, list[str]]]) -> str:
    body = ["<table border='1' cellspacing='0' cellpadding='6'>"]
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
