"""Модуль CPU: приоритет переднего плана, парковка ядер, инфо о процессоре."""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import log_change, get_logger
from app.core.optimizer import OptimizerModule
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore

_PRIO_CONTROL = r"SYSTEM\CurrentControlSet\Control\PriorityControl"

# Win32PrioritySeparation: 0x2A=макс. приоритет переднего плана (короткие кванты),
# 0x26=длинные кванты (для видеомонтажа), 0x18=равный (серверный режим).
PRIORITY_PRESETS = {
    "Передний план (десктоп)": 0x2A,
    "Длинные кванты (монтаж)": 0x26,
    "Равный (сервер)": 0x18,
}

# Обратная карта для человекочитаемого отображения текущего значения.
_PRIORITY_LABELS = {v: k for k, v in PRIORITY_PRESETS.items()}


def _priority_label(value) -> str:
    """Подпись текущего режима приоритета вместо сырого hex."""
    if value is None:
        return "не задан"
    label = _PRIORITY_LABELS.get(value)
    return label if label else f"другое значение ({hex(value)})"


class CpuModule(OptimizerModule):
    key = "cpu"
    title = "CPU"

    def info(self) -> Dict:
        d = {"cores": 0, "threads": 0, "freq_mhz": 0}
        if psutil is not None:
            try:
                d["cores"] = psutil.cpu_count(logical=False) or 0
                d["threads"] = psutil.cpu_count(logical=True) or 0
                f = psutil.cpu_freq()
                d["freq_mhz"] = int(f.max or f.current) if f else 0
            except Exception as e:
                _log.debug("psutil: не удалось получить данные CPU: %s", e)
        return d

    def set_priority_separation(self, value: int) -> bool:
        if not IS_WINDOWS:
            return False
        try:
            old, _ = reg.read_value("HKLM", _PRIO_CONTROL, "Win32PrioritySeparation")
            reg.write_value("HKLM", _PRIO_CONTROL, "Win32PrioritySeparation", value, "REG_DWORD")
            log_change("cpu", "Win32PrioritySeparation", old=old, new=value)
            return True
        except Exception as e:  # pragma: no cover
            log_change("cpu", "Win32PrioritySeparation", status=f"ERROR:{e}")
            return False

    def disable_core_parking(self) -> bool:
        """Минимум 100% состояния процессора в активном плане (через powercfg)."""
        if not IS_WINDOWS:
            return False
        try:
            # PROCTHROTTLEMIN = 100% для текущей схемы (AC).
            sub = "54533251-82be-4824-96c1-47b60b740d00"  # processor power management
            setting = "893dee8e-2bef-41e0-89c6-b55d0929964c"  # min processor state
            subprocess.run(["powercfg", "/setacvalueindex", "SCHEME_CURRENT", sub, setting, "100"],
                           capture_output=True, text=True)
            subprocess.run(["powercfg", "/setactive", "SCHEME_CURRENT"], capture_output=True, text=True)
            log_change("cpu", "min processor state", new="100%")
            return True
        except Exception as e:  # pragma: no cover
            log_change("cpu", "core parking", status=f"ERROR:{e}")
            return False

    def scan(self) -> List[Dict]:
        info = self.info()
        rows = [
            {"item": "Ядра / потоки", "value": f"{info['cores']} / {info['threads']}"},
            {"item": "Частота", "value": f"{info['freq_mhz']} МГц"},
        ]
        if IS_WINDOWS:
            try:
                cur, _ = reg.read_value("HKLM", _PRIO_CONTROL, "Win32PrioritySeparation")
                rows.append({"item": "Приоритет процессора", "value": _priority_label(cur)})
            except Exception as e:
                _log.debug("Не удалось прочитать Win32PrioritySeparation: %s", e)
        return rows
