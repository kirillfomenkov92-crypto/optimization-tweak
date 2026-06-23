"""Главное окно: левая навигация + правая рабочая область (QStackedWidget)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QStatusBar,
    QVBoxLayout, QWidget, QMainWindow, QScrollArea,
)

from app.ui.dashboard import Dashboard
from app.modules.registry import RegistryModule
from app.modules.startup import StartupModule

_STYLE = Path(__file__).resolve().parent / "styles" / "dark_theme.qss"
_ICON = Path(__file__).resolve().parents[2] / "resources" / "icons" / "app.ico"


class _ModulePlaceholder(QWidget):
    """Простая панель модуля на этапе фундамента: показывает результат scan()."""

    def __init__(self, title: str, rows: List[str]) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        layout.addWidget(head)
        area = QScrollArea()
        area.setWidgetResizable(True)
        inner = QWidget()
        inner_l = QVBoxLayout(inner)
        if not rows:
            inner_l.addWidget(QLabel("Нет данных (доступно на Windows)."))
        for r in rows:
            lbl = QLabel("• " + r)
            lbl.setWordWrap(True)
            inner_l.addWidget(lbl)
        inner_l.addStretch(1)
        area.setWidget(inner)
        layout.addWidget(area)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Windows Optimizer Pro")
        self.setMinimumSize(1100, 700)
        if _ICON.exists():
            self.setWindowIcon(QIcon(str(_ICON)))

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(self.sidebar)
        side_l.setContentsMargins(12, 16, 12, 16)
        side_l.setSpacing(6)

        self.stack = QStackedWidget()
        self.stack.setObjectName("WorkArea")

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for title, widget in self._pages():
            self._add_page(side_l, title, widget)
        side_l.addStretch(1)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов")

        if self._btn_group.buttons():
            self._btn_group.buttons()[0].setChecked(True)
            self.stack.setCurrentIndex(0)

        self._apply_style()

    def _pages(self) -> List[Tuple[str, QWidget]]:
        reg = RegistryModule()
        startup = StartupModule()
        reg_rows = [f"[{r['status']}] {r['name']} ({r['risk']})" for r in reg.scan()]
        startup_rows = [f"{r['name']} — {r.get('source','')}" for r in startup.scan()]
        return [
            ("🏠 Дашборд", Dashboard()),
            ("🚀 Автозагрузка", _ModulePlaceholder("Автозагрузка", startup_rows)),
            ("📝 Реестр", _ModulePlaceholder("Реестр", reg_rows)),
        ]

    def _add_page(self, side_layout: QVBoxLayout, title: str, widget: QWidget) -> None:
        idx = self.stack.addWidget(widget)
        btn = QPushButton(title)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _=False, i=idx: self.stack.setCurrentIndex(i))
        self._btn_group.addButton(btn)
        side_layout.addWidget(btn)

    def _apply_style(self) -> None:
        try:
            if _STYLE.exists():
                self.setStyleSheet(_STYLE.read_text(encoding="utf-8"))
        except Exception:
            pass
