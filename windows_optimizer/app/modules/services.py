"""Модуль служб Windows: категоризация и смена типа запуска.

Службы разбиты на группы: безопасно отключить / осторожно / никогда.
Группа «никогда» — жёсткая защита: такие службы не трогаются ни при каких
условиях. Чтение состояния — через psutil, изменение — через `sc config`.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List

from app.core.logger import get_logger, log_change
from app.core.optimizer import OptimizerModule

IS_WINDOWS = sys.platform == "win32"
_log = get_logger()

# Безопасно отключить на домашнем ПК.
SAFE_TO_DISABLE = {
    "DiagTrack": "Телеметрия (Connected User Experiences)",
    "dmwappushservice": "WAP Push маршрутизация (телеметрия)",
    "MapsBroker": "Загрузка офлайн-карт",
    "lfsvc": "Геолокация",
    "RetailDemo": "Демо-режим магазина",
    "Fax": "Факс",
    "WerSvc": "Отчёты об ошибках Windows",
    "wisvc": "Windows Insider",
    "WMPNetworkSvc": "Обмен Windows Media Player",
    "XblAuthManager": "Xbox Live аутентификация",
    "XblGameSave": "Xbox сохранения",
    "XboxNetApiSvc": "Xbox сеть",
}

# Отключать по ситуации.
CAUTION = {
    "WSearch": "Поиск Windows (нужен для индекса в Проводнике)",
    "SysMain": "Superfetch (на HDD оставить, на SSD можно отключить)",
    "Spooler": "Диспетчер печати (нужен с принтером)",
    "bthserv": "Bluetooth (нужен при наличии Bluetooth)",
    "TabletInputService": "Сенсорная клавиатура (нужна на планшетах)",
    "WbioSrvc": "Биометрия (нужна для отпечатка/лица)",
}

# Никогда не трогать (критично для системы/безопасности/обновлений).
NEVER = {
    "RpcSs", "DcomLaunch", "RpcEptMapper", "LSM", "BrokerInfrastructure",
    "SystemEventsBroker", "Power", "Schedule", "ProfSvc", "Themes",
    "wuauserv", "BITS", "UsoSvc", "WinDefend", "SecurityHealthService",
    "Sense", "WdNisSvc", "wscsvc", "mpssvc", "InstallService", "AppXSvc",
    "ClipSVC", "EventLog", "PlugPlay", "Dhcp", "Dnscache", "nsi",
}

# Имена служб Windows регистронезависимы. Заранее готовим версии в нижнем
# регистре, чтобы классификация и (главное) защита NEVER не зависели от того,
# в каком регистре служба пришла из перечисления/UI.
_NEVER_LC = {s.lower() for s in NEVER}
_SAFE_LC = {k.lower(): v for k, v in SAFE_TO_DISABLE.items()}
_CAUTION_LC = {k.lower(): v for k, v in CAUTION.items()}

_START_MAP = {"auto": "auto", "manual": "demand", "disabled": "disabled"}


class ServicesModule(OptimizerModule):
    key = "services"
    title = "Службы"

    def group_of(self, name: str) -> str:
        n = (name or "").lower()
        if n in _NEVER_LC:
            return "never"
        if n in _SAFE_LC:
            return "safe"
        if n in _CAUTION_LC:
            return "caution"
        return "other"

    def scan(self) -> List[Dict]:
        if not IS_WINDOWS:
            return []
        import psutil  # type: ignore

        result: List[Dict] = []
        try:
            for svc in psutil.win_service_iter():
                try:
                    info = svc.as_dict()
                except Exception:
                    continue
                name = info.get("name", "")
                grp = self.group_of(name)
                if grp == "other":
                    continue  # в UI показываем только классифицированные
                result.append({
                    "name": name,
                    "display_name": info.get("display_name", name),
                    "status": info.get("status", ""),
                    "start_type": info.get("start_type", ""),
                    "group": grp,
                    "note": _SAFE_LC.get(name.lower()) or _CAUTION_LC.get(name.lower()) or "",
                })
        except Exception as e:  # pragma: no cover
            _log.error("Перечисление служб не удалось: %s", e)
        return result

    def set_start_type(self, name: str, mode: str) -> bool:
        """Сменить тип запуска службы. mode: auto|manual|disabled."""
        if (name or "").lower() in _NEVER_LC:
            log_change("services", f"ЗАЩИТА: пропуск критической службы {name}", status="SKIPPED")
            return False
        if not IS_WINDOWS:
            return False
        sc_mode = _START_MAP.get(mode)
        if not sc_mode:
            raise ValueError(f"Неизвестный режим: {mode}")
        try:
            cp = subprocess.run(["sc", "config", name, f"start={sc_mode}"],
                                capture_output=True, text=True)
            ok = cp.returncode == 0
            log_change("services", f"{name} start={sc_mode}",
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("services", f"{name} start={sc_mode}", status=f"ERROR:{e}")
            return False
