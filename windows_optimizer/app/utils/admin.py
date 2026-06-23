"""Проверка и запрос прав администратора.

Все изменяющие систему операции требуют прав администратора. Модуль даёт
безопасные обёртки, которые не падают на не-Windows (для импорта/тестов).
"""
from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"


def is_admin() -> bool:
    """True, если процесс запущен с правами администратора."""
    if not IS_WINDOWS:
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> bool:
    """Перезапустить текущий процесс с повышением прав (UAC).

    Возвращает True, если перезапуск инициирован (тогда вызывающий код должен
    завершиться), иначе False.
    """
    if not IS_WINDOWS or is_admin():
        return False
    try:
        import ctypes

        params = " ".join(f'"{a}"' for a in sys.argv)
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        # ShellExecuteW возвращает значение > 32 при успехе.
        return int(rc) > 32
    except Exception:
        return False
