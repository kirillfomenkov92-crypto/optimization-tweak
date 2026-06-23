"""Кольцевой индикатор «Состояние системы» (Health Score) с анимацией."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from app.ui.styles.design_tokens import Colors, Typography


def _score_colors(value: int):
    if value <= 40:
        return Colors.DANGER, Colors.WARNING
    if value <= 70:
        return Colors.WARNING, Colors.ACCENT_PRIMARY
    return Colors.ACCENT_PRIMARY, Colors.SUCCESS


def score_caption(value: int) -> str:
    if value <= 40:
        return "Система работает медленно"
    if value <= 70:
        return "Есть что улучшить"
    if value <= 89:
        return "Система в порядке"
    return "Система оптимизирована"


class HealthScoreRing(QWidget):
    def __init__(self, value: int = 0, parent=None) -> None:
        super().__init__(parent)
        self._value = 0
        self._target = value
        self.setMinimumSize(180, 180)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.set_value(value)

    def _on_anim(self, v) -> None:
        self._value = int(v)
        self.update()

    def set_value(self, target: int) -> None:
        self._target = max(0, min(100, int(target)))
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(self._target)
        self._anim.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = 14
        rect = QRectF((self.width() - side) / 2 + margin, (self.height() - side) / 2 + margin,
                      side - 2 * margin, side - 2 * margin)

        # фоновое кольцо
        bg_pen = QPen(QColor(Colors.BG_ELEVATED), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(bg_pen)
        p.drawArc(rect, 0, 360 * 16)

        # прогресс
        start, end = _score_colors(self._value)
        pen = QPen(QColor(start), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        span = int(360 * 16 * (self._value / 100.0))
        p.drawArc(rect, 90 * 16, -span)  # сверху по часовой

        # число
        p.setPen(QColor(Colors.TEXT_PRIMARY))
        f = QFont()
        f.setPointSize(int(Typography.SIZE_2XL / 1.6))
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self._value))
        p.end()
