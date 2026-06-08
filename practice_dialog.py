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
    QTextBrowser,
    QVBoxLayout,
)
from aqt.utils import showWarning

from .config import get_config
from .llm_client import LLMError, chat_completion
from .models import SourceNote
from .prompt_builder import build_prompt


def _render_notes_preview(notes: list[SourceNote]) -> str:
    parts: list[str] = []
    for note in notes[:10]:
        fields = "<br>".join(
            f"<b>{html.escape(name)}</b>: {html.escape(value[:300])}"
            for name, value in note.fields.items()
            if value.strip()
        )
        parts.append(
            f"<p><b>Note {note.note_id}</b> "
            f"<span style='color: #666;'>({html.escape(note.model_name)})</span><br>{fields}</p>"
        )
    if len(notes) > 10:
        parts.append(f"<p>... and {len(notes) - 10} more notes.</p>")
    return "".join(parts)


def _render_practice(result: dict[str, Any]) -> str:
    title = html.escape(str(result.get("title") or "AI Practice"))
    questions = result.get("questions") or []
    body = [f"<h2>{title}</h2>"]

    for index, item in enumerate(questions, start=1):
        question = html.escape(str(item.get("question") or ""))
        answer = html.escape(str(item.get("answer") or ""))
        explanation = html.escape(str(item.get("explanation") or ""))
        options = item.get("options") or []

        body.append(f"<h3>Question {index}</h3>")
        body.append(f"<p>{question.replace(chr(10), '<br>')}</p>")
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

    if not questions:
        body.append("<pre>" + html.escape(json.dumps(result, ensure_ascii=False, indent=2)) + "</pre>")

    return "".join(body)


def _main_window_from_parent(parent: Any) -> Any:
    """Return Anki's main window from either mw or a child window like Browser."""
    return getattr(parent, "mw", parent)


class PracticeDialog(QDialog):
    def __init__(self, parent: Any, notes: list[SourceNote]) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self.mw = _main_window_from_parent(parent)
        self.notes = notes
        self.setWindowTitle("AI Practice")
        self.resize(860, 680)

        self.question_type = QComboBox()
        self.question_type.addItem("Cloze / 完形填空", "cloze")
        self.question_type.addItem("Q&A / 问答题", "qa")

        self.generate_button = QPushButton("Generate Practice")
        self.generate_button.clicked.connect(self._generate)

        top = QHBoxLayout()
        top.addWidget(QLabel(f"Selected notes: {len(notes)}"))
        top.addWidget(QLabel("Question type:"))
        top.addWidget(self.question_type)
        top.addStretch(1)
        top.addWidget(self.generate_button)

        self.output = QTextBrowser()
        self.output.setOpenExternalLinks(True)
        self.output.setHtml(
            "<h2>AI Practice</h2>"
            "<p>Review the selected notes below, choose a question type, "
            "then click <b>Generate Practice</b>.</p>"
            "<hr>"
            + _render_notes_preview(notes)
        )

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _generate(self) -> None:
        config = get_config(self.mw)
        question_type = str(self.question_type.currentData())
        language = str(config.get("language") or "zh-CN")
        messages = build_prompt(self.notes, question_type, language)

        self.generate_button.setEnabled(False)
        self.output.setHtml("<p>Generating practice questions...</p>")
        try:
            result = chat_completion(config, messages)
        except LLMError as exc:
            showWarning(str(exc))
            self.output.setHtml(
                "<h2>Generation failed</h2>"
                f"<pre>{html.escape(str(exc))}</pre>"
            )
            return
        finally:
            self.generate_button.setEnabled(True)

        self.output.setHtml(_render_practice(result))
