"""Кастомный тумблер (Toggle Switch) на QPainter с анимацией и «искрой».

При включении проигрывается короткая электрическая вспышка вокруг ползунка
(signature-анимация приложения) — энергично, но сдержанно.
"""
from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from app.ui.styles.design_tokens import active


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self._spark = 0.0  # 0..1 прогресс вспышки
        # Запас по краям, чтобы вспышка/свечение не обрезались виджетом.
        self.setFixedSize(60, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"pos_ratio", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)  # лёгкий «пружинный» доводчик

        self._spark_anim = QPropertyAnimation(self, b"spark", self)
        self._spark_anim.setDuration(420)
        self._spark_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- анимируемые свойства ----
    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    pos_ratio = pyqtProperty(float, fget=_get_pos, fset=_set_pos)

    def _get_spark(self) -> float:
        return self._spark

    def _set_spark(self, v: float) -> None:
        self._spark = v
        self.update()

    spark = pyqtProperty(float, fget=_get_spark, fset=_set_spark)

    # ---- состояние ----
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if value == self._checked:
            return
        self._checked = value
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if value else 0.0)
        self._anim.start()
        if value:                      # «молния» только при включении
            self._spark_anim.stop()
            self._spark = 0.0
            self._spark_anim.setStartValue(0.0)
            self._spark_anim.setEndValue(1.0)
            self._spark_anim.start()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    # ---- отрисовка ----
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = active()
        # Поле трека (с отступом под свечение).
        pad = 8
        w = self.width() - pad * 2
        h = self.height() - pad * 2

        on = QColor(c.ACCENT_PRIMARY)
        off = QColor(c.BG_ELEVATED)
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        p.setBrush(track)
        p.setPen(QColor(c.BORDER_DEFAULT))
        p.drawRoundedRect(QRectF(pad, pad, w, h), h / 2, h / 2)

        # Ползунок.
        d = h - 6
        x = pad + 3 + self._pos * (w - d - 6)
        cx, cy = x + d / 2, pad + 3 + d / 2

        # Вспышка-«молния» вокруг ползунка при включении.
        if self._spark > 0.0:
            self._draw_spark(p, cx, cy, d)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF") if self._pos > 0.5 else QColor(c.TEXT_TERTIARY))
        p.drawEllipse(QRectF(x, pad + 3, d, d))
        p.end()

    def _draw_spark(self, p: QPainter, cx: float, cy: float, d: float) -> None:
        """Радиальное свечение + короткие лучи (электрическая вспышка)."""
        s = self._spark
        alpha = int(220 * (1.0 - s))          # затухает к концу
        accent = QColor(active().ACCENT_SECONDARY)

        # Мягкое расширяющееся свечение.
        radius = d * (0.7 + s * 1.1)
        grad = QRadialGradient(QPointF(cx, cy), radius)
        glow = QColor(accent); glow.setAlpha(int(alpha * 0.5))
        edge = QColor(accent); edge.setAlpha(0)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, edge)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        # Короткие лучи-«искры», разлетающиеся наружу.
        pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), alpha))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        r0 = d * 0.55 + s * d * 0.5
        r1 = r0 + d * 0.45 * (1.0 - s)
        for i in range(8):
            ang = math.pi / 4 * i + s * 0.6
            dx, dy = math.cos(ang), math.sin(ang)
            p.drawLine(QPointF(cx + dx * r0, cy + dy * r0),
                       QPointF(cx + dx * r1, cy + dy * r1))
