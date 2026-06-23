"""Система резервного копирования — фундамент безопасности.

Перед КАЖДЫМ изменением системы создаётся бэкап соответствующего
компонента. Поддержано: экспорт веток реестра (reg export), точка
восстановления (через PowerShell Checkpoint-Computer), снимок состояния
служб/автозагрузки в JSON, а также метаданные бэкапа.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logger import get_logger

IS_WINDOWS = sys.platform == "win32"
_BACKUP_DIR = Path(__file__).resolve().parents[2] / "backups"
_log = get_logger()


def _ensure_dir() -> Path:
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return _BACKUP_DIR


def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, shell=False)


def export_registry_hive(hive: str, out_path: Path) -> bool:
    """Экспортировать ветку реестра в .reg (reg export)."""
    if not IS_WINDOWS:
        _log.warning("export_registry_hive: только Windows")
        return False
    try:
        cp = _run(["reg", "export", hive, str(out_path), "/y"])
        ok = cp.returncode == 0
        _log.info("Экспорт реестра %s -> %s: %s", hive, out_path.name, "OK" if ok else cp.stderr)
        return ok
    except Exception as e:
        _log.error("Ошибка экспорта реестра %s: %s", hive, e)
        return False


def create_restore_point(description: str = "WindowsOptimizer") -> bool:
    """Создать точку восстановления системы через PowerShell."""
    if not IS_WINDOWS:
        _log.warning("create_restore_point: только Windows")
        return False
    try:
        ps = (
            "Enable-ComputerRestore -Drive $env:SystemDrive; "
            f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS'"
        )
        cp = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
        ok = cp.returncode == 0
        _log.info("Точка восстановления: %s", "создана" if ok else cp.stderr.strip())
        return ok
    except Exception as e:
        _log.error("Ошибка создания точки восстановления: %s", e)
        return False


def create_backup(name: str, hives: Optional[List[str]] = None,
                  services_state: Optional[Dict] = None,
                  startup_state: Optional[Dict] = None,
                  applied_tweaks: Optional[List[str]] = None) -> Optional[Path]:
    """Создать комплексный бэкап и вернуть путь к его папке."""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    folder = _ensure_dir() / f"{ts}_{name}"
    folder.mkdir(parents=True, exist_ok=True)

    reg_files: List[str] = []
    for hive in (hives or []):
        out = folder / f"{hive}.reg"
        if export_registry_hive(hive, out):
            reg_files.append(out.name)

    meta = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "version": "1.0",
        "name": name,
        "registry_files": reg_files,
        "services_state": services_state or {},
        "startup_state": startup_state or {},
        "applied_tweaks": applied_tweaks or [],
    }
    (folder / "manifest.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log.info("Бэкап создан: %s", folder)
    return folder


def list_backups() -> List[Dict]:
    """Список бэкапов (по убыванию даты)."""
    _ensure_dir()
    items: List[Dict] = []
    for folder in sorted(_BACKUP_DIR.iterdir(), reverse=True):
        manifest = folder / "manifest.json"
        if folder.is_dir() and manifest.exists():
            try:
                items.append({"path": str(folder), **json.loads(manifest.read_text(encoding="utf-8"))})
            except Exception:
                continue
    return items
