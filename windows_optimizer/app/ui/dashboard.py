"""Дашборд: состояние системы (кольцо), метрики реального времени, действия."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from app.core import system_info, backup
from app.ui.widgets.health_ring import HealthScoreRing, score_caption
from app.ui.widgets.progress_overlay import ProgressOverlay
from app.ui.widgets.toast import Toast
from app.ui.widgets.worker import StepWorker


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
        self.optimize_btn.clicked.connect(self._start_optimize)
        self._overlay = ProgressOverlay(self)
        self._worker = None
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

    # ----- быстрая оптимизация -----
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._overlay.isVisible():
            self._overlay.resize(self.size())

    def _start_optimize(self) -> None:
        self.optimize_btn.setEnabled(False)
        self._overlay.begin()
        steps = [
            ("Сохраняем состояние системы…", self._step_backup),
            ("Включаем безопасные улучшения…", self._step_apply_safe),
            ("Очищаем временные файлы…", self._step_clean_temp),
        ]
        # stop_on_error: если бэкап не удался — не применяем остальные шаги.
        self._worker = StepWorker(steps, stop_on_error=True)
        self._worker.step.connect(self._overlay.set_progress)
        self._worker.step_done.connect(self._overlay.mark_done)
        self._worker.finished_ok.connect(self._optimize_done)
        self._worker.failed.connect(self._optimize_failed)
        self._worker.start()

    def _step_backup(self):
        return backup.create_backup("quick", hives=["HKLM", "HKCU"])

    def _step_apply_safe(self):
        from app.modules.registry import RegistryModule

        mod = RegistryModule()
        ids = [r["id"] for r in mod.scan()
               if r.get("risk_level") == "safe" and r.get("simple_mode_visible", True)
               and r.get("status") != "applied"]
        return mod.apply_many(ids) if ids else {}

    def _step_clean_temp(self):
        from app.modules.disk import DiskModule

        return DiskModule().clean(["Временные файлы пользователя", "Temp в LocalAppData"])

    def _optimize_done(self, results: dict) -> None:
        freed = 0
        applied = 0
        for v in results.values():
            if isinstance(v, dict):
                for k, val in v.items():
                    if isinstance(val, bool) and val:
                        applied += 1
                    elif isinstance(val, int):
                        freed += val
        mb = round(freed / (1024 * 1024), 1)
        self._overlay.finish(f"Применено улучшений: {applied}. Очищено: {mb} МБ.")
        self.optimize_btn.setEnabled(True)
        Toast.show_message(self, f"Готово! Улучшений: {applied}, очищено {mb} МБ.", "success")
        # обновляем кольцо состояния
        self.ring.set_value(_health_score())
        self.caption.setText(score_caption(_health_score()))

    def _optimize_failed(self, msg: str) -> None:
        self._overlay.finish(f"Не удалось завершить: {msg}")
        self.optimize_btn.setEnabled(True)
        Toast.show_message(self, f"Ошибка: {msg}", "error")
