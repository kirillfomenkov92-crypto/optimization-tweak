"""Модуль питания: планы электропитания и связанные настройки (powercfg)."""
from __future__ import annotations

import re
import subprocess
import sys
from typing import Dict, List, Optional

from app.core.logger import log_change, get_logger
from app.core.optimizer import OptimizerModule

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
_GUID_RE = re.compile(r"([0-9a-fA-F-]{36})")


def _run(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


class PowerModule(OptimizerModule):
    key = "power"
    title = "Питание"

    def list_plans(self) -> List[Dict]:
        """Список планов питания: [{guid, name, active}]."""
        if not IS_WINDOWS:
            return []
        plans: List[Dict] = []
        try:
            out = _run(["powercfg", "/list"]).stdout
            active = self.active_plan()
            for line in out.splitlines():
                m = _GUID_RE.search(line)
                if not m:
                    continue
                guid = m.group(1)
                name = ""
                nm = re.search(r"\(([^)]*)\)", line)
                if nm:
                    name = nm.group(1)
                plans.append({"guid": guid, "name": name, "active": guid == active})
        except Exception as e:
            _log.debug("powercfg /list не удался: %s", e)
        return plans

    def active_plan(self) -> Optional[str]:
        if not IS_WINDOWS:
            return None
        try:
            out = _run(["powercfg", "/getactivescheme"]).stdout
            m = _GUID_RE.search(out)
            return m.group(1) if m else None
        except Exception:
            return None

    def set_plan(self, guid: str) -> bool:
        if not IS_WINDOWS:
            return False
        old = self.active_plan()
        try:
            cp = _run(["powercfg", "/setactive", guid])
            ok = cp.returncode == 0
            log_change("power", f"set plan {guid}", old=old, new=guid,
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("power", f"set plan {guid}", status=f"ERROR:{e}")
            return False

    def enable_high_performance(self) -> bool:
        return self.set_plan(HIGH_PERF_GUID)

    def set_hibernation(self, enabled: bool) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            cp = _run(["powercfg", "/hibernate", "on" if enabled else "off"])
            ok = cp.returncode == 0
            log_change("power", f"hibernate {'on' if enabled else 'off'}",
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("power", "hibernate", status=f"ERROR:{e}")
            return False

    def scan(self) -> List[Dict]:
        plans = self.list_plans()
        rows = [{"name": p["name"] or p["guid"], "guid": p["guid"],
                 "active": p["active"]} for p in plans]
        if not rows and not IS_WINDOWS:
            rows.append({"name": "(планы доступны на Windows)", "guid": "", "active": False})
        return rows
