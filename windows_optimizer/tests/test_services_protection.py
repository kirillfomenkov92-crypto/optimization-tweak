"""Тесты защиты служб в Windows Optimizer Pro.

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_services_protection.py

Гарантирует, что службы Windows Update / Defender / Store / ядра ОС попадают
в группу "never" НЕЗАВИСИМО от регистра, а безопасные — нет.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Консоль Windows по умолчанию cp1252 — кириллица в print ломает её. Делаем
# вывод UTF-8 независимо от окружения, чтобы тест не падал на этапе печати.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]  # windows_optimizer/
sys.path.insert(0, str(ROOT))

from app.modules.services import ServicesModule, NEVER, SAFE_TO_DISABLE  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


mod = ServicesModule()

# 1) Критичные службы -> группа "never" в любом регистре.
for svc in ["wuauserv", "WUAUSERV", "Wuauserv", "BITS", "bits",
            "WinDefend", "windefend", "AppXSvc", "appxsvc", "wscsvc"]:
    check(mod.group_of(svc) == "never", f"служба должна быть 'never': {svc!r} -> {mod.group_of(svc)!r}")

# 2) Безопасные службы -> "safe" (и точно не "never").
for svc in ["DiagTrack", "diagtrack", "XblGameSave"]:
    g = mod.group_of(svc)
    check(g != "never", f"служба не должна быть 'never': {svc!r} -> {g!r}")

# 3) set_start_type блокирует защищённую службу в любом регистре (без прав/Windows
#    функция всё равно сначала проверяет NEVER и возвращает False до любых действий).
for svc in ["WUAUSERV", "WinDefend", "bits"]:
    check(mod.set_start_type(svc, "disabled") is False,
          f"set_start_type должен отказать для защищённой службы {svc!r}")

# 4) Набор NEVER реально покрывает Update/Defender/Store (на случай правок данных).
must_cover = {"wuauserv", "bits", "windefend", "appxsvc", "installservice"}
never_lc = {s.lower() for s in NEVER}
for s in must_cover:
    check(s in never_lc, f"NEVER должен содержать {s!r}")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: защита служб Optimizer корректна (включая регистронезависимость).")
