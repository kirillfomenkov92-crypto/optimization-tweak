"""Модуль памяти: pagefile, рекомендации, очистка рабочих наборов, кэш."""
from __future__ import annotations

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

_MEMMGMT = r"SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"


def pagefile_recommendation(ram_gb: float) -> str:
    if ram_gb < 4:
        return "1.5× RAM"
    if ram_gb < 8:
        return "1× RAM"
    if ram_gb <= 16:
        return "4–8 ГБ (фиксированный)"
    return "2–4 ГБ или отключить (с осторожностью)"


class MemoryModule(OptimizerModule):
    key = "memory"
    title = "Память"

    def ram_total_gb(self) -> float:
        if psutil is None:
            return 0.0
        try:
            return round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            return 0.0

    def scan(self) -> List[Dict]:
        ram = self.ram_total_gb()
        rows: List[Dict] = [
            {"item": "Объём ОЗУ", "value": f"{ram} ГБ"},
            {"item": "Рекомендуемый pagefile", "value": pagefile_recommendation(ram)},
        ]
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                rows.append({"item": "Используется", "value": f"{round(vm.used/(1024**3),1)} ГБ ({vm.percent}%)"})
            except Exception as e:
                _log.debug("psutil: не удалось получить использование памяти: %s", e)
        # LargeSystemCache: 0 = приоритет приложениям (рекомендуется для десктопа)
        if IS_WINDOWS:
            try:
                cur, _ = reg.read_value("HKLM", _MEMMGMT, "LargeSystemCache")
                label = {0: "приоритет приложениям (десктоп)",
                         1: "приоритет системному кэшу (сервер)"}.get(cur, "не задан")
                rows.append({"item": "Системный кэш", "value": label})
            except Exception as e:
                _log.debug("Не удалось прочитать LargeSystemCache: %s", e)
        return rows

    def set_large_system_cache(self, value: int = 0) -> bool:
        """0 — приоритет приложениям (десктоп), 1 — системному кэшу (сервер)."""
        if not IS_WINDOWS:
            return False
        try:
            old, _ = reg.read_value("HKLM", _MEMMGMT, "LargeSystemCache")
            reg.write_value("HKLM", _MEMMGMT, "LargeSystemCache", value, "REG_DWORD")
            log_change("memory", "LargeSystemCache", old=old, new=value)
            return True
        except Exception as e:  # pragma: no cover
            log_change("memory", "LargeSystemCache", status=f"ERROR:{e}")
            return False

    def empty_working_sets(self) -> int:
        """Освободить рабочие наборы процессов (EmptyWorkingSet). Возвращает число обработанных."""
        if not IS_WINDOWS:
            return 0
        import ctypes

        count = 0
        try:
            import psutil as ps  # type: ignore

            psapi = ctypes.WinDLL("psapi.dll")
            for proc in ps.process_iter(["pid"]):
                try:
                    h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info["pid"])
                    if h:
                        psapi.EmptyWorkingSet(h)
                        ctypes.windll.kernel32.CloseHandle(h)
                        count += 1
                except Exception:
                    continue
        except Exception as e:  # pragma: no cover
            log_change("memory", "empty_working_sets", status=f"ERROR:{e}")
        log_change("memory", "empty_working_sets", new=f"{count} процессов")
        return count
