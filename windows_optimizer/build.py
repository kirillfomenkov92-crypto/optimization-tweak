"""Сборка .exe через PyInstaller.

Запуск (на Windows):  python build.py
Результат:           dist/WindowsOptimizerPro.exe
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "resources" / "icons" / "app.ico"


def build() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except Exception as e:
        print(f"PyInstaller не установлен: {e}")
        return 2

    sep = ";" if sys.platform == "win32" else ":"
    args = [
        str(ROOT / "main.py"),
        "--name", "WindowsOptimizerPro",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--add-data={ROOT / 'data'}{sep}data",
        f"--add-data={ROOT / 'resources'}{sep}resources",
        f"--add-data={ROOT / 'app' / 'ui' / 'styles'}{sep}app/ui/styles",
        # playbook'и встроенного деблоата (JSON-данные, нужны в .exe).
        f"--add-data={ROOT / 'app' / 'debloat' / 'playbooks'}{sep}app/debloat/playbooks",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "wmi",
    ]
    if ICON.exists():
        args += ["--icon", str(ICON)]
    # requireAdmin-манифест: приложение само запрашивает UAC.
    if sys.platform == "win32":
        args += ["--uac-admin"]

    print("PyInstaller args:\n  " + "\n  ".join(args))
    pyi.run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
