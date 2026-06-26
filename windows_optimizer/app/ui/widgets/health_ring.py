"""Кольцевой индикатор «Состояние системы» (Health Score).

Толстая градиентная дуга с мягким свечением, крупное число и подпись «/100».
Анимируется плавно при изменении значения.
"""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import (
    QColor, QConicalGradient, QFont, QPainter, QPen,
)
from PyQt6.QtWidgets import QWidget

from app.ui.styles.design_tokens import Typography, active


def _score_colors(value: int):
    c = active()
    if value <= 40:
        return c.DANGER, c.WARNING
    if value <= 70:
        return c.WARNING, c.ACCENT_SECONDARY
    return c.ACCENT_PRIMARY, c.SUCCESS


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
        self._pulse = 0.0  # 0..1 прогресс пульса при росте балла
        self.setMinimumSize(190, 190)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(1100)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self._pulse_anim = QVariantAnimation(self)
        self._pulse_anim.setDuration(900)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pulse_anim.valueChanged.connect(self._on_pulse)
        self.set_value(value)

    def _on_anim(self, v) -> None:
        self._value = int(v)
        self.update()

    def _on_pulse(self, v) -> None:
        self._pulse = float(v)
        self.update()

    def set_value(self, target: int) -> None:
        target = max(0, min(100, int(target)))
        # Пульс — только при росте оценки (после оптимизации).
        if target > self._value:
            self._pulse_anim.stop()
            self._pulse_anim.setStartValue(0.0)
            self._pulse_anim.setEndValue(1.0)
            self._pulse_anim.start()
        self._target = target
        self._anim.stop()
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(self._target)
        self._anim.start()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        thickness = 12
        margin = 16
        rect = QRectF((self.width() - side) / 2 + margin, (self.height() - side) / 2 + margin,
                      side - 2 * margin, side - 2 * margin)
        center = rect.center()
        c = active()
        start, end = _score_colors(self._value)

        # Пульс-волна при росте балла — расходится наружу и затухает.
        if 0.0 < self._pulse < 1.0:
            grow = (rect.width() * 0.10) * self._pulse
            pr = rect.adjusted(-grow, -grow, grow, grow)
            pc = QColor(end); pc.setAlpha(int(120 * (1.0 - self._pulse)))
            p.setPen(QPen(pc, max(2.0, thickness * (1.0 - self._pulse)),
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(pr, 0, 360 * 16)

        # Фоновое кольцо — тонкое, приглушённое.
        p.setPen(QPen(QColor(c.BG_ELEVATED), thickness,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, 0, 360 * 16)

        span = self._value / 100.0
        if span > 0:
            # Мягкое свечение под дугой (несколько полупрозрачных проходов).
            glow = QColor(end)
            for w, a in ((thickness + 12, 26), (thickness + 6, 40)):
                gp = QColor(glow); gp.setAlpha(a)
                p.setPen(QPen(gp, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(rect, 90 * 16, -int(360 * 16 * span))

            # Градиентная дуга прогресса.
            grad = QConicalGradient(center, 90)
            grad.setColorAt(0.0, QColor(start))
            grad.setColorAt(min(0.999, span), QColor(end))
            grad.setColorAt(1.0, QColor(start))
            p.setPen(QPen(grad, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 90 * 16, -int(360 * 16 * span))

        # Число — крупное, лёгкое.
        p.setPen(QColor(c.TEXT_PRIMARY))
        fnum = QFont(Typography.FONT_TEXT.split(",")[0].strip('"'))
        fnum.setPixelSize(int(rect.height() * 0.34))
        fnum.setWeight(QFont.Weight.DemiBold)
        p.setFont(fnum)
        num_rect = QRectF(rect.left(), rect.top() + rect.height() * 0.12, rect.width(), rect.height() * 0.55)
        p.drawText(num_rect, Qt.AlignmentFlag.AlignCenter, str(self._value))

        # Подпись «/100» — мелко, под числом.
        p.setPen(QColor(c.TEXT_SECONDARY))
        fsub = QFont(Typography.FONT_TEXT.split(",")[0].strip('"'))
        fsub.setPixelSize(int(rect.height() * 0.11))
        fsub.setWeight(QFont.Weight.Medium)
        p.setFont(fsub)
        sub_rect = QRectF(rect.left(), rect.top() + rect.height() * 0.58, rect.width(), rect.height() * 0.22)
        p.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, "из 100")
        p.end()
