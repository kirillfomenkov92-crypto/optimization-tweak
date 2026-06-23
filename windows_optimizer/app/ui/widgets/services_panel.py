"""Интерактивная панель служб: таблица + смена типа запуска (с защитой)."""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.modules.services import ServicesModule
from app.ui.widgets.worker import OperationWorker

_GROUP_LABEL = {"safe": "безопасно", "caution": "осторожно", "never": "не трогать", "other": "—"}


class ServicesPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.module = ServicesModule()
        self._worker = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("Службы Windows")
        head.setObjectName("Title")
        root.addWidget(head)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["✓", "Служба", "Группа", "Статус", "Тип запуска"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Обновить")
        self.mode = QComboBox()
        self.mode.addItems(["disabled", "manual", "auto"])
        self.btn_apply = QPushButton("Применить к выбранным")
        self.btn_apply.setObjectName("Primary")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_apply.clicked.connect(self._apply)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(QLabel("Тип запуска:"))
        btns.addWidget(self.mode)
        btns.addWidget(self.btn_apply)
        root.addLayout(btns)

        self.status = QLabel("Службы группы «не трогать» защищены и игнорируются.")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)

    def refresh(self) -> None:
        rows: List[Dict] = self.module.scan()
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            chk = QTableWidgetItem()
            protected = r["group"] == "never"
            flags = Qt.ItemFlag.ItemIsEnabled
            if not protected:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            chk.setFlags(flags)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, r["name"])
            self.table.setItem(i, 0, chk)
            self.table.setItem(i, 1, QTableWidgetItem(r["display_name"]))
            self.table.setItem(i, 2, QTableWidgetItem(_GROUP_LABEL.get(r["group"], r["group"])))
            self.table.setItem(i, 3, QTableWidgetItem(str(r["status"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(r["start_type"])))
        self.status.setText(f"Служб показано: {len(rows)} (критичные защищены).")

    def _selected(self) -> List[str]:
        out: List[str] = []
        for i in range(self.table.rowCount()):
            it = self.table.item(i, 0)
            if it and (it.flags() & Qt.ItemFlag.ItemIsUserCheckable) and it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def _apply(self) -> None:
        names = self._selected()
        if not names:
            self.status.setText("Ничего не выбрано.")
            return
        mode = self.mode.currentText()
        self.btn_apply.setEnabled(False)
        self.status.setText(f"Применяю '{mode}' к {len(names)} службам…")

        def job():
            return {n: self.module.set_start_type(n, mode) for n in names}

        self._worker = OperationWorker(job)
        self._worker.finished_ok.connect(self._done)
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, result: Dict[str, bool]) -> None:
        ok = sum(1 for v in result.values() if v)
        self.status.setText(f"Готово: {ok}/{len(result)} успешно.")
        self.btn_apply.setEnabled(True)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка: {msg}")
        self.btn_apply.setEnabled(True)
