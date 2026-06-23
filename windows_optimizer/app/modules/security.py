"""Модуль безопасности: статус Defender, исключения, UAC, SmartScreen, Firewall.

Безопасность приоритетна: отключение Real-time Protection и понижение UAC
помечены как опасные и требуют явного подтверждения на уровне UI.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Dict, List, Optional

from app.core.logger import log_change
from app.core.optimizer import OptimizerModule
from app.utils import registry_helper as reg

IS_WINDOWS = sys.platform == "win32"

_UAC = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"


def _ps(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                          capture_output=True, text=True)


class SecurityModule(OptimizerModule):
    key = "security"
    title = "Безопасность"

    def defender_status(self) -> Dict:
        if not IS_WINDOWS:
            return {}
        try:
            out = _ps("(Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AntivirusEnabled | ConvertTo-Json)").stdout
            import json
            return json.loads(out) if out.strip() else {}
        except Exception:
            return {}

    def add_defender_exclusion(self, path: str) -> bool:
        """Добавить папку в исключения Defender (Add-MpPreference)."""
        if not IS_WINDOWS:
            return False
        try:
            cp = _ps(f"Add-MpPreference -ExclusionPath '{path}'")
            ok = cp.returncode == 0
            log_change("security", f"Defender exclusion {path}",
                       status="SUCCESS" if ok else f"ERROR:{cp.stderr.strip()}")
            return ok
        except Exception as e:  # pragma: no cover
            log_change("security", "Defender exclusion", status=f"ERROR:{e}")
            return False

    def uac_level(self) -> Optional[int]:
        if not IS_WINDOWS:
            return None
        try:
            cur, _ = reg.read_value("HKLM", _UAC, "ConsentPromptBehaviorAdmin")
            return cur
        except Exception:
            return None

    def firewall_status(self) -> str:
        if not IS_WINDOWS:
            return "—"
        try:
            return _ps("(Get-NetFirewallProfile | Select-Object Name,Enabled | Format-Table -HideTableHeaders | Out-String)").stdout.strip()
        except Exception:
            return "—"

    def scan(self) -> List[Dict]:
        rows: List[Dict] = []
        st = self.defender_status()
        if st:
            rows.append({"item": "Defender Real-time", "value": str(st.get("RealTimeProtectionEnabled"))})
            rows.append({"item": "Антивирус включён", "value": str(st.get("AntivirusEnabled"))})
        else:
            rows.append({"item": "Defender", "value": "(статус доступен на Windows)"})
        uac = self.uac_level()
        rows.append({"item": "UAC (ConsentPromptBehaviorAdmin)", "value": str(uac)})
        return rows
