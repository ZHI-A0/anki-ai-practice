from __future__ import annotations

import html
import json
from typing import Any

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
from aqt.utils import showWarning

from .config import get_config
from .llm_client import LLMError, chat_completion
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
    body = [f"<h2>{title}</h2>"]

    for index, item in enumerate(questions, start=1):
        question = html.escape(str(item.get("question") or ""))
        answer = html.escape(str(item.get("answer") or ""))
        explanation = html.escape(str(item.get("explanation") or ""))
        options = item.get("options") or []

        body.append(
            "<div style='border:1px solid #ddd;border-radius:8px;"
            "padding:12px;margin:12px 0;background:#fff;'>"
        )
        body.append(f"<h3>Question {index}</h3>")
        body.append(f"<p style='font-size:16px;'>{question.replace(chr(10), '<br>')}</p>")
        if options:
            body.append("<ol type='A'>")
            for option in options:
                body.append(f"<li>{html.escape(str(option))}</li>")
            body.append("</ol>")
        body.append("<details><summary>Show answer and explanation</summary>")
        body.append(f"<p><b>Answer:</b> {answer}</p>")
        if explanation:
            body.append(f"<p><b>Explanation:</b> {explanation.replace(chr(10), '<br>')}</p>")
        body.append("</details>")
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
        self.setWindowTitle("AI Practice")
        self.resize(1100, 760)

        self.question_type = QComboBox()
        self.question_type.addItem("Temporary cards / 临时练习卡", "cloze")
        self.question_type.addItem("Q&A / 问答题", "qa")

        self.generate_button = QPushButton("Generate Temporary Cards")
        self.generate_button.clicked.connect(self._generate)

        top = QHBoxLayout()
        top.addWidget(QLabel(f"Selected notes: {len(notes)}"))
        top.addWidget(QLabel("Practice type:"))
        top.addWidget(self.question_type)
        top.addStretch(1)
        top.addWidget(self.generate_button)

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
        language = str(config.get("language") or "zh-CN")
        compact_source = compact_notes_for_llm(self.notes, config)
        messages = build_prompt(self.notes, question_type, language, config)

        self.generate_button.setEnabled(False)
        self.practice_view.setHtml(
            "<h2>Generating...</h2>"
            "<p>Contacting the configured LLM API. Anki may appear busy until the request finishes.</p>"
            f"<p>Compressed source length: {len(compact_source)} characters.</p>"
        )
        try:
            result = chat_completion(config, messages)
        except LLMError as exc:
            showWarning(str(exc))
            self.practice_view.setHtml(
                "<h2>Generation failed</h2>"
                f"<pre>{html.escape(str(exc))}</pre>"
            )
            return
        finally:
            self.generate_button.setEnabled(True)

        self.practice_view.setHtml(_render_practice_cards(result))
