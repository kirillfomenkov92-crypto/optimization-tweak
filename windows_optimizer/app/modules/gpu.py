"""Модуль GPU: определение видеокарт, HAGS, GPU-приоритет, dxdiag."""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import log_change
from app.core.optimizer import OptimizerModule
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"

_GRAPHICS_DRIVERS = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"


class GpuModule(OptimizerModule):
    key = "gpu"
    title = "GPU"

    def detect(self) -> List[str]:
        """Список видеокарт через WMI."""
        if not IS_WINDOWS:
            return []
        try:
            import wmi  # type: ignore

            return [g.Name for g in wmi.WMI().Win32_VideoController() if g.Name]
        except Exception:
            return []

    def hags_enabled(self) -> Dict:
        """Состояние Hardware-Accelerated GPU Scheduling (HwSchMode)."""
        if not IS_WINDOWS:
            return {"supported": False, "value": None}
        try:
            cur, _ = reg.read_value("HKLM", _GRAPHICS_DRIVERS, "HwSchMode")
            return {"supported": True, "value": cur, "enabled": cur == 2}
        except Exception:
            return {"supported": False, "value": None}

    def set_hags(self, enabled: bool) -> bool:
        """Включить/выключить HAGS (2=вкл, 1=выкл). Требует перезагрузки."""
        if not IS_WINDOWS:
            return False
        try:
            old, _ = reg.read_value("HKLM", _GRAPHICS_DRIVERS, "HwSchMode")
            reg.write_value("HKLM", _GRAPHICS_DRIVERS, "HwSchMode", 2 if enabled else 1, "REG_DWORD")
            log_change("gpu", "HwSchMode", old=old, new=2 if enabled else 1)
            return True
        except Exception as e:  # pragma: no cover
            log_change("gpu", "HwSchMode", status=f"ERROR:{e}")
            return False

    def run_dxdiag(self, out_file: str) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            subprocess.run(["dxdiag", "/t", out_file], capture_output=True, text=True)
            return True
        except Exception:
            return False

    def scan(self) -> List[Dict]:
        rows: List[Dict] = []
        gpus = self.detect()
        if gpus:
            for g in gpus:
                rows.append({"item": "Видеокарта", "value": g})
        else:
            rows.append({"item": "Видеокарта", "value": "(определяется на Windows)"})
        hags = self.hags_enabled()
        rows.append({"item": "HAGS (HwSchMode)", "value": str(hags.get("value"))})
        return rows
