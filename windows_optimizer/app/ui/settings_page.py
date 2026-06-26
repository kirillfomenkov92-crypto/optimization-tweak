"""Страница настроек: тема (тёмная/светлая) и сведения о профиле."""
from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)


class SettingsPage(QWidget):
    def __init__(self, set_theme: Callable[[str], None], current_theme: str = "dark") -> None:
        super().__init__()
        self._set_theme = set_theme

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        head = QLabel("Настройки")
        head.setObjectName("Title")
        root.addWidget(head)

        # Внешний вид — в карточке, для аккуратной группировки.
        card = QFrame(); card.setObjectName("Card")
        cv = QVBoxLayout(card)
        cv.setSpacing(10)
        ct = QLabel("Внешний вид"); ct.setObjectName("CardTitle")
        cv.addWidget(ct)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        self.theme = QComboBox()
        self.theme.addItems(["Тёмная", "Светлая"])
        self.theme.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.theme.setFixedWidth(220)
        form.addRow("Тема оформления:", self.theme)
        cv.addLayout(form)
        root.addWidget(card)

        # Кнопка нормальной ширины, прижата влево (а не на весь экран).
        actions = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        apply_btn.setObjectName("Primary")
        apply_btn.setFixedWidth(180)
        apply_btn.clicked.connect(self._apply)
        actions.addWidget(apply_btn)
        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        actions.addWidget(self.status)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addStretch(1)

    def _apply(self) -> None:
        name = "dark" if self.theme.currentIndex() == 0 else "light"
        self._set_theme(name)
        self.status.setText("Тема применена.")
