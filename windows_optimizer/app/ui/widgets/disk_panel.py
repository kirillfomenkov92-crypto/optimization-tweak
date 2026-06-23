"""Интерактивная панель очистки диска: категории с размером и удалением."""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.modules.disk import DiskModule
from app.ui.widgets.worker import OperationWorker


class DiskPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.module = DiskModule()
        self._worker = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("Очистка диска")
        head.setObjectName("Title")
        root.addWidget(head)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["✓", "Категория", "Размер, МБ", "Путь"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Пересчитать размеры")
        self.btn_clean = QPushButton("Очистить выбранное")
        self.btn_clean.setObjectName("Primary")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_clean.clicked.connect(self._clean)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_clean)
        root.addLayout(btns)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)

    def refresh(self) -> None:
        rows: List[Dict] = self.module.scan()
        self.table.setRowCount(len(rows))
        total = 0.0
        for i, r in enumerate(rows):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, r["label"])
            self.table.setItem(i, 0, chk)
            label = r["label"] + ("  ⚠" if r["warn"] else "")
            self.table.setItem(i, 1, QTableWidgetItem(label))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["size_mb"])))
            self.table.setItem(i, 3, QTableWidgetItem(r["path"]))
            total += r["size_mb"]
        self.status.setText(f"Всего найдено: {round(total, 1)} МБ. ⚠ — удалять осторожно.")

    def _selected_labels(self) -> List[str]:
        out: List[str] = []
        for i in range(self.table.rowCount()):
            it = self.table.item(i, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def _clean(self) -> None:
        labels = self._selected_labels()
        if not labels:
            self.status.setText("Ничего не выбрано.")
            return
        self.btn_clean.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.status.setText("Очищаю…")
        self._worker = OperationWorker(self.module.clean, labels)
        self._worker.finished_ok.connect(self._done)
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, freed: Dict[str, int]) -> None:
        total_mb = round(sum(freed.values()) / (1024 * 1024), 1)
        self.status.setText(f"Освобождено: {total_mb} МБ.")
        self.btn_clean.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка: {msg}")
        self.btn_clean.setEnabled(True)
        self.btn_refresh.setEnabled(True)
