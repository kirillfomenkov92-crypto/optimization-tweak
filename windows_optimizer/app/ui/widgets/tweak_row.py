"""Строка одного улучшения: точка риска, название, польза, тумблер, детали."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.ui.styles.design_tokens import Colors, Typography
from app.ui.widgets.risk_badge import RiskLevel
from app.ui.widgets.toggle_switch import ToggleSwitch

_STATUS_RU = {"applied": "включено", "default": "выключено",
              "modified": "изменено вручную", "unknown": "—"}


class TweakRow(QFrame):
    def __init__(self, data: Dict, advanced: bool = False,
                 on_toggle: Optional[Callable[[str, bool], None]] = None) -> None:
        super().__init__()
        self.tweak_id = data.get("id", "")
        self._on_toggle = on_toggle
        self.setObjectName("TweakRow")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(12)

        # точка риска
        _id, _text, color, tip = RiskLevel.from_str(data.get("risk_level") or data.get("risk", "low"))
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        dot.setToolTip(tip)
        lay.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)

        # текстовая часть
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(data.get("friendly_name") or data.get("name", ""))
        name.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: {Typography.WEIGHT_MEDIUM};")
        benefit = QLabel(data.get("user_benefit", ""))
        benefit.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px;")
        benefit.setWordWrap(True)
        text.addWidget(name)
        text.addWidget(benefit)
        if advanced and data.get("registry_path_hint"):
            mono = QLabel(data["registry_path_hint"])
            mono.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-family: {Typography.FONT_MONO}; font-size: {Typography.SIZE_XS}px;")
            text.addWidget(mono)
        lay.addLayout(text, 1)

        # тумблер + статус
        right = QVBoxLayout()
        right.setSpacing(2)
        self.toggle = ToggleSwitch(checked=(data.get("status") == "applied"))
        if self._on_toggle:
            self.toggle.toggled.connect(lambda v: self._on_toggle(self.tweak_id, v))
        self.status_lbl = QLabel(_STATUS_RU.get(data.get("status", ""), ""))
        self.status_lbl.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.status_lbl)
        lay.addLayout(right, 0)

        if data.get("reboot_required"):
            self.setToolTip("После применения потребуется перезагрузка.")

    def is_on(self) -> bool:
        return self.toggle.isChecked()
