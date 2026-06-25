"""Модуль очистки диска: подсчёт размеров и удаление временных файлов/кэшей.

Удаляются только заведомо безопасные временные данные. Перед удалением
всегда можно посмотреть размер. Опасные категории помечены warn=True.
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logger import get_logger, log_change
from app.core.optimizer import OptimizerModule

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()


@dataclass
class CleanLocation:
    label: str
    path: Optional[Path]
    warn: bool = False


def _env_path(var: str, *parts: str) -> Optional[Path]:
    base = os.environ.get(var)
    if not base:
        return None
    return Path(base, *parts)


def _locations() -> List[CleanLocation]:
    locs: List[CleanLocation] = [
        CleanLocation("Временные файлы пользователя", _env_path("TEMP")),
        CleanLocation("Temp в LocalAppData", _env_path("LOCALAPPDATA", "Temp")),
        CleanLocation("Системный Temp", Path(r"C:\Windows\Temp") if IS_WINDOWS else None),
        CleanLocation("Кэш Chrome", _env_path("LOCALAPPDATA", "Google", "Chrome", "User Data", "Default", "Cache")),
        CleanLocation("Кэш Edge", _env_path("LOCALAPPDATA", "Microsoft", "Edge", "User Data", "Default", "Cache")),
        CleanLocation("Эскизы (thumbnail cache)", _env_path("LOCALAPPDATA", "Microsoft", "Windows", "Explorer")),
        CleanLocation("Отчёты об ошибках (WER)", _env_path("LOCALAPPDATA", "Microsoft", "Windows", "WER")),
        CleanLocation("Crash Dumps", _env_path("LOCALAPPDATA", "CrashDumps")),
        CleanLocation("Кэш обновлений Windows", Path(r"C:\Windows\SoftwareDistribution\Download") if IS_WINDOWS else None, warn=True),
        CleanLocation("Prefetch", Path(r"C:\Windows\Prefetch") if IS_WINDOWS else None, warn=True),
    ]
    return [l for l in locs if l.path is not None]


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except Exception:
                    continue
    except Exception as e:
        _log.debug("Не удалось посчитать размер %s: %s", path, e)
    return total


class DiskModule(OptimizerModule):
    key = "disk"
    title = "Очистка диска"

    def scan(self) -> List[Dict]:
        result: List[Dict] = []
        for loc in _locations():
            exists = loc.path.is_dir()
            size = _dir_size(loc.path) if exists else 0
            result.append({
                "label": loc.label,
                "path": str(loc.path),
                "exists": exists,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 1),
                "warn": loc.warn,
            })
        return result

    def clean(self, labels: List[str]) -> Dict[str, int]:
        """Очистить выбранные категории. Возвращает {label: освобождено_байт}."""
        freed: Dict[str, int] = {}
        by_label = {l.label: l for l in _locations()}
        for label in labels:
            loc = by_label.get(label)
            if not loc or not loc.path.is_dir():
                continue
            before = _dir_size(loc.path)
            removed = self._empty_dir(loc.path)
            freed[label] = removed
            log_change("disk", f"clean {label}", old=before, new=before - removed)
        return freed

    @staticmethod
    def _empty_dir(path: Path) -> int:
        """Удалить содержимое каталога (не сам каталог). Вернуть освобождённые байты."""
        freed = 0
        try:
            for entry in path.iterdir():
                try:
                    if entry.is_file() or entry.is_symlink():
                        sz = entry.stat().st_size
                        entry.unlink(missing_ok=True)
                        freed += sz
                    elif entry.is_dir():
                        sz = _dir_size(entry)
                        shutil.rmtree(entry, ignore_errors=True)
                        freed += sz
                except Exception:
                    # Занятые/защищённые файлы пропускаем — graceful degradation.
                    continue
        except Exception as e:  # pragma: no cover
            _log.warning("Очистка %s: %s", path, e)
        return freed
