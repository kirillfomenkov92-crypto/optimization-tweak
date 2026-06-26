"""Тесты очистки диска (безопасность и подсчёт освобождённого).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_disk_clean.py

Используется временная папка как TEMP — реальные файловые операции, но в
изолированном каталоге. Система не трогается.
"""
from __future__ import annotations

import os
import sys
import tempfile
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


with tempfile.TemporaryDirectory() as tmp_temp, tempfile.TemporaryDirectory() as tmp_other:
    # Подменяем TEMP и LOCALAPPDATA на изолированные каталоги.
    os.environ["TEMP"] = tmp_temp
    os.environ["LOCALAPPDATA"] = tmp_other

    from app.modules.disk import DiskModule  # импорт после установки env

    temp = Path(tmp_temp)
    (temp / "a.tmp").write_bytes(b"x" * 1000)
    sub = temp / "sub"; sub.mkdir()
    (sub / "b.log").write_bytes(b"y" * 2000)

    # Контрольный файл в ДРУГОЙ категории — не должен быть тронут.
    other_keep = Path(tmp_other) / "keep.dat"
    other_keep.write_bytes(b"z" * 500)

    mod = DiskModule()

    # scan видит размер temp-папки.
    rows = {r["label"]: r for r in mod.scan()}
    check("Временные файлы пользователя" in rows, "scan должен включать пользовательский TEMP")
    check(rows["Временные файлы пользователя"]["size_bytes"] >= 3000,
          f"размер TEMP должен быть >=3000, получено {rows['Временные файлы пользователя']['size_bytes']}")

    # clean чистит только запрошенную категорию и считает байты.
    freed = mod.clean(["Временные файлы пользователя"])
    check(freed.get("Временные файлы пользователя", 0) >= 3000,
          f"освобождено должно быть >=3000, получено {freed}")
    check(not list(temp.iterdir()), "TEMP должен быть очищен")

    # Файл в другой категории НЕ тронут.
    check(other_keep.exists(), "файл вне запрошенной категории не должен удаляться")

    # Очистка несуществующей метки безопасна (пустой результат, без ошибок).
    check(mod.clean(["Несуществующая категория"]) == {}, "неизвестная метка -> пустой результат")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: очистка диска безопасна и корректно считает освобождённое.")
