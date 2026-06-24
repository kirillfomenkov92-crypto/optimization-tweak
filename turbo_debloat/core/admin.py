"""Проверка и запрос прав администратора для TurboDebloat."""
from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"


def is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin(extra_args=None) -> bool:
    """Перезапустить процесс с повышением прав (UAC). True — перезапуск начат."""
    if not IS_WINDOWS or is_admin():
        return False
    try:
        import ctypes

        args = list(sys.argv[1:]) + list(extra_args or [])
        params = " ".join(f'"{a}"' for a in args)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        return int(rc) > 32
    except Exception:
        return False
