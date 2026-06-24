"""Бэкап перед применением playbook: реестр, службы, hosts, манифест."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

IS_WINDOWS = sys.platform == "win32"

BACKUP_ROOT = Path(r"C:\TurboDebloat") if IS_WINDOWS else (Path(os.environ.get("TEMP", "/tmp")) / "TurboDebloat")


def _hosts_path() -> Path:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return Path(root) / "System32" / "drivers" / "etc" / "hosts"


def create_backup(services: Optional[List[str]] = None) -> Path:
    """Создать папку бэкапа с реестром/службами/hosts и вернуть её путь."""
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder = BACKUP_ROOT / f"backup_{ts}"
    (folder / "registry").mkdir(parents=True, exist_ok=True)

    # Реестр
    reg_files = []
    if IS_WINDOWS:
        for hive in ("HKLM", "HKCU"):
            out = folder / "registry" / f"{hive}.reg"
            try:
                cp = subprocess.run(["reg", "export", hive, str(out), "/y"],
                                    capture_output=True, text=True)
                if cp.returncode == 0:
                    reg_files.append(out.name)
            except Exception:
                pass

    # Состояние служб (тип запуска)
    services_state: Dict[str, str] = {}
    _KEYWORDS = ("BOOT_START", "SYSTEM_START", "AUTO_START", "DEMAND_START", "DISABLED")
    if IS_WINDOWS and services:
        for name in services:
            try:
                cp = subprocess.run(["sc", "qc", name], capture_output=True, text=True, timeout=30)
                for line in cp.stdout.splitlines():
                    if "START_TYPE" in line:
                        # Строка вида "START_TYPE : 2  AUTO_START" — берём ключевое слово,
                        # а не "2  AUTO_START", иначе откат не распознает исходный тип.
                        tail = line.split(":", 1)[-1]
                        kw = next((t for t in tail.split() if t in _KEYWORDS), "")
                        if kw:
                            services_state[name] = kw
                        break
            except Exception:
                continue
    (folder / "services_state.json").write_text(
        json.dumps(services_state, ensure_ascii=False, indent=2), encoding="utf-8")

    # hosts
    try:
        hp = _hosts_path()
        if hp.exists():
            shutil.copy2(hp, folder / "hosts.bak")
    except Exception:
        pass

    manifest = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "platform": sys.platform,
        "registry_files": reg_files,
        "services_backed_up": list(services_state.keys()),
    }
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # Лог применённых шагов (заполняется движком).
    (folder / "applied_steps.json").write_text("[]", encoding="utf-8")
    return folder


def list_backups() -> List[Path]:
    if not BACKUP_ROOT.exists():
        return []
    return sorted((p for p in BACKUP_ROOT.iterdir()
                   if p.is_dir() and (p / "manifest.json").exists()), reverse=True)
