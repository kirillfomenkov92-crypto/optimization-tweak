"""Тест подсчёта ошибок при откате TurboDebloat.

Запуск (из корня репозитория):
    python turbo_debloat/tests/test_restore.py

Гарантирует, что частично сбойный откат отражается в report['failed'] (>0),
а не выглядит как полностью успешный.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from turbo_debloat.core import restore as restore_mod  # noqa: E402

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


# --- Сценарий 1: все sc/reg возвращают ненулевой код => failed > 0 ---
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    folder = _make_backup(tmp)

    orig_win = restore_mod.IS_WINDOWS
    orig_run = subprocess.run
    restore_mod.IS_WINDOWS = True
    restore_mod.subprocess.run = lambda *a, **k: _FakeProc(1)
    try:
        report = restore_mod.restore(folder, dry_run=False)
    finally:
        restore_mod.IS_WINDOWS = orig_win
        restore_mod.subprocess.run = orig_run

    check("failed" in report, "report должен содержать ключ 'failed'")
    check(report.get("failed", 0) > 0,
          f"при сбоях откат должен сообщать failed>0, получено {report.get('failed')}")
    # 1 реестр + 2 службы = минимум 3 неуспешных шага
    check(report.get("failed", 0) >= 3,
          f"ожидалось >=3 неуспешных шагов, получено {report.get('failed')}")

# --- Сценарий 2: все команды успешны => failed == 0 ---
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    folder = _make_backup(tmp)

    orig_win = restore_mod.IS_WINDOWS
    orig_run = subprocess.run
    restore_mod.IS_WINDOWS = True
    restore_mod.subprocess.run = lambda *a, **k: _FakeProc(0)
    try:
        report = restore_mod.restore(folder, dry_run=False)
    finally:
        restore_mod.IS_WINDOWS = orig_win
        restore_mod.subprocess.run = orig_run

    check(report.get("failed", -1) == 0,
          f"при успехе failed должен быть 0, получено {report.get('failed')}")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: подсчёт ошибок отката TurboDebloat корректен.")
