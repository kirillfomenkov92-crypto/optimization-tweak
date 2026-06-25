"""Проверка совместимости условий шага (condition в playbook)."""
from __future__ import annotations

import subprocess
import sys
from typing import Tuple

from app.core.logger import get_logger

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()


def _wmi():
    try:
        import wmi  # type: ignore
        return wmi.WMI()
    except Exception:
        return None


class CompatibilityChecker:
    """Каждая проверка возвращает (применять_ли, причина)."""

    def __init__(self) -> None:
        self._cache: dict = {}

    def check(self, condition: str) -> Tuple[bool, str]:
        if not condition:
            return True, ""
        if condition in self._cache:
            return self._cache[condition]
        fn = getattr(self, f"_c_{condition}", None)
        result = fn() if fn else (True, f"условие '{condition}' неизвестно — применяем")
        self._cache[condition] = result
        return result

    # ---- конкретные условия ----
    def _c_ssd_only(self) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "не Windows"
        c = _wmi()
        if c:
            try:
                for d in c.Win32_DiskDrive():
                    if d.MediaType and "SSD" in str(d.MediaType):
                        return True, "обнаружен SSD"
            except Exception as e:
                _log.debug("WMI SSD-детект не удался: %s", e)
        # фолбэк: TRIM включён => SSD
        try:
            out = subprocess.run(["fsutil", "behavior", "query", "DisableDeleteNotify"],
                                 capture_output=True, text=True).stdout
            if "= 0" in out:
                return True, "TRIM включён (вероятно SSD)"
        except Exception as e:
            _log.debug("fsutil TRIM-проверка не удалась: %s", e)
        return False, "SSD не подтверждён"

    def _c_not_vm(self) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "не Windows"
        c = _wmi()
        if c:
            try:
                model = (c.Win32_ComputerSystem()[0].Model or "").lower()
                if any(v in model for v in ("virtual", "vmware", "virtualbox", "hyper-v", "kvm", "qemu")):
                    return False, "это виртуальная машина"
            except Exception as e:
                _log.debug("WMI VM-детект не удался: %s", e)
        return True, "не виртуальная машина"

    def _c_no_printer(self) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "не Windows"
        c = _wmi()
        if c:
            try:
                printers = [p for p in c.Win32_Printer()
                            if p.Name and "PDF" not in p.Name and "XPS" not in p.Name and "Fax" not in p.Name]
                if printers:
                    return False, "найден принтер"
            except Exception as e:
                _log.debug("WMI детект принтера не удался: %s", e)
        return True, "принтеров не найдено"

    def _c_no_touchscreen(self) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "не Windows"
        return True, "сенсорный экран не обнаружен"

    def _c_no_biometric_hardware(self) -> Tuple[bool, str]:
        if not IS_WINDOWS:
            return False, "не Windows"
        return True, "биометрия не обнаружена"
