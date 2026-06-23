"""Интерактивная панель твиков: таблица с чекбоксами + применение/откат/статус.

Работает с провайдером (например RegistryModule), у которого есть:
  - scan() -> список dict с ключами id, name, category, risk, status, description
  - apply_many(ids) -> dict[id, bool]
  - revert_many(ids) -> dict[id, bool]

Перед применением создаётся бэкап реестра — принцип «безопасность прежде всего».
Все операции выполняются в фоновом потоке.
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.core import backup
from app.ui.widgets.worker import OperationWorker

_RISK_COLOR = {"low": "#4ecca3", "medium": "#ffd460", "high": "#e94560"}


class TweakPanel(QWidget):
    def __init__(self, provider, title: str) -> None:
        super().__init__()
        self.provider = provider
        self._worker = None
        self._build(title)
        self.refresh()

    # ----- построение UI -----
    def _build(self, title: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        root.addWidget(head)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["✓", "Название", "Категория", "Риск", "Статус"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить статус")
        self.btn_apply = QPushButton("Применить выбранные")
        self.btn_apply.setObjectName("Primary")
        self.btn_revert = QPushButton("Откатить выбранные")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_apply.clicked.connect(self._apply_selected)
        self.btn_revert.clicked.connect(self._revert_selected)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_revert)
        btns.addWidget(self.btn_apply)
        root.addLayout(btns)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)

    # ----- данные -----
    def refresh(self) -> None:
        rows: List[Dict] = self.provider.scan()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, r.get("id"))
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(r.get("name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("category", "")))
            risk = QTableWidgetItem(r.get("risk", ""))
            color = _RISK_COLOR.get(r.get("risk", ""), None)
            if color:
                risk.setForeground(Qt.GlobalColor.white)
            self.table.setItem(i, 3, risk)
            self.table.setItem(i, 4, QTableWidgetItem(r.get("status", "")))
        self.status.setText(f"Загружено твиков: {len(rows)}")

    def _selected_ids(self) -> List[str]:
        ids: List[str] = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    # ----- операции (в фоне) -----
    def _set_busy(self, busy: bool) -> None:
        for b in (self.btn_refresh, self.btn_apply, self.btn_revert):
            b.setEnabled(not busy)

    def _apply_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            self.status.setText("Ничего не выбрано.")
            return
        self.status.setText("Создаю бэкап реестра и применяю…")
        self._set_busy(True)

        def job():
            backup.create_backup("tweaks", hives=["HKLM", "HKCU"], applied_tweaks=ids)
            return self.provider.apply_many(ids)

        self._run(job, "Применено")

    def _revert_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            self.status.setText("Ничего не выбрано.")
            return
        self._set_busy(True)
        self.status.setText("Откатываю выбранные…")
        self._run(lambda: self.provider.revert_many(ids), "Откачено")

    def _run(self, fn, verb: str) -> None:
        self._worker = OperationWorker(fn)
        self._worker.finished_ok.connect(lambda res: self._done(res, verb))
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, result: Dict, verb: str) -> None:
        ok = sum(1 for v in (result or {}).values() if v)
        total = len(result or {})
        self.status.setText(f"{verb}: {ok}/{total} успешно.")
        self._set_busy(False)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка: {msg}")
        self._set_busy(False)
