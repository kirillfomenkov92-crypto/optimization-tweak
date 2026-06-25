"""Тесты защитного слоя TurboDebloat.

Запуск (из корня репозитория):
    python turbo_debloat/tests/test_safety.py

Проверяет главную гарантию инструмента: Windows Update / Defender / Store и
ядро ОС защищены НЕЗАВИСИМО от регистра имени, и ни один поставляемый
playbook не пытается отключить защищённую службу/ветку/пакет.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

# Консоль Windows по умолчанию cp1252 — кириллица в print ломает её.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from turbo_debloat.core import safety  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# 1) Критичные службы защищены в любом регистре.
for svc in ["wuauserv", "WUAUSERV", "Wuauserv", "bits", "BITS", "Bits",
            "WinDefend", "windefend", "WINDEFEND",
            "InstallService", "installservice",  # Store
            "wscsvc", "mpssvc", "Sense", "RpcSs", "DcomLaunch"]:
    check(safety.is_protected_service(svc), f"служба должна быть защищена: {svc!r}")

# 2) Безопасные для отключения службы НЕ защищены (иначе инструмент бесполезен).
for svc in ["DiagTrack", "dmwappushservice", "XblGameSave", "SysMain"]:
    check(not safety.is_protected_service(svc), f"служба не должна быть защищена: {svc!r}")

# 3) Store/Defender-пакеты и .NET-рантайм защищены в любом регистре.
for pkg in ["Microsoft.WindowsStore", "microsoft.windowsstore_8wekyb3d8bbwe",
            "Microsoft.SecHealthUI", "Microsoft.DesktopAppInstaller",
            "Microsoft.NET.Native.Framework.2.2", "Microsoft.VCLibs.140.00"]:
    check(safety.is_protected_appx(pkg), f"пакет должен быть защищён: {pkg!r}")

# 3b) Граница имени: префикс защиты НЕ должен ловить посторонние пакеты.
for pkg in ["Microsoft.NetworkSpeedTest", "Microsoft.WindowsStoreApp.Extra"]:
    check(not safety.is_protected_appx(pkg),
          f"пакет НЕ должен попадать под защиту по границе имени: {pkg!r}")

# 4) Ветки Defender в реестре защищены (любой регистр/слэши).
for path in [r"HKLM\SOFTWARE\Microsoft\Windows Defender",
             r"hklm\software\microsoft\windows defender\real-time protection",
             "HKLM/SOFTWARE/Policies/Microsoft/Windows Defender"]:
    check(safety.is_protected_registry(path), f"ветка должна быть защищена: {path!r}")

# 5) Главный инвариант: ни один поставляемый playbook не трогает защищённое.
for pb_file in glob.glob(str(ROOT / "turbo_debloat" / "playbooks" / "*.json")):
    pb = json.loads(Path(pb_file).read_text(encoding="utf-8"))
    name = Path(pb_file).name
    for cat in pb.get("categories", []):
        svc_names = list(cat.get("services_disable", [])) + \
            [s.get("name") for s in cat.get("services", [])]
        for s in svc_names:
            check(not safety.is_protected_service(s),
                  f"{name}: playbook пытается тронуть защищённую службу {s!r}")
        for entry in cat.get("registry", []):
            check(not safety.is_protected_registry(entry[0]),
                  f"{name}: playbook пишет в защищённую ветку {entry[0]!r}")
        for pkg in cat.get("appx_remove_all_users", []):
            check(not safety.is_protected_appx(pkg),
                  f"{name}: playbook удаляет защищённый пакет {pkg!r}")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: защитный слой TurboDebloat корректен (включая регистронезависимость).")
