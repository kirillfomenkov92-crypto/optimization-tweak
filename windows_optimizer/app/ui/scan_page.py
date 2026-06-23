"""Страница полного сканирования: прогон scan() по всем модулям в фоне."""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app.ui.widgets.worker import OperationWorker


def _collect_modules():
    """Импорт модулей здесь, чтобы страница импортировалась без побочных эффектов."""
    from app.modules.registry import RegistryModule
    from app.modules.startup import StartupModule
    from app.modules.services import ServicesModule
    from app.modules.disk import DiskModule
    from app.modules.network import NetworkModule
    from app.modules.power import PowerModule
    from app.modules.memory import MemoryModule
    from app.modules.gaming import GamingModule
    from app.modules.gpu import GpuModule
    from app.modules.cpu import CpuModule
    from app.modules.security import SecurityModule
    from app.modules.privacy import PrivacyModule

    return [
        RegistryModule(), StartupModule(), ServicesModule(), DiskModule(),
        NetworkModule(), PowerModule(), MemoryModule(), GamingModule(),
        GpuModule(), CpuModule(), SecurityModule(), PrivacyModule(),
    ]


def _run_scan() -> Dict[str, List[Dict]]:
    report: Dict[str, List[Dict]] = {}
    for mod in _collect_modules():
        try:
            report[mod.title] = mod.scan()
        except Exception as e:  # pragma: no cover
            report[mod.title] = [{"error": str(e)}]
    return report


def _row_text(row: Dict) -> str:
    if "error" in row:
        return f"ошибка: {row['error']}"
    if "name" in row:
        extra = row.get("status") or row.get("description") or ""
        return f"{row['name']}  {extra}".strip()
    if "label" in row:
        return f"{row['label']}: {row.get('size_mb', 0)} МБ"
    if "item" in row:
        return f"{row['item']}: {row.get('value','')}"
    return str(row)


class ScanPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker = None
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        head = QLabel("Полное сканирование системы")
        head.setObjectName("Title")
        root.addWidget(head)

        top = QHBoxLayout()
        self.btn = QPushButton("Запустить сканирование")
        self.btn.setObjectName("Primary")
        self.btn.clicked.connect(self._start)
        top.addWidget(self.btn)
        top.addStretch(1)
        self.status = QLabel("")
        self.status.setObjectName("Subtitle")
        top.addWidget(self.status)
        root.addLayout(top)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Компонент / находка"])
        root.addWidget(self.tree, 1)

    def _start(self) -> None:
        self.btn.setEnabled(False)
        self.status.setText("Сканирую все модули…")
        self.tree.clear()
        self._worker = OperationWorker(_run_scan)
        self._worker.finished_ok.connect(self._show)
        self._worker.failed.connect(self._error)
        self._worker.start()

    def _show(self, report: Dict[str, List[Dict]]) -> None:
        total = 0
        for module_title, rows in report.items():
            parent = QTreeWidgetItem([f"{module_title} ({len(rows)})"])
            for r in rows:
                QTreeWidgetItem(parent, [_row_text(r)])
                total += 1
            self.tree.addTopLevelItem(parent)
        self.tree.expandAll()
        self.status.setText(f"Готово: {total} находок в {len(report)} модулях.")
        self.btn.setEnabled(True)

    def _error(self, msg: str) -> None:
        self.status.setText(f"Ошибка сканирования: {msg}")
        self.btn.setEnabled(True)
