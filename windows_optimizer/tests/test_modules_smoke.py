"""Смоук-тест всех функциональных модулей (instantiate + scan/info).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_modules_smoke.py

На не-Windows многие scan() возвращают пустые/ограниченные данные — это
нормально; тест проверяет, что НИ ОДИН модуль не падает при создании и скане.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


def try_call(label: str, fn) -> None:
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        import traceback
        _failures.append(f"{label}: {e}\n{traceback.format_exc()}")


from app.modules.registry import RegistryModule          # noqa: E402
from app.modules.startup import StartupModule            # noqa: E402
from app.modules.services import ServicesModule          # noqa: E402
from app.modules.disk import DiskModule                  # noqa: E402
from app.modules.privacy import PrivacyModule            # noqa: E402
from app.modules.network import NetworkModule            # noqa: E402
from app.modules.power import PowerModule                # noqa: E402
from app.modules.memory import MemoryModule              # noqa: E402
from app.modules.gaming import GamingModule              # noqa: E402
from app.modules.gpu import GpuModule                    # noqa: E402
from app.modules.cpu import CpuModule                    # noqa: E402
from app.modules.security import SecurityModule          # noqa: E402

# Каждый модуль: создать и вызвать scan() (и info() где есть) — без падений.
for name, factory in [
    ("registry", RegistryModule), ("startup", StartupModule), ("services", ServicesModule),
    ("disk", DiskModule), ("privacy", PrivacyModule), ("network", NetworkModule),
    ("power", PowerModule), ("memory", MemoryModule), ("gaming", GamingModule),
    ("gpu", GpuModule), ("cpu", CpuModule), ("security", SecurityModule),
]:
    mod = None
    try_call(f"{name}.__init__", lambda f=factory: globals().__setitem__("_m", f()))
    mod = globals().get("_m")
    if mod is None:
        continue
    if hasattr(mod, "scan"):
        rows = []
        try_call(f"{name}.scan", lambda m=mod: rows.append(m.scan()))
        if rows:
            check(isinstance(rows[0], list), f"{name}.scan должен вернуть list, вернул {type(rows[0])}")
    if hasattr(mod, "info"):
        try_call(f"{name}.info", lambda m=mod: m.info())


# RegistryModule должен реально загрузить твики из БД.
check(len(RegistryModule().tweaks) > 0, "RegistryModule не загрузил твики из БД")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} модулей с ошибкой")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: все модули создаются и сканируют без падений.")
