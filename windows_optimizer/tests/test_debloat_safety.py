"""Тесты защитного слоя встроенного деблоата (app/debloat).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_debloat_safety.py

Гарантирует: Windows Update / Defender / Store / ядро ОС защищены в любом
регистре, граница имени пакетов корректна, и ни один встроенный playbook не
трогает защищённую службу/ветку/пакет.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]  # windows_optimizer/
sys.path.insert(0, str(ROOT))

from app.debloat import safety  # noqa: E402
from app.utils.resources import resource_path  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# 1) Критичные службы защищены в любом регистре.
for svc in ["wuauserv", "WUAUSERV", "Wuauserv", "bits", "BITS",
            "WinDefend", "windefend", "InstallService", "wscsvc", "RpcSs"]:
    check(safety.is_protected_service(svc), f"служба должна быть защищена: {svc!r}")

# 2) Безопасные для отключения службы НЕ защищены.
for svc in ["DiagTrack", "dmwappushservice", "XblGameSave", "SysMain"]:
    check(not safety.is_protected_service(svc), f"служба не должна быть защищена: {svc!r}")

# 3) Store/Defender/.NET защищены; граница имени не ловит посторонние пакеты.
for pkg in ["Microsoft.WindowsStore", "microsoft.windowsstore_8wekyb3d8bbwe",
            "Microsoft.SecHealthUI", "Microsoft.NET.Native.Framework.2.2"]:
    check(safety.is_protected_appx(pkg), f"пакет должен быть защищён: {pkg!r}")
for pkg in ["Microsoft.NetworkSpeedTest"]:
    check(not safety.is_protected_appx(pkg), f"пакет НЕ должен попадать под защиту: {pkg!r}")

# 4) Ветки Defender в реестре защищены (любой регистр/слэши).
for path in [r"HKLM\SOFTWARE\Microsoft\Windows Defender",
             "HKLM/SOFTWARE/Policies/Microsoft/Windows Defender"]:
    check(safety.is_protected_registry(path), f"ветка должна быть защищена: {path!r}")

# 5) Главный инвариант: ни один встроенный playbook не трогает защищённое.
pb_dir = resource_path("app", "debloat", "playbooks")
for pb_file in glob.glob(str(pb_dir / "*.json")):
    pb = json.loads(Path(pb_file).read_text(encoding="utf-8"))
    name = Path(pb_file).name
    for cat in pb.get("categories", []):
        svc_names = list(cat.get("services_disable", [])) + \
            [s.get("name") for s in cat.get("services", [])]
        for s in svc_names:
            check(not safety.is_protected_service(s),
                  f"{name}: playbook трогает защищённую службу {s!r}")
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
    print("OK: защитный слой встроенного деблоата корректен.")
