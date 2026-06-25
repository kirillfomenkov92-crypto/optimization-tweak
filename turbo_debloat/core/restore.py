"""Откат изменений из бэкапа TurboDebloat.

Восстанавливает реестр (.reg), типы запуска служб, hosts и выполняет
undo-команды (bcdedit/задачи/службы). Удалённые приложения не
восстанавливаются — об этом предупреждается до применения.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from turbo_debloat.core import backup as backup_mod
from turbo_debloat.core.logger import get_logger

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()


def restore(backup_path: Path, dry_run: bool = False) -> Dict:
    backup_path = Path(backup_path)
    actions: List[str] = []
    failed = 0

    # реестр
    reg_dir = backup_path / "registry"
    if reg_dir.is_dir():
        for reg_file in reg_dir.glob("*.reg"):
            actions.append(f"reg import {reg_file.name}")
            if not dry_run and IS_WINDOWS:
                try:
                    cp = subprocess.run(["reg", "import", str(reg_file)], capture_output=True, text=True)
                    if cp.returncode != 0:
                        failed += 1
                        _log.warning("Откат реестра %s не удался: %s", reg_file.name, cp.stderr.strip())
                except Exception as e:
                    failed += 1
                    _log.warning("Откат реестра %s упал: %s", reg_file.name, e)

    # службы
    svc_file = backup_path / "services_state.json"
    if svc_file.exists():
        try:
            state = json.loads(svc_file.read_text(encoding="utf-8"))
        except Exception as e:
            _log.error("Не удалось прочитать services_state.json: %s", e)
            state = {}
        for name, start in state.items():
            mode = {
                "AUTO_START": "auto", "BOOT_START": "auto", "SYSTEM_START": "auto",
                "DEMAND_START": "demand", "DISABLED": "disabled",
            }.get(str(start).strip().upper(), "auto")
            actions.append(f"sc config {name} start= {mode}")
            if not dry_run and IS_WINDOWS:
                try:
                    cp = subprocess.run(["sc", "config", name, f"start={mode}"], capture_output=True, text=True)
                    if cp.returncode != 0:
                        failed += 1
                        _log.warning("Откат службы %s не удался: %s", name, cp.stderr.strip())
                except Exception as e:
                    failed += 1
                    _log.warning("Откат службы %s упал: %s", name, e)

    # hosts
    hosts_bak = backup_path / "hosts.bak"
    if hosts_bak.exists():
        actions.append("restore hosts")
        if not dry_run and IS_WINDOWS:
            try:
                shutil.copy2(hosts_bak, backup_mod._hosts_path())
            except Exception as e:
                failed += 1
                _log.warning("Откат hosts не удался: %s", e)

    # undo-команды
    applied = backup_path / "applied_steps.json"
    if applied.exists():
        try:
            for item in json.loads(applied.read_text(encoding="utf-8")):
                for cmd in item.get("undo", []):
                    actions.append(cmd)
                    if not dry_run and IS_WINDOWS:
                        try:
                            cp = subprocess.run(cmd.split(), capture_output=True, text=True)
                            if cp.returncode != 0:
                                failed += 1
                                _log.warning("Undo-команда не удалась (%s): %s", cmd, cp.stderr.strip())
                        except Exception as e:
                            failed += 1
                            _log.warning("Undo-команда упала (%s): %s", cmd, e)
        except Exception as e:
            _log.error("Не удалось прочитать applied_steps.json: %s", e)

    if failed:
        _log.warning("Восстановление завершено с ошибками: неуспешных шагов %d", failed)
    return {"backup": str(backup_path), "dry_run": dry_run, "actions": actions,
            "count": len(actions), "failed": failed}
