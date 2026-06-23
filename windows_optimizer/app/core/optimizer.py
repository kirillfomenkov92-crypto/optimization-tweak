"""Базовые сущности оптимизатора: Tweak и OptimizerModule.

От ``OptimizerModule`` наследуются все функциональные модули (реестр,
службы, автозагрузка и т.д.). ``Tweak`` описывает одно атомарное изменение
с применением, проверкой и откатом.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.logger import log_change
from app.utils import registry_helper as reg


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TweakStatus(str, Enum):
    APPLIED = "applied"        # значение соответствует оптимизированному
    DEFAULT = "default"        # значение соответствует дефолтному
    MODIFIED = "modified"      # изменено вручную / иное
    UNKNOWN = "unknown"        # не удалось определить


@dataclass
class RegistryChange:
    hive: str
    path: str
    name: str
    type: str
    value_optimized: Any
    value_default: Any


@dataclass
class Tweak:
    """Атомарный твик: одно или несколько изменений реестра + метаданные."""
    id: str
    name: str
    description: str = ""
    category: str = "performance"
    risk: Risk = Risk.LOW
    reboot_required: bool = False
    registry_changes: List[RegistryChange] = field(default_factory=list)

    # --- применение / откат / проверка ---
    def apply(self) -> bool:
        ok = True
        for ch in self.registry_changes:
            try:
                old, _ = reg.read_value(ch.hive, ch.path, ch.name)
                reg.write_value(ch.hive, ch.path, ch.name, ch.value_optimized, ch.type)
                log_change("registry", f"{self.id}:{ch.hive}\\{ch.path}\\{ch.name}",
                           old=old, new=ch.value_optimized)
            except Exception as e:  # pragma: no cover - зависит от ОС
                log_change("registry", f"{self.id}:{ch.name}", status=f"ERROR:{e}")
                ok = False
        return ok

    def revert(self) -> bool:
        ok = True
        for ch in self.registry_changes:
            try:
                old, _ = reg.read_value(ch.hive, ch.path, ch.name)
                reg.write_value(ch.hive, ch.path, ch.name, ch.value_default, ch.type)
                log_change("registry", f"revert {self.id}:{ch.name}", old=old, new=ch.value_default)
            except Exception as e:  # pragma: no cover
                log_change("registry", f"revert {self.id}:{ch.name}", status=f"ERROR:{e}")
                ok = False
        return ok

    def status(self) -> TweakStatus:
        if not self.registry_changes:
            return TweakStatus.UNKNOWN
        states = set()
        for ch in self.registry_changes:
            cur, _ = reg.read_value(ch.hive, ch.path, ch.name)
            if cur is None:
                states.add(TweakStatus.DEFAULT if ch.value_default is None else TweakStatus.UNKNOWN)
            elif cur == ch.value_optimized:
                states.add(TweakStatus.APPLIED)
            elif cur == ch.value_default:
                states.add(TweakStatus.DEFAULT)
            else:
                states.add(TweakStatus.MODIFIED)
        if states == {TweakStatus.APPLIED}:
            return TweakStatus.APPLIED
        if states == {TweakStatus.DEFAULT}:
            return TweakStatus.DEFAULT
        if TweakStatus.MODIFIED in states:
            return TweakStatus.MODIFIED
        return TweakStatus.UNKNOWN

    @classmethod
    def from_dict(cls, d: Dict) -> "Tweak":
        changes = [RegistryChange(**c) for c in d.get("registry_changes", [])]
        return cls(
            id=d["id"],
            name=d.get("name", d["id"]),
            description=d.get("description", ""),
            category=d.get("category", "performance"),
            risk=Risk(d.get("risk", "low")),
            reboot_required=bool(d.get("reboot_required", False)),
            registry_changes=changes,
        )


class OptimizerModule(ABC):
    """Базовый класс функционального модуля оптимизатора."""

    #: машинное имя модуля (для логов/навигации)
    key: str = "module"
    #: человекочитаемое название
    title: str = "Модуль"

    @abstractmethod
    def scan(self) -> List[Dict]:
        """Просканировать систему и вернуть список находок/элементов."""
        raise NotImplementedError

    def health_score(self) -> int:
        """Оценка состояния по модулю (0..100). По умолчанию — нейтральная."""
        return 100
