"""Страница «О программе»."""
from __future__ import annotations

import platform
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

_ABOUT = """
<h2>Windows Optimizer Pro</h2>
<p>Версия 1.0 · PyQt6</p>
<p>Десктопное приложение для оптимизации Windows 10/11: автозагрузка, службы,
реестр, очистка диска, сеть, питание, память, игры, GPU, CPU, безопасность,
приватность. Все изменения обратимы, перед применением создаётся бэкап.</p>
<p><b>Принципы:</b> безопасность прежде всего · прозрачность изменений ·
полный откат · защита критичных компонентов системы.</p>
<p style="color:#a8a8b3">Запускать от имени администратора. Первый запуск —
через «Сканирование», чтобы оценить состояние без изменений.</p>
"""


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        body = QLabel(_ABOUT)
        body.setObjectName("Subtitle")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(body)
        env = QLabel(f"Python {platform.python_version()} · {platform.system()} {platform.release()} · {sys.platform}")
        env.setObjectName("Subtitle")
        root.addWidget(env)
        root.addStretch(1)
