"""Фоновое выполнение playbook для GUI (QThread)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from turbo_debloat.core.engine import PlaybookEngine


class RunWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, playbook: dict, selected_ids: Optional[set], dry_run: bool) -> None:
        super().__init__()
        self._playbook = playbook
        self._selected = selected_ids
        self._dry_run = dry_run

    def run(self) -> None:
        try:
            engine = PlaybookEngine(dry_run=self._dry_run)
            report = engine.run(
                self._playbook,
                selected_ids=self._selected,
                progress_cb=lambda p, label: self.progress.emit(p, label),
            )
            self.done.emit(report)
        except Exception as e:  # pragma: no cover
            self.failed.emit(str(e))
