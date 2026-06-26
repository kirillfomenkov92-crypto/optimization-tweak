"""Тесты оценки влияния автозагрузки на старт.

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_startup_impact.py
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

from app.modules.startup import estimate_impact  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# Тяжёлые приложения => high.
for name, cmd in [("Steam", r"C:\Program Files\Steam\steam.exe"),
                  ("Adobe CCXProcess", "CCXProcess.exe"),
                  ("Discord", "Update.exe"),
                  ("OneDrive", "OneDrive.exe")]:
    check(estimate_impact(name, cmd) == "high", f"{name} должно быть high, получено {estimate_impact(name, cmd)}")

# Лёгкие драйверы => low.
for name in ["RealtekAudio", "SynapticsTouchpad", "SecurityHealth"]:
    check(estimate_impact(name) == "low", f"{name} должно быть low, получено {estimate_impact(name)}")

# Неизвестное => medium.
check(estimate_impact("MyLittleUtility", "util.exe") == "medium", "неизвестное => medium")

# Регистр не важен.
check(estimate_impact("STEAM") == "high", "регистронезависимость")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: оценка влияния автозагрузки корректна.")
