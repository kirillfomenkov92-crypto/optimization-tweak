"""Неблокирующий overlay прогресса оптимизации поверх контента."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from app.ui.styles.design_tokens import Colors, Radius, Typography


class ProgressOverlay(QWidget):
    """Затемняет родителя и показывает карточку с шагами и прогрессом."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {Colors.BG_BASE}EE;")
        self.hide()

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("MetricCard")
        self.card.setFixedWidth(460)
        self.card.setStyleSheet(
            f"#MetricCard {{ background-color: {Colors.BG_SURFACE}; "
            f"border: 1px solid {Colors.BORDER_ACCENT}; border-radius: {Radius.XL}px; padding: 24px; }}"
        )
        cl = QVBoxLayout(self.card)
        cl.setSpacing(14)

        self.title = QLabel("Оптимизируем систему…")
        self.title.setObjectName("Title")
        self.step = QLabel("")
        self.step.setObjectName("Subtitle")
        self.step.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.steps_box = QLabel("")
        self.steps_box.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: {Typography.SIZE_SM}px;")
        self.steps_box.setWordWrap(True)
        self.cancel = QPushButton("Скрыть")
        self.cancel.clicked.connect(self.hide)

        cl.addWidget(self.title)
        cl.addWidget(self.step)
        cl.addWidget(self.bar)
        cl.addWidget(self.steps_box)
        cl.addWidget(self.cancel, 0, Qt.AlignmentFlag.AlignRight)

        outer.addWidget(self.card)
        self._done_lines = []

    def begin(self) -> None:
        self._done_lines = []
        self.steps_box.setText("")
        self.title.setText("Оптимизируем систему…")
        self.bar.setValue(0)
        self.resize(self.parent().size())
        self.show()
        self.raise_()

    def set_progress(self, text: str, percent: int) -> None:
        self.step.setText(text)
        self.bar.setValue(percent)

    def mark_done(self, text: str) -> None:
        self._done_lines.append(f"✓ {text}")
        self.steps_box.setText("\n".join(self._done_lines))

    def finish(self, summary: str) -> None:
        self.title.setText("Готово!")
        self.step.setText(summary)
        self.bar.setValue(100)
        self.cancel.setText("Закрыть")
