"""Тесты форматирования строк scan() (читаемость разделов).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_row_format.py

Регрессия на баг, замеченный на живой Windows: раздел Питание показывал
"[] <план> — " (пустые скобки + висящее тире).
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

from app.ui.widgets.row_format import format_scan_row  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


# 1) Питание: активный план — без пустых скобок, с пометкой активности.
out = format_scan_row({"name": "Высокая производительность", "guid": "x", "active": True})
check(out == "Высокая производительность  —  ● активен", f"активный план: {out!r}")

# 2) Питание: обычный план — чистое имя, без висящего тире.
out = format_scan_row({"name": "Сбалансированный", "guid": "y", "active": False})
check(out == "Сбалансированный", f"обычный план: {out!r}")
check("—" not in out and "[]" not in out, f"не должно быть тире/скобок: {out!r}")

# 3) Сеть/Игры: статус переведён на русский.
out = format_scan_row({"name": "TcpAckFrequency", "description": "Убрать задержку", "status": "applied"})
check("✓ применён" in out and "applied" not in out, f"статус не переведён: {out!r}")

# 4) Инфо-строки {item,value} (CPU, Память).
check(format_scan_row({"item": "Частота", "value": "3200 МГц"}) == "Частота: 3200 МГц",
      "инфо-строка item:value")
check(format_scan_row({"item": "Ядра", "value": ""}) == "Ядра", "пустое value — без двоеточия")

# 5) Никогда не выводим пустые скобки/висящее тире ни на одной форме.
for r in [{"name": "X"}, {"item": "Y"}, {"name": "Z", "status": ""},
          {"name": "W", "description": ""}]:
    s = format_scan_row(r)
    check("[]" not in s, f"пустые скобки в {s!r}")
    check(not s.endswith("—") and not s.endswith("— "), f"висящее тире в {s!r}")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: форматирование строк scan() читаемо и без артефактов.")
