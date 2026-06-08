from __future__ import annotations

import html
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
from .note_selector import collect_notes_from_browser, collect_selected_notes


class GraphBuildDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.parent_window = parent or mw
        self.setWindowTitle("Build Knowledge Graph")
        self.resize(820, 620)

        self.deck_combo = QComboBox()
        self._load_decks()

        self.build_button = QPushButton("Build Graph from Deck")
        self.build_button.clicked.connect(self._build_from_deck)

        self.build_selection_button = QPushButton("Build Graph from Active Browser Selection")
        self.build_selection_button.clicked.connect(self._build_from_selection)

        top = QHBoxLayout()
        top.addWidget(QLabel("Deck:"))
        top.addWidget(self.deck_combo, 1)
        top.addWidget(self.build_button)
        top.addWidget(self.build_selection_button)

        self.output = QTextBrowser()
        self.output.setHtml(
            "<h2>Build Knowledge Graph</h2>"
            "<p>Choose a deck and build a local graph. The graph is saved as JSON in:</p>"
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
        max_notes = int(config.get("max_notes") or 30)
        return [mw.col.get_note(nid) for nid in note_ids[:max_notes]]

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
        term_fields = split_fields(config.get("local_graph_fields")) or split_fields(config.get("llm_graph_fields"))
        manager = LocalGraphManager()
        manager.build_graph_from_notes(notes, term_fields)
        path = save_graph(manager, _safe_graph_name(deck_name))
        rows = manager.preview_rows(40)
        self.output.setHtml(_render_graph_preview(deck_name, len(notes), path, rows))
        showInfo(f"Built graph with {len(manager.nodes)} nodes.")


class GraphViewerDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle("View Knowledge Graph")
        self.resize(820, 620)

        self.deck_combo = QComboBox()
        self._load_decks()

        self.view_button = QPushButton("View Graph")
        self.view_button.clicked.connect(self._view_graph)

        top = QHBoxLayout()
        top.addWidget(QLabel("Graph:"))
        top.addWidget(self.deck_combo, 1)
        top.addWidget(self.view_button)

        self.output = QTextBrowser()
        self.output.setHtml(
            "<h2>View Knowledge Graph</h2>"
            "<p>Select a graph to preview its nodes and nearest source-graph distractors.</p>"
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
        try:
            manager = load_graph(str(graph_name))
        except Exception as exc:
            showWarning(f"Could not load graph:\n{exc}")
            return
        self.output.setHtml(_render_graph_preview(deck_name, len(manager.nodes), "", manager.preview_rows(120)))


def _safe_graph_name(deck_name: str) -> str:
    return deck_name.replace("/", "_").replace("\\", "_").replace(":", "__")


def _render_graph_preview(deck_name: str, source_count: int, path: str, rows: list[tuple[str, list[str]]]) -> str:
    body = [
        f"<h2>{html.escape(deck_name)}</h2>",
        f"<p>Source notes/nodes: <b>{source_count}</b></p>",
    ]
    if path:
        body.append(f"<p>Saved to:</p><pre>{html.escape(path)}</pre>")
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
