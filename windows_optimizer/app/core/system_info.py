"""Сбор информации о системе и метрик реального времени.

Использует psutil (кроссплатформенно) и, при наличии, WMI для деталей
Windows. Все обращения защищены try/except, чтобы отсутствие компонента
не роняло приложение.
"""
from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from typing import List, Optional

IS_WINDOWS = sys.platform == "win32"

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # type: ignore


@dataclass
class DiskInfo:
    device: str
    media_type: str          # 'SSD' | 'HDD' | 'Unknown'
    size_gb: float


@dataclass
class SystemInfo:
    os_name: str = ""
    os_build: str = ""
    cpu_name: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    ram_total_gb: float = 0.0
    gpus: List[str] = field(default_factory=list)
    disks: List[DiskInfo] = field(default_factory=list)


def collect() -> SystemInfo:
    """Собрать статическую информацию о системе."""
    info = SystemInfo()
    info.os_name = f"{platform.system()} {platform.release()}"
    info.os_build = platform.version()

    if psutil is not None:
        try:
            info.cpu_cores = psutil.cpu_count(logical=False) or 0
            info.cpu_threads = psutil.cpu_count(logical=True) or 0
            info.ram_total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            pass

    info.cpu_name = platform.processor() or "неизвестно"

    if IS_WINDOWS:
        _enrich_windows(info)
    return info


def _enrich_windows(info: SystemInfo) -> None:
    try:
        import wmi  # type: ignore

        c = wmi.WMI()
        try:
            cpu = c.Win32_Processor()[0]
            info.cpu_name = (cpu.Name or info.cpu_name).strip()
        except Exception:
            pass
        try:
            info.gpus = [g.Name for g in c.Win32_VideoController() if g.Name]
        except Exception:
            pass
        try:
            for d in c.Win32_DiskDrive():
                size = round(int(d.Size) / (1024 ** 3), 0) if d.Size else 0
                mt = "SSD" if (d.MediaType and "SSD" in str(d.MediaType)) else "Unknown"
                info.disks.append(DiskInfo(device=str(d.DeviceID), media_type=mt, size_gb=size))
        except Exception:
            pass
        try:
            os_ = c.Win32_OperatingSystem()[0]
            info.os_name = (os_.Caption or info.os_name).strip()
            info.os_build = str(os_.BuildNumber or info.os_build)
        except Exception:
            pass
    except Exception:
        # WMI недоступен — остаёмся на данных psutil/platform.
        pass


def live_metrics() -> dict:
    """Снимок метрик реального времени для дашборда."""
    metrics = {"cpu_percent": 0.0, "ram_percent": 0.0, "ram_used_gb": 0.0,
               "ram_total_gb": 0.0, "disk_percent": 0.0}
    if psutil is None:
        return metrics
    try:
        metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        metrics["ram_percent"] = vm.percent
        metrics["ram_used_gb"] = round(vm.used / (1024 ** 3), 1)
        metrics["ram_total_gb"] = round(vm.total / (1024 ** 3), 1)
        root = "C:\\" if IS_WINDOWS else "/"
        metrics["disk_percent"] = psutil.disk_usage(root).percent
    except Exception:
        pass
    return metrics
