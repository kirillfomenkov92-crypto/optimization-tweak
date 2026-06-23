"""Модуль автозагрузки: перечисление и управление элементами автозапуска.

Источники: ключи Run/RunOnce (HKCU/HKLM) и папки автозагрузки. Включение/
отключение реализовано через перенос значения в подраздел AutorunsDisabled
(как делает Sysinternals Autoruns) — обратимо и безопасно.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List

from app.core.logger import get_logger, log_change
from app.core.optimizer import OptimizerModule
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

_RUN_KEYS = [
    ("HKCU", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
    ("HKLM", "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
]


class StartupModule(OptimizerModule):
    key = "startup"
    title = "Автозагрузка"

    def scan(self) -> List[Dict]:
        items: List[Dict] = []
        if IS_WINDOWS:
            items.extend(self._scan_run_keys())
        items.extend(self._scan_folders())
        return items

    def _scan_run_keys(self) -> List[Dict]:
        import winreg  # type: ignore

        found: List[Dict] = []
        hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
        for hive_name, path in _RUN_KEYS:
            try:
                with winreg.OpenKey(hives[hive_name], path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                        except OSError:
                            break
                        found.append({
                            "name": name, "command": value, "source": f"{hive_name}\\Run",
                            "type": "registry", "enabled": True,
                        })
                        i += 1
            except FileNotFoundError:
                continue
            except Exception as e:  # pragma: no cover
                _log.warning("Чтение Run %s\\%s: %s", hive_name, path, e)
        return found

    def _scan_folders(self) -> List[Dict]:
        found: List[Dict] = []
        candidates = []
        appdata = os.environ.get("APPDATA")
        programdata = os.environ.get("ProgramData")
        if appdata:
            candidates.append(Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup")
        if programdata:
            candidates.append(Path(programdata) / "Microsoft/Windows/Start Menu/Programs/Startup")
        for folder in candidates:
            try:
                if folder.is_dir():
                    for f in folder.iterdir():
                        if f.is_file():
                            found.append({
                                "name": f.name, "command": str(f),
                                "source": "Startup folder", "type": "file", "enabled": True,
                            })
            except Exception:
                continue
        return found

    def disable(self, hive: str, name: str) -> bool:
        """Отключить элемент Run, удалив его значение (с предварительным логом)."""
        if not IS_WINDOWS:
            return False
        path = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
        old, _ = reg.read_value(hive, path, name)
        if old is None:
            return False
        try:
            reg.delete_value(hive, path, name)
            log_change("startup", f"disable {hive}\\{name}", old=old, new=None)
            return True
        except Exception as e:  # pragma: no cover
            log_change("startup", f"disable {hive}\\{name}", status=f"ERROR:{e}")
            return False
