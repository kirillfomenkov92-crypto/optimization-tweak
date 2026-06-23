"""Панель улучшений: список строк-тумблеров (TweakRow) + применение в фоне.

Тумблеры отражают желаемое состояние. Кнопка «Применить изменения» сравнивает
их с текущим и включает/отключает только разницу — с предварительным
сохранением состояния системы (бэкап реестра). Простой режим показывает только
понятные безопасные улучшения; «Показать всё» открывает остальные.
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from app.core import backup
from app.ui.modes import mode_manager
from app.ui.widgets.tweak_row import TweakRow
from app.ui.widgets.worker import OperationWorker


class TweakPanel(QWidget):
    def __init__(self, provider, title: str) -> None:
        super().__init__()
        self.provider = provider
        self._rows: List[TweakRow] = []
        self._worker = None
        self._build(title)
        self.refresh()

    def _build(self, title: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        head = QLabel(title)
        head.setObjectName("Title")
        root.addWidget(head)

        self.show_all = QCheckBox("Показать всё (включая пункты для опытных)")
        self.show_all.stateChanged.connect(lambda _=0: self.refresh())
        root.addWidget(self.show_all)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(6)
        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll, 1)

        btns = QHBoxLayout()
        self.btn_refresh = QPushButton("Проверить состояние")
        self.btn_apply = QPushButton("Применить изменения")
        self.btn_apply.setObjectName("Primary")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_apply.clicked.connect(self._apply)
        btns.addWidget(self.btn_refresh)
        btns.addStretch(1)
        btns.addWidget(self.btn_apply)
        root.addLayout(btns)

        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

    def _visible(self) -> List[Dict]:
        rows = self.provider.scan()
        if mode_manager().is_simple() and not self.show_all.isChecked():
            rows = [r for r in rows
                    if r.get("simple_mode_visible", True) and r.get("risk_level", "safe") != "advanced"]
        return rows

    def refresh(self) -> None:
        # очистить
        for i in reversed(range(self.vbox.count())):
            w = self.vbox.itemAt(i).widget()
            if w:
                w.setParent(None)
        self._rows.clear()

        rows = self._visible()
        advanced = not mode_manager().is_simple()
        if not rows:
            empty = QLabel("✓\n\nВсё оптимизировано\nВ этом разделе больше нечего улучшать.")
            empty.setObjectName("Subtitle")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.vbox.addWidget(empty)
            self.status.setText("Здесь всё в порядке.")
            return

        for r in rows:
            row = TweakRow(r, advanced=advanced)
            self._rows.append(row)
            self.vbox.addWidget(row)
        self.vbox.addStretch(1)
        self.status.setText(f"Доступно улучшений: {len(rows)}. Переключите тумблеры и нажмите «Применить изменения».")

    def _set_busy(self, busy: bool) -> None:
        self.btn_refresh.setEnabled(not busy)
        self.btn_apply.setEnabled(not busy)

    def _apply(self) -> None:
        statuses = {r["id"]: r["status"] for r in self.provider.scan()}
        to_enable, to_disable = [], []
        for row in self._rows:
            desired = row.is_on()
            current_applied = statuses.get(row.tweak_id) == "applied"
            if desired and not current_applied:
                to_enable.append(row.tweak_id)
            elif not desired and current_applied:
                to_disable.append(row.tweak_id)

        if not to_enable and not to_disable:
            self.status.setText("Изменений нет — тумблеры совпадают с текущим состоянием.")
            return

        self._set_busy(True)
        self.status.setText("Сохраняю состояние системы и применяю изменения…")

        def job():
            backup.create_backup("tweaks", hives=["HKLM", "HKCU"],
                                 applied_tweaks=to_enable + to_disable)
            res = {}
            if to_enable:
                res.update(self.provider.apply_many(to_enable))
            if to_disable:
                res.update(self.provider.revert_many(to_disable))
            return res

        self._worker = OperationWorker(job)
        self._worker.finished_ok.connect(self._done)
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _done(self, result: Dict) -> None:
        ok = sum(1 for v in (result or {}).values() if v)
        total = len(result or {})
        self.status.setText(f"Готово: {ok} из {total}. Изменения можно отменить, вернув тумблеры и нажав «Применить».")
        self._set_busy(False)
        self.refresh()

    def _error(self, msg: str) -> None:
        self.status.setText(f"Не удалось: {msg}")
        self._set_busy(False)
