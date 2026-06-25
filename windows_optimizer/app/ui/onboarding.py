"""Мастер первого запуска: приветствие → находки → профиль.

Показывается один раз (флаг first_run в QSettings). Объясняет простым языком,
что приложение умеет, и предлагает подобрать профиль использования.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.core.logger import get_logger

_log = get_logger()


def _findings_text() -> str:
    """Быстрые находки без тяжёлых операций (не сканируем размеры диска)."""
    startup_n = 0
    safe_n = 0
    try:
        from app.modules.startup import StartupModule
        startup_n = len(StartupModule().scan())
    except Exception as e:
        _log.debug("Онбординг: скан автозапуска не удался: %s", e)
    try:
        from app.modules.registry import RegistryModule
        rows = RegistryModule().scan()
        safe_n = sum(1 for r in rows
                     if r.get("risk_level") == "safe" and r.get("status") != "applied")
    except Exception as e:
        _log.debug("Онбординг: скан твиков реестра не удался: %s", e)
    lines = []
    if startup_n:
        lines.append(f"🐢  Вместе с Windows запускается программ: {startup_n}.\n"
                     f"     Часть из них можно убрать из автозапуска для ускорения.")
    lines.append(f"⚡  Доступно безопасных улучшений: {safe_n}.\n"
                 f"     Их можно включить одной кнопкой на главном экране.")
    lines.append("🗑️  Временные файлы можно очистить в разделе «Очистка диска».")
    return "\n\n".join(lines)


class Onboarding(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добро пожаловать")
        self.setMinimumSize(560, 420)
        self.profile: Optional[str] = None

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_findings())
        self.stack.addWidget(self._page_profile())

        nav = QHBoxLayout()
        self.btn_skip = QPushButton("Пропустить")
        self.btn_next = QPushButton("Далее")
        self.btn_next.setObjectName("Primary")
        self.btn_skip.clicked.connect(self.accept)
        self.btn_next.clicked.connect(self._next)
        nav.addWidget(self.btn_skip)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

    def _title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("Title")
        lbl.setWordWrap(True)
        return lbl

    def _page_welcome(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 24, 24, 24)
        v.addStretch(1)
        v.addWidget(self._title("Добро пожаловать в Windows Optimizer"))
        sub = QLabel("Это приложение поможет ускорить компьютер безопасными "
                     "настройками. Перед любыми изменениями оно сохраняет состояние "
                     "системы, поэтому всё можно отменить.\n\nПосмотрим, что можно улучшить.")
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        v.addWidget(sub)
        v.addStretch(1)
        return w

    def _page_findings(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 24, 24, 24)
        v.addWidget(self._title("Вот что мы нашли"))
        self._findings_lbl = QLabel("…")
        self._findings_lbl.setObjectName("Subtitle")
        self._findings_lbl.setWordWrap(True)
        v.addWidget(self._findings_lbl)
        v.addStretch(1)
        return w

    def _page_profile(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 24, 24, 24)
        v.addWidget(self._title("Как вы используете компьютер?"))
        sub = QLabel("Мы подберём, какие улучшения отметить как рекомендованные.")
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        v.addWidget(sub)
        row = QHBoxLayout()
        for label, key in (("🎮 Игры", "gaming"), ("💼 Работа", "work"), ("🎬 Видео/Творчество", "media")):
            b = QPushButton(label)
            b.setMinimumHeight(56)
            b.clicked.connect(lambda _=False, k=key: self._choose_profile(k))
            row.addWidget(b)
        v.addLayout(row)
        v.addStretch(1)
        return w

    def _next(self) -> None:
        idx = self.stack.currentIndex()
        if idx == 0:
            self._findings_lbl.setText(_findings_text())
        if idx >= self.stack.count() - 1:
            self.accept()
            return
        self.stack.setCurrentIndex(idx + 1)
        if self.stack.currentIndex() == self.stack.count() - 1:
            self.btn_next.setText("Готово")

    def _choose_profile(self, key: str) -> None:
        self.profile = key
        try:
            from PyQt6.QtCore import QSettings
            QSettings("WindowsOptimizer", "App").setValue("profile", key)
        except Exception as e:
            _log.debug("Не удалось сохранить профиль онбординга: %s", e)
        self.accept()


def maybe_show(parent: QWidget) -> None:
    """Показать мастер один раз (по флагу first_run)."""
    try:
        from PyQt6.QtCore import QSettings

        s = QSettings("WindowsOptimizer", "App")
        if str(s.value("first_run", "true")).lower() != "false":
            dlg = Onboarding(parent)
            dlg.exec()
            s.setValue("first_run", "false")
    except Exception as e:
        _log.debug("Мастер первого запуска не показан: %s", e)
