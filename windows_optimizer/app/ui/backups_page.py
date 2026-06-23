"""Страница бэкапов: список, создание точки восстановления и бэкапа реестра."""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget,
)

from app.core import backup
from app.ui.widgets.worker import OperationWorker


class BackupsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("Резервные копии")
        head.setObjectName("Title")
        root.addWidget(head)

        info = QLabel("Перед изменениями приложение делает бэкап. Здесь можно создать их вручную.")
        info.setObjectName("Subtitle")
        info.setWordWrap(True)
        root.addWidget(info)

        btns = QHBoxLayout()
        self.btn_rp = QPushButton("Создать точку восстановления")
        self.btn_rp.setObjectName("Primary")
        self.btn_reg = QPushButton("Бэкап реестра сейчас")
        self.btn_refresh = QPushButton("Обновить список")
        self.btn_rp.clicked.connect(self._make_rp)
        self.btn_reg.clicked.connect(self._make_reg)
        self.btn_refresh.clicked.connect(self.refresh)
        btns.addWidget(self.btn_rp)
        btns.addWidget(self.btn_reg)
        btns.addStretch(1)
        btns.addWidget(self.btn_refresh)
        root.addLayout(btns)

        self.list = QListWidget()
        root.addWidget(self.list, 1)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        root.addWidget(self.status)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        items: List[Dict] = backup.list_backups()
        for it in items:
            self.list.addItem(f"{it.get('timestamp','?')} — {it.get('name','')} "
                              f"(реестр: {len(it.get('registry_files', []))} файлов)")
        self.status.setText(f"Бэкапов: {len(items)}")

    def _busy(self, busy: bool) -> None:
        for b in (self.btn_rp, self.btn_reg, self.btn_refresh):
            b.setEnabled(not busy)

    def _make_rp(self) -> None:
        self._busy(True)
        self.status.setText("Создаю точку восстановления…")
        self._worker = OperationWorker(backup.create_restore_point, "WindowsOptimizer (вручную)")
        self._worker.finished_ok.connect(lambda ok: self._after(ok, "Точка восстановления"))
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _make_reg(self) -> None:
        self._busy(True)
        self.status.setText("Делаю бэкап реестра…")
        self._worker = OperationWorker(backup.create_backup, "manual_registry", ["HKLM", "HKCU"])
        self._worker.finished_ok.connect(lambda p: self._after(bool(p), "Бэкап реестра"))
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _after(self, ok, what: str) -> None:
        self.status.setText(f"{what}: {'готово' if ok else 'не удалось (нужны права/Windows)'}.")
        self._busy(False)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка: {msg}")
        self._busy(False)
