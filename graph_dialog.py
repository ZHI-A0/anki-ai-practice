from __future__ import annotations

import html
import math
from typing import Any, Callable

from aqt import mw
from aqt.qt import (
    QColor,
    QBrush,
    QComboBox,
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsTextItem,
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
from .graph_manager import GraphEdge, GraphNode, LocalGraphManager
from .graph_store import GRAPH_STORAGE_DIR, load_graph, save_graph
from .note_selector import collect_selected_notes


class CenterNodeItem(QGraphicsEllipseItem):
    def __init__(self, canvas: "GraphCanvas", node_id: str, radius: float, tooltip: str) -> None:
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.canvas = canvas
        self.node_id = node_id
        self.setToolTip(tooltip)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        self.canvas.focus_node(self.node_id)
        super().mousePressEvent(event)


class CenterTextItem(QGraphicsTextItem):
    def __init__(self, canvas: "GraphCanvas", node_id: str, text: str, tooltip: str) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.node_id = node_id
        self.setToolTip(tooltip)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def mousePressEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        self.canvas.focus_node(self.node_id)
        super().mousePressEvent(event)


class GraphCanvas(QGraphicsView):
    """Interactive center-focused graph canvas.

    Clicking a node recenters the view around that node:
    - center node: largest
    - first-hop neighbors: inner ring, medium size
    - second-hop neighbors: outer ring, smaller size
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumHeight(460)
        self.manager: LocalGraphManager | None = None
        self.graph_type = "spelling"
        self.node_by_id: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.adjacency: dict[str, list[tuple[str, float]]] = {}
        self.focus_id: str | None = None
        self.on_focus: Callable[[str, str], None] | None = None

    def set_graph(self, manager: LocalGraphManager, graph_type: str) -> None:
        self.manager = manager
        self.graph_type = graph_type
        self.node_by_id = {node.id: node for node in manager.nodes}
        self.edges = list(manager.graphs.get(graph_type, []))
        self.adjacency = _build_undirected_adjacency(self.edges)
        if not manager.nodes:
            self.scene.clear()
            self.scene.addText("No graph nodes found. Rebuild the graph first.")
            return
        self.focus_node(manager.nodes[0].id)

    def focus_node(self, node_id: str) -> None:
        if not self.manager or node_id not in self.node_by_id:
            return
        self.focus_id = node_id
        self._draw_centered(node_id)
        if self.on_focus:
            self.on_focus(node_id, self.graph_type)

    def _draw_centered(self, center_id: str) -> None:
        self.scene.clear()
        center = self.node_by_id[center_id]
        first = [node_id for node_id, _ in self.adjacency.get(center_id, [])[:18] if node_id in self.node_by_id]
        first_set = set(first)
        second: list[str] = []
        seen = {center_id, *first_set}
        for first_id in first:
            for candidate_id, _ in self.adjacency.get(first_id, [])[:8]:
                if candidate_id in self.node_by_id and candidate_id not in seen:
                    second.append(candidate_id)
                    seen.add(candidate_id)
                if len(second) >= 42:
                    break
            if len(second) >= 42:
                break

        visible_ids = [center_id, *first, *second]
        visible_set = set(visible_ids)
        width = 1180
        height = 760
        cx = width / 2
        cy = height / 2
        positions: dict[str, tuple[float, float, float, str]] = {center_id: (cx, cy, 30, "center")}

        _place_ring(first, positions, cx, cy, radius=175, node_radius=18, layer="first")
        _place_ring(second, positions, cx, cy, radius=325, node_radius=10, layer="second")

        self._draw_background(width, height, center.term)
        self._draw_edges(visible_set, positions)
        self._draw_nodes(visible_ids, positions)
        self.scene.setSceneRect(0, 0, width, height)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_background(self, width: int, height: int, center_label: str) -> None:
        self.scene.addRect(0, 0, width, height, QPen(QColor(230, 230, 230)), QBrush(QColor(250, 250, 250)))
        title = self.scene.addText(f"Center: {center_label}  ·  Click any node to recenter")
        title.setDefaultTextColor(QColor(80, 80, 80))
        title.setPos(18, 12)
        title.setZValue(10)

    def _draw_edges(self, visible_set: set[str], positions: dict[str, tuple[float, float, float, str]]) -> None:
        drawn: set[tuple[str, str]] = set()
        for edge in self.edges:
            if edge.source not in visible_set or edge.target not in visible_set:
                continue
            key = tuple(sorted((edge.source, edge.target)))
            if key in drawn:
                continue
            drawn.add(key)
            x1, y1, _, layer1 = positions[edge.source]
            x2, y2, _, layer2 = positions[edge.target]
            opacity = 50 + int(min(0.9, max(0.05, edge.score)) * 140)
            pen = QPen(QColor(130, 130, 130, opacity))
            pen.setWidth(2 if "center" in (layer1, layer2) else 1)
            line = self.scene.addLine(x1, y1, x2, y2, pen)
            line.setZValue(1)

    def _draw_nodes(self, visible_ids: list[str], positions: dict[str, tuple[float, float, float, str]]) -> None:
        for node_id in visible_ids:
            node = self.node_by_id[node_id]
            x, y, radius, layer = positions[node_id]
            tooltip = _node_tooltip(node, layer, self.graph_type)
            brush = _brush_for_layer(layer)
            pen = QPen(QColor(255, 255, 255))
            pen.setWidth(2 if layer == "center" else 1)
            ellipse = CenterNodeItem(self, node_id, radius, tooltip)
            ellipse.setBrush(brush)
            ellipse.setPen(pen)
            ellipse.setPos(x, y)
            ellipse.setZValue(4 if layer == "center" else 3)
            self.scene.addItem(ellipse)

            label = node.term[:28 if layer == "center" else 20]
            text = CenterTextItem(self, node_id, label, tooltip)
            text.setDefaultTextColor(QColor(25, 25, 25) if layer != "second" else QColor(90, 90, 90))
            text.setScale(1.25 if layer == "center" else 1.0 if layer == "first" else 0.82)
            text.setPos(x + radius + 6, y - radius)
            text.setZValue(5)
            self.scene.addItem(text)


def _place_ring(
    node_ids: list[str],
    positions: dict[str, tuple[float, float, float, str]],
    cx: float,
    cy: float,
    radius: float,
    node_radius: float,
    layer: str,
) -> None:
    if not node_ids:
        return
    for index, node_id in enumerate(node_ids):
        angle = 2 * math.pi * index / len(node_ids)
        positions[node_id] = (
            cx + radius * math.cos(angle),
            cy + radius * math.sin(angle),
            node_radius,
            layer,
        )


def _build_undirected_adjacency(edges: list[GraphEdge]) -> dict[str, list[tuple[str, float]]]:
    best: dict[tuple[str, str], float] = {}
    for edge in edges:
        if not edge.source or not edge.target or edge.source == edge.target:
            continue
        key = tuple(sorted((edge.source, edge.target)))
        best[key] = max(best.get(key, 0.0), float(edge.score or 0.0))

    adjacency: dict[str, list[tuple[str, float]]] = {}
    for (a, b), score in best.items():
        adjacency.setdefault(a, []).append((b, score))
        adjacency.setdefault(b, []).append((a, score))
    for node_id in adjacency:
        adjacency[node_id].sort(key=lambda item: item[1], reverse=True)
    return adjacency


def _brush_for_layer(layer: str) -> QBrush:
    if layer == "center":
        return QBrush(QColor(255, 170, 55))
    if layer == "first":
        return QBrush(QColor(79, 107, 237))
    return QBrush(QColor(145, 180, 255))


def _node_tooltip(node: GraphNode, layer: str, graph_type: str) -> str:
    return (
        f"{node.term}\n"
        f"Layer: {layer}\n"
        f"Graph: {graph_type}\n\n"
        f"Meaning: {node.meaning}\n\n"
        f"Example: {node.example}"
    )


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
        self.resize(1240, 900)
        self.current_manager: LocalGraphManager | None = None
        self.current_deck_name = ""

        self.deck_combo = QComboBox()
        self._load_decks()

        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItem("Spelling graph", "spelling")
        self.graph_type_combo.addItem("Meaning graph", "meaning")
        self.graph_type_combo.currentIndexChanged.connect(self._redraw_current_graph)

        self.view_button = QPushButton("View Graph")
        self.view_button.clicked.connect(self._view_graph)

        top = QHBoxLayout()
        top.addWidget(QLabel("Graph:"))
        top.addWidget(self.deck_combo, 1)
        top.addWidget(QLabel("Type:"))
        top.addWidget(self.graph_type_combo)
        top.addWidget(self.view_button)

        self.canvas = GraphCanvas(self)
        self.canvas.on_focus = self._update_focus_info
        self.output = QTextBrowser()
        self.output.setHtml(
            "<h2>View Knowledge Graph</h2>"
            "<p>Select a graph and click View Graph. Click a node or its label to move it to the center. Nodes are draggable. Hover nodes to see details.</p>"
        )

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.output)
        splitter.setSizes([620, 260])

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
        self.current_deck_name = self.deck_combo.currentText()
        try:
            self.current_manager = load_graph(str(graph_name))
        except Exception as exc:
            showWarning(f"Could not load graph:\n{exc}")
            return
        self._redraw_current_graph()

    def _redraw_current_graph(self) -> None:
        if not self.current_manager:
            return
        graph_type = str(self.graph_type_combo.currentData() or "spelling")
        self.canvas.set_graph(self.current_manager, graph_type)

    def _update_focus_info(self, node_id: str, graph_type: str) -> None:
        if not self.current_manager:
            return
        self.output.setHtml(_render_focus_panel(self.current_deck_name, self.current_manager, graph_type, node_id))


def _safe_graph_name(deck_name: str) -> str:
    return deck_name.replace("/", "_").replace("\\", "_").replace(":", "__")


def _render_build_summary(deck_name: str, source_count: int, path: str, manager: LocalGraphManager) -> str:
    return (
        f"<h2>{html.escape(deck_name)}</h2>"
        f"<p>Nodes: <b>{source_count}</b></p>"
        f"<p>Spelling edges: <b>{len(manager.graphs.get('spelling', []))}</b></p>"
        f"<p>Meaning edges: <b>{len(manager.graphs.get('meaning', []))}</b></p>"
        f"<p>Saved to:</p><pre>{html.escape(path)}</pre>"
        "<p>Open <b>Tools → AI Practice → View Knowledge Graph</b> to inspect the center-focused graph.</p>"
        "<h3>Spelling preview</h3>"
        + _render_rows_table(manager.preview_rows("spelling", 40))
        + "<h3>Meaning preview</h3>"
        + _render_rows_table(manager.preview_rows("meaning", 40))
    )


def _render_focus_panel(deck_name: str, manager: LocalGraphManager, graph_type: str, node_id: str) -> str:
    node_by_id = {node.id: node for node in manager.nodes}
    node = node_by_id.get(node_id)
    if not node:
        return "<p>Node not found.</p>"
    adjacency = _build_undirected_adjacency(manager.graphs.get(graph_type, []))
    neighbors = adjacency.get(node_id, [])[:20]
    body = [
        f"<h2>{html.escape(deck_name)} — {html.escape(graph_type)}</h2>",
        f"<h3>Center node: {html.escape(node.term)}</h3>",
        f"<p><b>Meaning:</b> {html.escape(node.meaning)}</p>",
        f"<p><b>Example:</b> {html.escape(node.example)}</p>",
        f"<p>Nodes: <b>{len(manager.nodes)}</b>; Edges: <b>{len(manager.graphs.get(graph_type, []))}</b></p>",
        "<h3>Nearest neighbors</h3>",
        "<table border='1' cellspacing='0' cellpadding='6'>",
        "<tr><th>Neighbor</th><th>Score</th><th>Meaning</th></tr>",
    ]
    for neighbor_id, score in neighbors:
        neighbor = node_by_id.get(neighbor_id)
        if not neighbor:
            continue
        body.append(
            "<tr>"
            f"<td>{html.escape(neighbor.term)}</td>"
            f"<td>{score:.3f}</td>"
            f"<td>{html.escape(neighbor.meaning)}</td>"
            "</tr>"
        )
    body.append("</table>")
    return "".join(body)


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
