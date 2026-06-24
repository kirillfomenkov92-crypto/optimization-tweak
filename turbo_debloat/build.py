"""Сборка TurboDebloat.exe через PyInstaller (запускать на Windows)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def build() -> int:
    try:
        import PyInstaller.__main__ as pyi
    except Exception as e:
        print(f"PyInstaller не установлен: {e}")
        return 2
    sep = ";" if sys.platform == "win32" else ":"
    args = [
        str(ROOT / "main.py"),
        "--name", "TurboDebloat",
        "--onefile", "--windowed", "--noconfirm", "--clean",
        f"--add-data={ROOT / 'playbooks'}{sep}turbo_debloat/playbooks",
        "--hidden-import", "wmi", "--hidden-import", "win32com.client",
    ]
    if sys.platform == "win32":
        args += ["--uac-admin"]
    pyi.run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
