from __future__ import annotations

import html
import json
from typing import Any

from aqt.operations import QueryOp
from aqt.qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    Qt,
)
from aqt.utils import showInfo, showWarning

from .card_creator import save_practice_as_cards
from .config import get_config
from .llm_client import chat_completion
from .models import SourceNote
from .prompt_builder import build_prompt
from .source_compactor import clean_field_text, compact_notes_for_llm


def _render_notes_preview(notes: list[SourceNote]) -> str:
    parts: list[str] = []
    for index, note in enumerate(notes[:20], start=1):
        front = clean_field_text(note.front_text or note.first_field_text())
        if len(front) > 500:
            front = front[:500].rstrip() + "..."
        parts.append(
            f"<p><b>Selected item {index}</b> "
            f"<span style='color: #666;'>({html.escape(note.model_name)})</span><br>"
            f"{html.escape(front)}</p>"
        )
    if len(notes) > 20:
        parts.append(f"<p>... and {len(notes) - 20} more selected items.</p>")
    return "".join(parts)


def _render_practice_cards(result: dict[str, Any]) -> str:
    title = html.escape(str(result.get("title") or "AI Practice"))
    questions = result.get("questions") or []
    body = [
        "<style>"
        ".practice-card{border:1px solid #e5e5e5;border-radius:14px;padding:14px;margin:14px 0;background:#fff;}"
        ".practice-question{font-size:16px;font-weight:600;margin-bottom:12px;}"
        ".practice-options{display:grid;grid-template-columns:1fr 1fr;gap:8px;}"
        ".practice-option{border:1px solid #ddd;border-radius:10px;padding:8px 10px;background:#fafafa;}"
        ".practice-badge{display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;border-radius:50%;border:1px solid #aaa;margin-right:8px;font-weight:bold;}"
        ".practice-answer{margin-top:12px;padding:10px;border-radius:10px;background:#f6f6f6;}"
        "</style>"
        f"<h2>{title}</h2>"
    ]

    for index, item in enumerate(questions, start=1):
        question = html.escape(str(item.get("question") or ""))
        answer = html.escape(str(item.get("answer") or ""))
        explanation = html.escape(str(item.get("explanation") or ""))
        options = list(item.get("options") or [])[:4]
        labels = ["A", "B", "C", "D"]

        body.append("<div class='practice-card'>")
        body.append(f"<h3>Question {index}</h3>")
        body.append(f"<div class='practice-question'>{question.replace(chr(10), '<br>')}</div>")
        if options:
            body.append("<div class='practice-options'>")
            for label, option in zip(labels, options):
                body.append(
                    "<div class='practice-option'>"
                    f"<span class='practice-badge'>{label}</span>{html.escape(str(option))}"
                    "</div>"
                )
            body.append("</div>")
        body.append("<div class='practice-answer'>")
        body.append(f"<b>Answer:</b> {answer}<br>")
        if explanation:
            body.append(f"<b>Explanation:</b> {explanation.replace(chr(10), '<br>')}")
        body.append("</div>")
        body.append("</div>")

    if not questions:
        body.append("<pre>" + html.escape(json.dumps(result, ensure_ascii=False, indent=2)) + "</pre>")

    return "".join(body)


def _main_window_from_parent(parent: Any) -> Any:
    return getattr(parent, "mw", parent)


class PracticeDialog(QDialog):
    def __init__(self, parent: Any, notes: list[SourceNote]) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.mw = _main_window_from_parent(parent)
        self.notes = notes
        self.generated_result: dict[str, Any] | None = None
        self.setWindowTitle("AI Practice")
        self.resize(1100, 760)

        self.question_type = QComboBox()
        self.question_type.addItem("Temporary cards / 临时练习卡", "cloze")
        self.question_type.addItem("Q&A / 问答题", "qa")

        self.generate_button = QPushButton("Generate Temporary Cards")
        self.generate_button.clicked.connect(self._generate)

        self.save_button = QPushButton("Save as Anki Cards")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_as_cards)

        top = QHBoxLayout()
        top.addWidget(QLabel(f"Selected notes: {len(notes)}"))
        top.addWidget(QLabel("Practice type:"))
        top.addWidget(self.question_type)
        top.addStretch(1)
        top.addWidget(self.generate_button)
        top.addWidget(self.save_button)

        self.selection_preview = QTextBrowser()
        self.selection_preview.setOpenExternalLinks(True)
        self.selection_preview.setHtml(
            "<h2>Selection Preview</h2>"
            "<p>The model will use the front-side display text by default.</p>"
            "<hr>"
            + _render_notes_preview(notes)
        )

        self.practice_view = QTextBrowser()
        self.practice_view.setOpenExternalLinks(True)
        self.practice_view.setHtml(
            "<h2>Temporary Practice Cards</h2>"
            "<p>Click <b>Generate Temporary Cards</b> to create a temporary practice set. "
            "Your selection preview will remain visible on the left.</p>"
            "<p>After generation, click <b>Save as Anki Cards</b> to create interactive choice cards in "
            "<b>AI Practice::Generated</b>.</p>"
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.selection_preview)
        splitter.addWidget(self.practice_view)
        splitter.setSizes([420, 680])

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(splitter)
        self.setLayout(layout)

    def _generate(self) -> None:
        config = get_config(self.mw)
        question_type = str(self.question_type.currentData())
        language = str(config.get("language") or "auto")
        compact_source = compact_notes_for_llm(self.notes, config)
        messages = build_prompt(self.notes, question_type, language, config)

        self.generated_result = None
        self.save_button.setEnabled(False)
        self.generate_button.setEnabled(False)
        self.practice_view.setHtml(
            "<h2>Generating...</h2>"
            "<p>The request is running in the background. You can keep Anki open while it completes.</p>"
            f"<p>Compressed source length: {len(compact_source)} characters.</p>"
        )

        def run_in_background(_: Any) -> dict[str, Any]:
            return chat_completion(config, messages)

        def on_success(result: dict[str, Any]) -> None:
            self.generated_result = result
            self.generate_button.setEnabled(True)
            self.save_button.setEnabled(True)
            self.practice_view.setHtml(_render_practice_cards(result))

        def on_failure(exc: Exception) -> None:
            self.generate_button.setEnabled(True)
            self.save_button.setEnabled(False)
            showWarning(str(exc))
            self.practice_view.setHtml(
                "<h2>Generation failed</h2>"
                f"<pre>{html.escape(str(exc))}</pre>"
            )

        QueryOp(
            parent=self,
            op=run_in_background,
            success=on_success,
        ).failure(on_failure).without_collection().run_in_background()

    def _save_as_cards(self) -> None:
        if not self.generated_result:
            showWarning("Generate practice cards first.")
            return

        try:
            added = save_practice_as_cards(self.mw, self.generated_result, self.notes)
        except Exception as exc:
            showWarning(f"Failed to save generated cards:\n{exc}")
            return

        showInfo(f"Saved {added} cards to AI Practice::Generated.")
