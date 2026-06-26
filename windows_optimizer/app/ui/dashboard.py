"""Дашборд: состояние системы (кольцо), метрики реального времени, действия."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from app.core import system_info, backup, health
from app.core import smart_optimize as smart
from app.ui.widgets.health_ring import HealthScoreRing, score_caption
from app.ui.widgets.progress_overlay import ProgressOverlay
from app.ui.widgets.toast import Toast
from app.ui.widgets.worker import StepWorker


def _health_score() -> int:
    """Оценка состояния: доля применённых безопасных улучшений (см. app/core/health)."""
    try:
        from app.modules.registry import RegistryModule

        return health.score_from_rows(RegistryModule().scan())
    except Exception:
        return 80


class MetricCard(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("MetricCard")
        # Мягкая тень для ощущения глубины (Apple-стиль).
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor as _QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(_QColor(0, 0, 0, 110))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        self.name_lbl = QLabel(label.upper())   # капс-подпись для иерархии
        self.name_lbl.setObjectName("MetricLabel")
        self.value_lbl = QLabel("—")
        self.value_lbl.setObjectName("MetricValue")
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        self.bar.setRange(0, 100)
        layout.addWidget(self.name_lbl)
        layout.addWidget(self.value_lbl)
        layout.addSpacing(4)
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
        self.optimize_btn = QPushButton("⚡  Ускорить компьютер")
        self.optimize_btn.setObjectName("Primary")
        self.optimize_btn.setMinimumHeight(58)
        self.optimize_btn.clicked.connect(self._start_optimize)
        # Мягкое акцентное свечение под кнопкой (премиум-глубина).
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor as _QC
        _glow = QGraphicsDropShadowEffect(self.optimize_btn)
        _glow.setBlurRadius(40); _glow.setXOffset(0); _glow.setYOffset(10)
        _glow.setColor(_QC(108, 99, 255, 120))   # ACCENT_PRIMARY с прозрачностью
        self.optimize_btn.setGraphicsEffect(_glow)
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
        # Предпросмотр (dry-run): сначала показываем, что будет сделано, и
        # просим подтверждение — ничего не меняем без согласия пользователя.
        try:
            from app.modules.registry import RegistryModule
            count = len(smart.pending_safe_tweak_ids(RegistryModule().scan()))
        except Exception:
            count = 0
        if count:
            msg = (f"Будет применено безопасных улучшений: {count}\n"
                   f"и очищены временные файлы.\n\n"
                   f"Перед изменениями создаётся сохранение для отката. Продолжить?")
        else:
            msg = ("Новых безопасных улучшений нет — будут лишь очищены временные файлы.\n\n"
                   "Перед изменениями создаётся сохранение для отката. Продолжить?")
        confirm = QMessageBox.question(
            self, "Ускорить компьютер", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._score_before = _health_score()
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
        self._worker.cancelled.connect(self._optimize_cancelled)
        # Кнопка overlay реально прерывает операцию (между шагами).
        self._overlay.cancel.clicked.connect(self._worker.requestInterruption)
        self._worker.start()

    def _optimize_cancelled(self) -> None:
        self._overlay.finish("Отменено. Применённые шаги можно откатить в разделе «Бэкапы».")
        self.optimize_btn.setEnabled(True)

    def _step_backup(self):
        return backup.create_backup("quick", hives=["HKLM", "HKCU"])

    def _step_apply_safe(self):
        from app.modules.registry import RegistryModule

        mod = RegistryModule()
        ids = smart.pending_safe_tweak_ids(mod.scan())
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
        # Обновляем кольцо состояния и показываем динамику «было → стало».
        after = _health_score()
        self.ring.set_value(after)
        before = getattr(self, "_score_before", after)
        self.caption.setText(health.delta_text(before, after))

    def _optimize_failed(self, msg: str) -> None:
        self._overlay.finish(f"Не удалось завершить: {msg}")
        self.optimize_btn.setEnabled(True)
        Toast.show_message(self, f"Ошибка: {msg}", "error")
