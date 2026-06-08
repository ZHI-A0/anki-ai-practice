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

VisibleEdge = tuple[str, str, float]


class CenterNodeItem(QGraphicsEllipseItem):
    def __init__(self, canvas: "GraphCanvas", node_id: str, radius: float, tooltip: str) -> None:
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.canvas = canvas
        self.node_id = node_id
        self.setToolTip(tooltip)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def mousePressEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        try:
            event.accept()
        except Exception:
            pass
        self.canvas.focus_node(self.node_id)


class CenterTextItem(QGraphicsTextItem):
    def __init__(self, canvas: "GraphCanvas", node_id: str, text: str, tooltip: str) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.node_id = node_id
        self.setToolTip(tooltip)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def mousePressEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        try:
            event.accept()
        except Exception:
            pass
        self.canvas.focus_node(self.node_id)


class GraphCanvas(QGraphicsView):
    """Pseudo-3D center-focused graph canvas.

    - Click node: make it the center.
    - Drag background: rotate the graph.
    - Mouse wheel: zoom.
    - Similarity controls distance and node size.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMinimumHeight(500)
        self.manager: LocalGraphManager | None = None
        self.graph_type = "spelling"
        self.node_by_id: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self.adjacency: dict[str, list[tuple[str, float]]] = {}
        self.focus_id: str | None = None
        self.on_focus: Callable[[str, str], None] | None = None
        self.yaw = -0.35
        self.pitch = 0.22
        self.zoom = 1.0
        self._rotating = False
        self._last_mouse: tuple[float, float] | None = None
        self._layout3d: dict[str, tuple[float, float, float, float, str, float]] = {}
        self._visible_edges: list[VisibleEdge] = []

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
        self._layout3d, self._visible_edges = self._build_similarity_layout(node_id)
        self._render_3d()
        if self.on_focus:
            self.on_focus(node_id, self.graph_type)

    def mousePressEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        pos = _event_xy(event)
        item = None
        try:
            item = self.itemAt(int(pos[0]), int(pos[1]))
        except Exception:
            item = None

        if isinstance(item, (CenterNodeItem, CenterTextItem)):
            super().mousePressEvent(event)
            return

        self._rotating = True
        self._last_mouse = pos
        try:
            event.accept()
        except Exception:
            pass

    def mouseMoveEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        if self._rotating and self._last_mouse:
            x, y = _event_xy(event)
            last_x, last_y = self._last_mouse
            self.yaw += (x - last_x) * 0.008
            self.pitch += (y - last_y) * 0.008
            self.pitch = max(-1.25, min(1.25, self.pitch))
            self._last_mouse = (x, y)
            self._render_3d()
            try:
                event.accept()
            except Exception:
                pass
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        self._rotating = False
        self._last_mouse = None
        try:
            event.accept()
        except Exception:
            pass

    def wheelEvent(self, event: Any) -> None:  # pragma: no cover - Qt callback
        try:
            delta = event.angleDelta().y()
        except Exception:
            delta = 0
        if delta > 0:
            self.zoom *= 1.10
        elif delta < 0:
            self.zoom /= 1.10
        self.zoom = max(0.45, min(2.25, self.zoom))
        self._render_3d()
        try:
            event.accept()
        except Exception:
            pass

    def _build_similarity_layout(
        self, center_id: str
    ) -> tuple[dict[str, tuple[float, float, float, float, str, float]], list[VisibleEdge]]:
        layout: dict[str, tuple[float, float, float, float, str, float]] = {
            center_id: (0.0, 0.0, 0.0, 36.0, "center", 1.0)
        }
        visible_edges: list[VisibleEdge] = []
        first_neighbors = self.adjacency.get(center_id, [])[:22]
        seen = {center_id}

        first_dirs = _fibonacci_sphere(len(first_neighbors), phase=0.31)
        for index, (node_id, score) in enumerate(first_neighbors):
            if node_id not in self.node_by_id or node_id in seen:
                continue
            seen.add(node_id)
            direction = first_dirs[index]
            score_norm = _clamp_score(score)
            distance = 115.0 + (1.0 - score_norm) * 310.0
            size = 14.0 + score_norm * 18.0
            layout[node_id] = (
                direction[0] * distance,
                direction[1] * distance,
                direction[2] * distance,
                size,
                "first",
                score_norm,
            )
            visible_edges.append((center_id, node_id, score_norm))

        second_budget = 58
        second_count = 0
        for parent_index, (parent_id, _) in enumerate(first_neighbors):
            if parent_id not in layout:
                continue
            px, py, pz, _, _, _ = layout[parent_id]
            parent_vec = _normalize3((px, py, pz))
            candidates = self.adjacency.get(parent_id, [])[:8]
            local_dirs = _fibonacci_sphere(len(candidates), phase=0.17 + parent_index * 0.07)
            for candidate_index, (child_id, child_score) in enumerate(candidates):
                if child_id not in self.node_by_id or child_id in seen:
                    continue
                seen.add(child_id)
                child_score_norm = _clamp_score(child_score)
                local_dir = local_dirs[candidate_index]
                mixed = _normalize3(
                    (
                        parent_vec[0] * 0.70 + local_dir[0] * 0.30,
                        parent_vec[1] * 0.70 + local_dir[1] * 0.30,
                        parent_vec[2] * 0.70 + local_dir[2] * 0.30,
                    )
                )
                parent_distance = math.sqrt(px * px + py * py + pz * pz)
                distance = parent_distance + 95.0 + (1.0 - child_score_norm) * 260.0
                size = 7.0 + child_score_norm * 9.0
                layout[child_id] = (
                    mixed[0] * distance,
                    mixed[1] * distance,
                    mixed[2] * distance,
                    size,
                    "second",
                    child_score_norm,
                )
                visible_edges.append((parent_id, child_id, child_score_norm))
                second_count += 1
                if second_count >= second_budget:
                    return layout, visible_edges
        return layout, visible_edges

    def _render_3d(self) -> None:
        self.scene.clear()
        if not self.focus_id or not self._layout3d:
            return
        width = 1240
        height = 780
        cx = width / 2
        cy = height / 2
        projected: dict[str, tuple[float, float, float, float, str, float]] = {}

        for node_id, (x, y, z, size, layer, score) in self._layout3d.items():
            rx, ry, rz = _rotate3((x, y, z), self.yaw, self.pitch)
            perspective = 900.0 / max(260.0, 900.0 - rz)
            scale = self.zoom * perspective
            sx = cx + rx * scale
            sy = cy + ry * scale
            projected[node_id] = (sx, sy, rz, max(4.0, size * scale), layer, score)

        center_label = self.node_by_id.get(self.focus_id).term if self.focus_id in self.node_by_id else ""
        self._draw_title(center_label)
        self._draw_projected_edges(projected)
        self._draw_projected_nodes(projected)
        self.scene.setSceneRect(0, 0, width, height)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_title(self, center_label: str) -> None:
        title = self.scene.addText(
            f"3D Graph · Center: {center_label} · Drag blank area/lines to rotate · Wheel to zoom · Click node to recenter"
        )
        title.setDefaultTextColor(QColor(80, 80, 80))
        title.setPos(18, 12)
        title.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        title.setZValue(1000)

    def _draw_projected_edges(self, projected: dict[str, tuple[float, float, float, float, str, float]]) -> None:
        drawn: set[tuple[str, str]] = set()
        for source_id, target_id, score in self._visible_edges:
            if source_id not in projected or target_id not in projected:
                continue
            key = tuple(sorted((source_id, target_id)))
            if key in drawn:
                continue
            drawn.add(key)
            x1, y1, z1, _, layer1, _ = projected[source_id]
            x2, y2, z2, _, layer2, _ = projected[target_id]
            avg_z = (z1 + z2) / 2
            depth_front = _depth_frontness(avg_z)
            opacity = int((80 + _clamp_score(score) * 145) * (1.0 - 0.38 * depth_front))
            opacity = max(28, min(220, opacity))
            pen = QPen(QColor(120, 120, 120, opacity))
            pen.setWidth(3 if "center" in (layer1, layer2) else 1)
            line = self.scene.addLine(x1, y1, x2, y2, pen)
            line.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            line.setZValue(avg_z)

    def _draw_projected_nodes(self, projected: dict[str, tuple[float, float, float, float, str, float]]) -> None:
        for node_id, (x, y, z, radius, layer, score) in sorted(projected.items(), key=lambda item: item[1][2]):
            node = self.node_by_id[node_id]
            tooltip = _node_tooltip(node, layer, self.graph_type, score)
            brush = _brush_for_layer(layer, z)
            pen_alpha = 255 if layer == "center" else _alpha_for_depth(z, base=230, fade=95)
            pen = QPen(QColor(255, 255, 255, pen_alpha))
            pen.setWidth(2 if layer == "center" else 1)
            ellipse = CenterNodeItem(self, node_id, radius, tooltip)
            ellipse.setBrush(brush)
            ellipse.setPen(pen)
            ellipse.setPos(x, y)
            ellipse.setZValue(500 + z)
            self.scene.addItem(ellipse)

            label = node.term[:28 if layer == "center" else 20]
            text = CenterTextItem(self, node_id, label, tooltip)
            label_alpha = 245 if layer == "center" else _alpha_for_depth(z, base=220, fade=80)
            text.setDefaultTextColor(QColor(25, 25, 25, label_alpha) if layer != "second" else QColor(80, 80, 80, label_alpha))
            label_scale = 1.20 if layer == "center" else 0.92 if layer == "first" else 0.72
            if layer == "second" and radius < 7.8:
                label_scale = 0.0
            text.setScale(label_scale)
            text.setPos(x + radius + 5, y - radius)
            text.setZValue(520 + z)
            if label_scale > 0:
                self.scene.addItem(text)


def _event_xy(event: Any) -> tuple[float, float]:
    try:
        position = event.position()
        return float(position.x()), float(position.y())
    except Exception:
        try:
            position = event.pos()
            return float(position.x()), float(position.y())
        except Exception:
            return 0.0, 0.0


def _fibonacci_sphere(count: int, phase: float = 0.0) -> list[tuple[float, float, float]]:
    if count <= 0:
        return []
    points: list[tuple[float, float, float]] = []
    golden_angle = math.pi * (3 - math.sqrt(5))
    for index in range(count):
        y = 1 - (index / max(1, count - 1)) * 2
        radius = math.sqrt(max(0.0, 1 - y * y))
        theta = golden_angle * (index + phase)
        points.append((math.cos(theta) * radius, y, math.sin(theta) * radius))
    return points


def _normalize3(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = vector
    length = math.sqrt(x * x + y * y + z * z)
    if length <= 1e-9:
        return 1.0, 0.0, 0.0
    return x / length, y / length, z / length


def _rotate3(vector: tuple[float, float, float], yaw: float, pitch: float) -> tuple[float, float, float]:
    x, y, z = vector
    cos_yaw = math.cos(yaw)
    sin_yaw = math.sin(yaw)
    x1 = x * cos_yaw + z * sin_yaw
    z1 = -x * sin_yaw + z * cos_yaw
    cos_pitch = math.cos(pitch)
    sin_pitch = math.sin(pitch)
    y2 = y * cos_pitch - z1 * sin_pitch
    z2 = y * sin_pitch + z1 * cos_pitch
    return x1, y2, z2


def _clamp_score(score: float) -> float:
    return max(0.0, min(1.0, float(score or 0.0)))


def _depth_frontness(z: float) -> float:
    """0 = far/back, 1 = close/front."""
    return max(0.0, min(1.0, (z + 420.0) / 840.0))


def _alpha_for_depth(z: float, base: int, fade: int) -> int:
    # Closer-to-camera nodes are more transparent so they do not hide the center.
    return max(85, min(255, int(base - fade * _depth_frontness(z))))


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


def _brush_for_layer(layer: str, z: float = 0.0) -> QBrush:
    # Distinct layers + depth alpha. Foreground nodes become more transparent.
    if layer == "center":
        return QBrush(QColor(255, 150, 35, 255))
    alpha = _alpha_for_depth(z, base=235, fade=105)
    if layer == "first":
        return QBrush(QColor(52, 105, 235, alpha))
    return QBrush(QColor(40, 185, 150, alpha))


def _node_tooltip(node: GraphNode, layer: str, graph_type: str, score: float = 1.0) -> str:
    return (
        f"{node.term}\n"
        f"Layer: {layer}\n"
        f"Graph: {graph_type}\n"
        f"Similarity score: {score:.3f}\n\n"
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
            "<p>After building, open <b>Tools → AI Practice → View Knowledge Graph</b> for the 3D graph canvas.</p>"
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
            "<p>Select a graph and click View Graph. Click a node to move it to the center. Drag blank area/lines to rotate. Wheel to zoom.</p>"
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
        "<p>Open <b>Tools → AI Practice → View Knowledge Graph</b> to inspect the 3D graph.</p>"
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
