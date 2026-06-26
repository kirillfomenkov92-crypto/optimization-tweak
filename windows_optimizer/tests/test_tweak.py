"""Тесты ядра Tweak (apply / revert / status / from_dict).

Запуск (из корня репозитория):
    python windows_optimizer/tests/test_tweak.py

Реестр подменяется словарём в памяти — система не трогается.
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

from app.core import optimizer as opt  # noqa: E402
from app.core.optimizer import Tweak, RegistryChange, TweakStatus  # noqa: E402

_failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        _failures.append(msg)


class FakeReg:
    def __init__(self) -> None:
        self.store: dict = {}
        self.silent_drop: set = set()   # write «успешен», но значение не меняется

    def read_value(self, hive, path, name):
        return self.store.get((hive, path, name), (None, None))

    def write_value(self, hive, path, name, value, regtype="REG_DWORD"):
        if (hive, path, name) in self.silent_drop:
            return
        self.store[(hive, path, name)] = (value, regtype)


def with_fake(fake: FakeReg):
    orig = (opt.reg.read_value, opt.reg.write_value)
    opt.reg.read_value = fake.read_value
    opt.reg.write_value = fake.write_value
    def restore():
        opt.reg.read_value, opt.reg.write_value = orig
    return restore


def make_tweak(default=0, optimized=1):
    return Tweak(id="t1", name="Тест", registry_changes=[
        RegistryChange("HKLM", r"SOFT\A", "V", "REG_DWORD", optimized, default)])


# 1) apply: пишет оптимизированное и подтверждает read-back => True.
fake = FakeReg(); r = with_fake(fake)
try:
    t = make_tweak()
    check(t.apply() is True, "apply должен вернуть True при подтверждённой записи")
    check(fake.store[("HKLM", r"SOFT\A", "V")] == (1, "REG_DWORD"), "значение записано")
    check(t.status() == TweakStatus.APPLIED, "после apply статус APPLIED")
finally:
    r()

# 2) apply с несработавшей записью => False (верификация ловит).
fake = FakeReg(); fake.silent_drop.add(("HKLM", r"SOFT\A", "V")); r = with_fake(fake)
try:
    check(make_tweak().apply() is False, "apply должен вернуть False, если read-back не совпал")
finally:
    r()

# 3) revert: возвращает дефолт; статус становится DEFAULT.
fake = FakeReg(); r = with_fake(fake)
try:
    t = make_tweak(default=0, optimized=1)
    t.apply()
    check(t.revert() is True, "revert True")
    check(fake.store[("HKLM", r"SOFT\A", "V")] == (0, "REG_DWORD"), "вернулось дефолтное")
    check(t.status() == TweakStatus.DEFAULT, "после revert статус DEFAULT")
finally:
    r()

# 4) status: MODIFIED при значении, отличном от обоих.
fake = FakeReg(); fake.store[("HKLM", r"SOFT\A", "V")] = (99, "REG_DWORD"); r = with_fake(fake)
try:
    check(make_tweak().status() == TweakStatus.MODIFIED, "чужое значение => MODIFIED")
finally:
    r()

# 5) status: UNKNOWN без registry_changes.
fake = FakeReg(); r = with_fake(fake)
try:
    check(Tweak(id="x", name="x").status() == TweakStatus.UNKNOWN, "нет изменений => UNKNOWN")
finally:
    r()

# 6) from_dict: разбирает поля и registry_changes.
d = {
    "id": "disable_x", "name": "Откл X", "risk": "low", "risk_level": "safe",
    "registry_changes": [{"hive": "HKCU", "path": "P", "name": "N", "type": "REG_DWORD",
                          "value_optimized": 1, "value_default": 0}],
    "profiles": ["gaming"],
}
tw = Tweak.from_dict(d)
check(tw.id == "disable_x" and len(tw.registry_changes) == 1, "from_dict разобрал твик")
check(tw.registry_changes[0].hive == "HKCU", "from_dict разобрал RegistryChange")
check(tw.profiles == ["gaming"], "from_dict разобрал profiles")


if __name__ == "__main__":
    if _failures:
        print(f"ПРОВАЛ: {len(_failures)} проверок")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("OK: ядро Tweak (apply/revert/status/from_dict) корректно.")
