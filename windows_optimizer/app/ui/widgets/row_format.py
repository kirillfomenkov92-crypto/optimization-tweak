"""Форматирование строк scan() в читаемый вид (без зависимости от Qt).

Разные модули возвращают из scan() словари разной формы ({item,value} или
{name,status,description,active,...}). Эта функция приводит их к чистой
строке без пустых скобок и висящих тире — вынесена отдельно, чтобы покрыть
тестом без PyQt6.
"""
from __future__ import annotations

from typing import Dict, List

# Человеко-понятные подписи статусов вместо applied/default/modified.
_STATUS_RU = {
    "applied": "✓ применён",
    "default": "по умолчанию",
    "modified": "изменён вручную",
    "unknown": "",
    "": "",
}


def format_scan_row(r: Dict) -> str:
    if not isinstance(r, dict):
        return str(r)
    # Информационные строки вида {item, value} (CPU, Память).
    if "item" in r:
        value = str(r.get("value", "")).strip()
        return f"{r['item']}: {value}" if value else str(r["item"])
    # Строки-находки вида {name, ...}.
    name = str(r.get("name", "")).strip()
    bits: List[str] = []
    if r.get("active") is True:          # активный план питания
        bits.append("● активен")
    status = _STATUS_RU.get(str(r.get("status", "")), str(r.get("status", "")))
    if status:
        bits.append(status)
    desc = str(r.get("description", "")).strip()
    if desc:
        bits.append(desc)
    return f"{name}  —  " + " · ".join(bits) if bits else name
