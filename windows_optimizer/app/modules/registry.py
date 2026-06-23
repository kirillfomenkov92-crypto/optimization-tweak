"""Модуль реестра: загрузка твиков из БД, применение/проверка/откат."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.core.logger import get_logger
from app.core.optimizer import OptimizerModule, Tweak, TweakStatus

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "tweaks_database.json"
_log = get_logger()


class RegistryModule(OptimizerModule):
    key = "registry"
    title = "Реестр"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or _DB_PATH
        self.tweaks: List[Tweak] = []
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            self.tweaks = [Tweak.from_dict(t) for t in data.get("tweaks", [])]
            _log.info("Загружено твиков реестра: %d", len(self.tweaks))
        except Exception as e:
            _log.error("Не удалось загрузить БД твиков: %s", e)
            self.tweaks = []

    def by_category(self) -> Dict[str, List[Tweak]]:
        groups: Dict[str, List[Tweak]] = {}
        for t in self.tweaks:
            groups.setdefault(t.category, []).append(t)
        return groups

    def get(self, tweak_id: str) -> Optional[Tweak]:
        return next((t for t in self.tweaks if t.id == tweak_id), None)

    def scan(self) -> List[Dict]:
        """Вернуть статус каждого твика."""
        result = []
        for t in self.tweaks:
            try:
                st = t.status()
            except Exception:
                st = TweakStatus.UNKNOWN
            result.append({
                "id": t.id, "name": t.name, "category": t.category,
                "risk": t.risk.value, "status": st.value,
                "reboot_required": t.reboot_required, "description": t.description,
            })
        return result

    def apply_many(self, ids: List[str]) -> Dict[str, bool]:
        return {tid: (self.get(tid).apply() if self.get(tid) else False) for tid in ids}

    def revert_many(self, ids: List[str]) -> Dict[str, bool]:
        return {tid: (self.get(tid).revert() if self.get(tid) else False) for tid in ids}

    def health_score(self) -> int:
        """Доля применённых безопасных твиков как простая оценка."""
        if not self.tweaks:
            return 100
        applied = sum(1 for t in self.tweaks if _safe_status(t) == TweakStatus.APPLIED)
        return int(round(applied / len(self.tweaks) * 100))


def _safe_status(t: Tweak) -> TweakStatus:
    try:
        return t.status()
    except Exception:
        return TweakStatus.UNKNOWN
