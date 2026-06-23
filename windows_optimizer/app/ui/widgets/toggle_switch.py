"""Кастомный тумблер (Toggle Switch), рисуется через QPainter, с анимацией."""
from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from app.ui.styles.design_tokens import Colors


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._checked = checked
        self._pos = 1.0 if checked else 0.0
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"pos_ratio", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # анимируемое свойство (0..1)
    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, v: float) -> None:
        self._pos = v
        self.update()

    pos_ratio = pyqtProperty(float, fget=_get_pos, fset=_set_pos)

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

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        # трек
        on = QColor(Colors.ACCENT_PRIMARY)
        off = QColor(Colors.BG_ELEVATED)
        track = QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
        )
        p.setBrush(track)
        p.setPen(QColor(Colors.BORDER_DEFAULT))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        # ползунок
        d = h - 6
        x = 3 + self._pos * (w - d - 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF") if self._pos > 0.5 else QColor(Colors.TEXT_TERTIARY))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()
