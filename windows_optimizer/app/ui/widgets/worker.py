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


class StepWorker(QThread):
    """Выполняет последовательность шагов [(подпись, функция)], сообщая прогресс."""

    step = pyqtSignal(str, int)        # подпись текущего шага, процент (0..100)
    step_done = pyqtSignal(str)        # подпись завершённого шага
    finished_ok = pyqtSignal(dict)     # сводка результатов
    failed = pyqtSignal(str)

    def __init__(self, steps, stop_on_error: bool = False) -> None:
        super().__init__()
        self._steps = list(steps)
        self._stop_on_error = stop_on_error

    def run(self) -> None:
        results = {}
        n = max(1, len(self._steps))
        try:
            for i, (label, fn) in enumerate(self._steps):
                self.step.emit(label, int(i / n * 100))
                try:
                    results[label] = fn()
                except Exception as e:  # pragma: no cover
                    results[label] = e
                    # Критический сбой (например, не удалось сделать бэкап) —
                    # прерываем выполнение, чтобы не менять систему без отката.
                    if self._stop_on_error:
                        self.failed.emit(str(e))
                        return
                self.step_done.emit(label)
            self.step.emit("Готово!", 100)
            self.finished_ok.emit(results)
        except Exception as e:  # pragma: no cover
            self.failed.emit(str(e))
