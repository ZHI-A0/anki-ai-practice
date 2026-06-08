from __future__ import annotations

from typing import Any

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from aqt import mw

from .config import get_config, save_config


class SettingsDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle('AI Practice Settings')
        self.resize(700, 500)

        self.config = get_config()

        layout = QVBoxLayout()

        # Generation mode
        layout.addWidget(QLabel('Generation Mode:'))
        self.generation_mode_combo = QComboBox()
        self.generation_mode_combo.addItems(['local_first', 'llm_first'])
        self.generation_mode_combo.setCurrentText(self.config.get('generation_mode', 'local_first'))
        layout.addWidget(self.generation_mode_combo)

        # Question language
        layout.addWidget(QLabel('Question Language (source/default):'))
        self.question_lang_edit = QLineEdit(self.config.get('question_language', 'source'))
        layout.addWidget(self.question_lang_edit)

        # Explanation language
        layout.addWidget(QLabel('Explanation Language:'))
        self.explanation_lang_edit = QLineEdit(self.config.get('explanation_language', 'zh-CN'))
        layout.addWidget(self.explanation_lang_edit)

        # Local-first specific fields
        layout.addWidget(QLabel('Local-first Example Fields (comma-separated):'))
        self.local_example_fields_edit = QLineEdit(self.config.get('local_example_fields', '英语例句,Example'))
        layout.addWidget(self.local_example_fields_edit)

        layout.addWidget(QLabel('Local-first Target Fields (comma-separated):'))
        self.local_target_fields_edit = QLineEdit(self.config.get('local_target_fields', 'Front,英语单词'))
        layout.addWidget(self.local_target_fields_edit)

        layout.addWidget(QLabel('Local-first Graph Fields (comma-separated):'))
        self.local_graph_fields_edit = QLineEdit(self.config.get('local_graph_fields', 'Front,英语单词'))
        layout.addWidget(self.local_graph_fields_edit)

        # Use existing examples
        self.use_existing_examples_chk = QCheckBox('Use existing examples for blanks')
        self.use_existing_examples_chk.setChecked(self.config.get('use_existing_examples', True))
        layout.addWidget(self.use_existing_examples_chk)

        # LLM-specific fields
        layout.addWidget(QLabel('LLM Source Fields (for LLM-first mode, comma-separated):'))
        self.llm_source_fields_edit = QLineEdit(self.config.get('llm_source_fields', 'Front,正面,Question,问题,英语单词'))
        layout.addWidget(self.llm_source_fields_edit)

        layout.addWidget(QLabel('LLM Graph Fields (for LLM-first mode, comma-separated):'))
        self.llm_graph_fields_edit = QLineEdit(self.config.get('llm_graph_fields', 'Front,英语单词'))
        layout.addWidget(self.llm_graph_fields_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.save)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def save(self) -> None:
        self.config['generation_mode'] = self.generation_mode_combo.currentText()
        self.config['question_language'] = self.question_lang_edit.text().strip() or 'source'
        self.config['explanation_language'] = self.explanation_lang_edit.text().strip() or 'zh-CN'
        self.config['local_example_fields'] = self.local_example_fields_edit.text().strip()
        self.config['local_target_fields'] = self.local_target_fields_edit.text().strip()
        self.config['local_graph_fields'] = self.local_graph_fields_edit.text().strip()
        self.config['use_existing_examples'] = self.use_existing_examples_chk.isChecked()
        self.config['llm_source_fields'] = self.llm_source_fields_edit.text().strip()
        self.config['llm_graph_fields'] = self.llm_graph_fields_edit.text().strip()
        save_config(self, self.config)
        self.close()