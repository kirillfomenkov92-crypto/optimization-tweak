"""Toast-уведомление: всплывает в правом нижнем углу и само исчезает."""
from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from app.ui.styles.design_tokens import Colors, Radius, Typography

_KIND = {
    "success": Colors.SUCCESS,
    "warning": Colors.WARNING,
    "error": Colors.DANGER,
    "info": Colors.INFO,
}


class Toast(QFrame):
    def __init__(self, parent: QWidget, text: str, kind: str = "success") -> None:
        super().__init__(parent)
        color = _KIND.get(kind, Colors.INFO)
        self.setStyleSheet(
            f"background-color: {Colors.BG_ELEVATED}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-left: 3px solid {color}; border-radius: {Radius.MD}px;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: {Typography.SIZE_SM}px; border: none;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)
        self.adjustSize()

    @staticmethod
    def show_message(parent: QWidget, text: str, kind: str = "success", duration_ms: int = 3000) -> "Toast":
        toast = Toast(parent, text, kind)
        toast.setFixedWidth(320)
        toast.adjustSize()
        margin = 24
        x = parent.width() - toast.width() - margin
        y = parent.height() - toast.height() - margin
        toast.move(max(0, x), max(0, y))
        toast.show()
        toast.raise_()

        eff = QGraphicsOpacityEffect(toast)
        toast.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", toast)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        toast._anim = anim  # удержать ссылку

        def fade_out():
            out = QPropertyAnimation(eff, b"opacity", toast)
            out.setDuration(300)
            out.setStartValue(1.0)
            out.setEndValue(0.0)
            out.finished.connect(toast.deleteLater)
            out.start()
            toast._anim_out = out

        QTimer.singleShot(duration_ms, fade_out)
        return toast
