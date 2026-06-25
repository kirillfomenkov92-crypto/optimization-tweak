"""Тест подсчёта ошибок при откате встроенного деблоата (app/debloat/restore).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_debloat_restore.py

Частично сбойный откат должен отражаться в report['failed'] (>0).
"""
from __future__ import annotations

import json
import subprocess
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

from app.debloat import restore as restore_mod  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


class _FakeProc:
    def __init__(self, returncode: int, stderr: str = "boom") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = ""


def _make_backup(tmp: Path) -> Path:
    folder = tmp / "backup_test"
    (folder / "registry").mkdir(parents=True, exist_ok=True)
    (folder / "registry" / "HKLM.reg").write_text("Windows Registry Editor Version 5.00\n", encoding="utf-8")
    (folder / "services_state.json").write_text(
        json.dumps({"DiagTrack": "AUTO_START", "SysMain": "DEMAND_START"}), encoding="utf-8")
    return folder


# 1) Все sc/reg возвращают ненулевой код => failed >= 3.
with tempfile.TemporaryDirectory() as d:
    folder = _make_backup(Path(d))
    ow, orun = restore_mod.IS_WINDOWS, subprocess.run
    restore_mod.IS_WINDOWS = True
    restore_mod.subprocess.run = lambda *a, **k: _FakeProc(1)
    try:
        rep = restore_mod.restore(folder, dry_run=False)
    finally:
        restore_mod.IS_WINDOWS, restore_mod.subprocess.run = ow, orun
    check("failed" in rep, "report должен содержать 'failed'")
    check(rep.get("failed", 0) >= 3, f"ожидалось failed>=3, получено {rep.get('failed')}")

# 2) Все успешны => failed == 0.
with tempfile.TemporaryDirectory() as d:
    folder = _make_backup(Path(d))
    ow, orun = restore_mod.IS_WINDOWS, subprocess.run
    restore_mod.IS_WINDOWS = True
    restore_mod.subprocess.run = lambda *a, **k: _FakeProc(0)
    try:
        rep = restore_mod.restore(folder, dry_run=False)
    finally:
        restore_mod.IS_WINDOWS, restore_mod.subprocess.run = ow, orun
    check(rep.get("failed", -1) == 0, f"при успехе failed=0, получено {rep.get('failed')}")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: подсчёт ошибок отката встроенного деблоата корректен.")
