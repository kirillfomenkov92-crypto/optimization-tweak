"""Дашборд: системные метрики в реальном времени и быстрые действия."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.core import system_info


class MetricCard(QFrame):
    """Карточка одной метрики (значение + подпись)."""

    def __init__(self, label: str, unit: str = "") -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        self._unit = unit
        layout = QVBoxLayout(self)
        self.value_lbl = QLabel("—")
        self.value_lbl.setObjectName("MetricValue")
        self.name_lbl = QLabel(label)
        self.name_lbl.setObjectName("MetricLabel")
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.name_lbl)

    def set_value(self, value) -> None:
        self.value_lbl.setText(f"{value}{self._unit}")


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
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Дашборд")
        title.setObjectName("Title")
        root.addWidget(title)

        sub = QLabel(
            f"{self.info.os_name} · {self.info.cpu_name} · "
            f"{self.info.cpu_cores} ядер / {self.info.cpu_threads} потоков · "
            f"{self.info.ram_total_gb} ГБ ОЗУ"
        )
        sub.setObjectName("Subtitle")
        sub.setWordWrap(True)
        root.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.card_cpu = MetricCard("Загрузка CPU", " %")
        self.card_ram = MetricCard("Память", " %")
        self.card_disk = MetricCard("Диск C:", " %")
        grid.addWidget(self.card_cpu, 0, 0)
        grid.addWidget(self.card_ram, 0, 1)
        grid.addWidget(self.card_disk, 0, 2)
        root.addLayout(grid)

        actions = QHBoxLayout()
        for text in ("Быстрая оптимизация", "Полное сканирование", "Точка восстановления"):
            btn = QPushButton(text)
            btn.setObjectName("Primary")
            actions.addWidget(btn)
        actions.addStretch(1)
        root.addLayout(actions)
        root.addStretch(1)

    def _refresh(self) -> None:
        m = system_info.live_metrics()
        self.card_cpu.set_value(round(m["cpu_percent"]))
        self.card_ram.set_value(round(m["ram_percent"]))
        self.card_disk.set_value(round(m["disk_percent"]))
