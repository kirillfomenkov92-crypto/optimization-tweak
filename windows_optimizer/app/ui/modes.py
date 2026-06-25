"""Режимы интерфейса: Простой (по умолчанию) и Расширенный.

В простом режиме показываются только понятные крупные разделы и безопасные
улучшения; технические детали скрыты. Расширенный — полный доступ.
Состояние сохраняется в QSettings и применяется без перезапуска.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, List

from app.core.logger import get_logger

_log = get_logger()


class AppMode(Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"


class ModeManager:
    def __init__(self) -> None:
        # QSettings создаётся лениво, чтобы не требовать QApplication при импорте.
        self._settings = None
        self._mode = None
        self._callbacks: List[Callable[[AppMode], None]] = []

    def _ensure(self) -> None:
        if self._mode is not None:
            return
        try:
            from PyQt6.QtCore import QSettings

            self._settings = QSettings("WindowsOptimizer", "App")
            value = self._settings.value("ui_mode", AppMode.SIMPLE.value)
            self._mode = AppMode(value if value in (m.value for m in AppMode) else "simple")
        except Exception as e:
            _log.debug("Не удалось прочитать режим UI, остаюсь на Простом: %s", e)
            self._mode = AppMode.SIMPLE

    @property
    def mode(self) -> AppMode:
        self._ensure()
        return self._mode

    def set_mode(self, mode: AppMode) -> None:
        self._ensure()
        self._mode = mode
        try:
            if self._settings is not None:
                self._settings.setValue("ui_mode", mode.value)
        except Exception as e:
            _log.debug("Не удалось сохранить режим UI: %s", e)
        for cb in list(self._callbacks):
            try:
                cb(mode)
            except Exception as e:
                _log.debug("Колбэк смены режима упал: %s", e)

    def on_change(self, callback: Callable[[AppMode], None]) -> None:
        self._callbacks.append(callback)

    def is_simple(self) -> bool:
        return self.mode == AppMode.SIMPLE


_manager = None


def mode_manager() -> ModeManager:
    """Глобальный (ленивый) синглтон менеджера режимов."""
    global _manager
    if _manager is None:
        _manager = ModeManager()
    return _manager
