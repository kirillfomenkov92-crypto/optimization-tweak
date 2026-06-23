"""Универсальная панель действия: список находок + кнопка «Применить».

Подходит модулям с единым действием (apply_*), например Сеть и Игры:
показывает результат scan() и выполняет переданный callable в фоне, при
необходимости — с предварительным бэкапом реестра.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)

from app.core import backup
from app.ui.widgets.worker import OperationWorker


class ActionPanel(QWidget):
    def __init__(self, title: str, scan_fn: Callable[[], List[Dict]],
                 apply_fn: Callable[[], Dict], apply_label: str = "Применить рекомендованное",
                 backup_before: bool = True, hint: str = "") -> None:
        super().__init__()
        self._scan_fn = scan_fn
        self._apply_fn = apply_fn
        self._backup_before = backup_before
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        root.addWidget(head)
        if hint:
            h = QLabel(hint)
            h.setObjectName("Subtitle")
            h.setWordWrap(True)
            root.addWidget(h)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить")
        self.btn_apply = QPushButton(apply_label)
        self.btn_apply.setObjectName("Primary")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_apply.clicked.connect(self._apply)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_apply)
        root.addLayout(btns)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        rows = self._scan_fn()
        for r in rows:
            if "name" in r:
                self.list.addItem(f"[{r.get('status','')}] {r['name']} — {r.get('description','')}")
            elif "item" in r:
                self.list.addItem(f"{r['item']}: {r.get('value','')}")
            else:
                self.list.addItem(str(r))
        self.status.setText(f"Пунктов: {len(rows)}")

    def _apply(self) -> None:
        self.btn_apply.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.status.setText("Создаю бэкап и применяю…" if self._backup_before else "Применяю…")

        def job():
            if self._backup_before:
                backup.create_backup("action", hives=["HKLM", "HKCU"])
            return self._apply_fn()

        self._worker = OperationWorker(job)
        self._worker.finished_ok.connect(self._done)
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, result: Optional[Dict]) -> None:
        if isinstance(result, dict):
            ok = sum(1 for v in result.values() if v)
            self.status.setText(f"Применено: {ok}/{len(result)} успешно.")
        else:
            self.status.setText("Готово.")
        self.btn_apply.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка: {msg}")
        self.btn_apply.setEnabled(True)
        self.btn_refresh.setEnabled(True)
