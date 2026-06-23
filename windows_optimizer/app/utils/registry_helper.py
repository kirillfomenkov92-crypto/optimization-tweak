"""Вспомогательные функции для работы с реестром Windows.

Тонкая обёртка над ``winreg`` с понятными ошибками. На не-Windows функции
импортируются, но при вызове бросают RuntimeError (для тестов/импорта).
"""
from __future__ import annotations

import sys
from typing import Any, Optional, Tuple

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg  # type: ignore

    _HIVES = {
        "HKLM": winreg.HKEY_LOCAL_MACHINE,
        "HKCU": winreg.HKEY_CURRENT_USER,
        "HKCR": winreg.HKEY_CLASSES_ROOT,
        "HKU": winreg.HKEY_USERS,
        "HKCC": winreg.HKEY_CURRENT_CONFIG,
    }
    _TYPES = {
        "REG_DWORD": winreg.REG_DWORD,
        "REG_QWORD": winreg.REG_QWORD,
        "REG_SZ": winreg.REG_SZ,
        "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
        "REG_BINARY": winreg.REG_BINARY,
        "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
    }


def _require_windows() -> None:
    if not IS_WINDOWS:
        raise RuntimeError("Операции с реестром доступны только на Windows.")


def _hive(name: str):
    _require_windows()
    try:
        return _HIVES[name.upper()]
    except KeyError as e:
        raise ValueError(f"Неизвестный куст реестра: {name}") from e


def read_value(hive: str, path: str, name: str) -> Tuple[Optional[Any], Optional[int]]:
    """Прочитать значение. Возвращает (value, type) или (None, None), если нет."""
    _require_windows()
    try:
        with winreg.OpenKey(_hive(hive), path, 0, winreg.KEY_READ) as key:
            value, regtype = winreg.QueryValueEx(key, name)
            return value, regtype
    except FileNotFoundError:
        return None, None


def write_value(hive: str, path: str, name: str, value: Any, regtype: str = "REG_DWORD") -> None:
    """Записать значение, создав путь при необходимости."""
    _require_windows()
    rtype = _TYPES.get(regtype.upper())
    if rtype is None:
        raise ValueError(f"Неизвестный тип реестра: {regtype}")
    key = winreg.CreateKeyEx(_hive(hive), path, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, name, 0, rtype, value)
    finally:
        winreg.CloseKey(key)


def delete_value(hive: str, path: str, name: str) -> bool:
    """Удалить значение. True — удалено, False — не было."""
    _require_windows()
    try:
        with winreg.OpenKey(_hive(hive), path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
            return True
    except FileNotFoundError:
        return False
