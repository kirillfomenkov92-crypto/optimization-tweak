"""Дашборд: состояние системы (кольцо), метрики реального времени, действия."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from app.core import system_info
from app.ui.widgets.health_ring import HealthScoreRing, score_caption


def _health_score() -> int:
    """Простая оценка состояния: доля применённых безопасных улучшений,
    смещённая в дружелюбный диапазон 55..100 (чтобы не пугать пользователя)."""
    try:
        from app.modules.registry import RegistryModule

        rows = RegistryModule().scan()
        if not rows:
            return 80
        applied = sum(1 for r in rows if r.get("status") == "applied")
        ratio = applied / len(rows)
        return int(round(55 + ratio * 45))
    except Exception:
        return 80


class MetricCard(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        layout = QVBoxLayout(self)
        self.name_lbl = QLabel(label)
        self.name_lbl.setObjectName("MetricLabel")
        self.value_lbl = QLabel("—")
        self.value_lbl.setObjectName("MetricValue")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.setRange(0, 100)
        layout.addWidget(self.name_lbl)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.bar)

    def set(self, text: str, percent: int) -> None:
        self.value_lbl.setText(text)
        self.bar.setValue(max(0, min(100, int(percent))))


class Dashboard(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.info = system_info.collect()
        self._build()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)
        self._refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        # --- Hero: состояние системы ---
        hero = QHBoxLayout()
        score = _health_score()
        self.ring = HealthScoreRing(score)
        hero.addWidget(self.ring, 0, Qt.AlignmentFlag.AlignLeft)

        hero_text = QVBoxLayout()
        title = QLabel("Состояние системы")
        title.setObjectName("Title")
        self.caption = QLabel(score_caption(score))
        self.caption.setObjectName("Subtitle")
        sub = QLabel(
            f"{self.info.os_name} · {self.info.cpu_name} · "
            f"{self.info.cpu_cores} ядер · {self.info.ram_total_gb} ГБ ОЗУ"
        )
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        hero_text.addStretch(1)
        hero_text.addWidget(title)
        hero_text.addWidget(self.caption)
        hero_text.addWidget(sub)
        hero_text.addStretch(1)
        hero.addLayout(hero_text, 1)
        root.addLayout(hero)

        # --- Главное действие ---
        self.optimize_btn = QPushButton("🚀  Оптимизировать систему")
        self.optimize_btn.setObjectName("Primary")
        self.optimize_btn.setMinimumHeight(56)
        hint = QLabel("Безопасно применит рекомендованные улучшения · перед изменениями создаётся сохранение")
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        root.addWidget(self.optimize_btn)
        root.addWidget(hint)

        # --- Метрики ---
        grid = QGridLayout()
        grid.setSpacing(12)
        self.card_cpu = MetricCard("Процессор")
        self.card_ram = MetricCard("Память")
        self.card_disk = MetricCard("Диск C:")
        grid.addWidget(self.card_cpu, 0, 0)
        grid.addWidget(self.card_ram, 0, 1)
        grid.addWidget(self.card_disk, 0, 2)
        root.addLayout(grid)
        root.addStretch(1)

    def _refresh(self) -> None:
        m = system_info.live_metrics()
        self.card_cpu.set(f"{round(m['cpu_percent'])}%", m["cpu_percent"])
        self.card_ram.set(f"{m['ram_used_gb']} из {m['ram_total_gb']} ГБ", m["ram_percent"])
        self.card_disk.set(f"занято {round(m['disk_percent'])}%", m["disk_percent"])
