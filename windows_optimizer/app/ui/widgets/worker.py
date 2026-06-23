"""Фоновый воркер для длительных операций (чтобы GUI не зависал).

Любую функцию можно выполнить в отдельном потоке QThread и получить
результат через сигнал. Применяется для сканирования и применения твиков.
"""
from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QThread, pyqtSignal


class OperationWorker(QThread):
    """Выполняет ``fn(*args, **kwargs)`` в отдельном потоке."""

    finished_ok = pyqtSignal(object)   # результат функции
    failed = pyqtSignal(str)           # текст ошибки

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # noqa: D401
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished_ok.emit(result)
        except Exception as e:  # pragma: no cover - зависит от среды
            self.failed.emit(str(e))
