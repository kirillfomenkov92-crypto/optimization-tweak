"""Главное окно: левая навигация + правая рабочая область (QStackedWidget)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QStatusBar,
    QVBoxLayout, QWidget, QMainWindow, QScrollArea,
)

from app.ui.dashboard import Dashboard
from app.ui.scan_page import ScanPage
from app.ui.backups_page import BackupsPage
from app.ui.about_page import AboutPage
from app.ui.settings_page import SettingsPage
from app.ui.history_panel import HistoryPanel
from app.ui.debloat_panel import DebloatPanel
from app.ui.widgets.tweak_panel import TweakPanel
from app.ui.widgets.disk_panel import DiskPanel
from app.ui.widgets.services_panel import ServicesPanel
from app.ui.widgets.action_panel import ActionPanel
from app.modules.registry import RegistryModule
from app.modules.startup import StartupModule
from app.modules.services import ServicesModule
from app.modules.disk import DiskModule
from app.modules.privacy import PrivacyModule
from app.modules.network import NetworkModule
from app.modules.power import PowerModule
from app.modules.memory import MemoryModule
from app.modules.gaming import GamingModule
from app.modules.gpu import GpuModule
from app.modules.cpu import CpuModule
from app.modules.security import SecurityModule

from app.utils.resources import resource_path
from app.core.logger import get_logger

_log = get_logger()

_STYLES_DIR = resource_path("app", "ui", "styles")
_STYLE = _STYLES_DIR / "dark_theme.qss"
_ICON = resource_path("resources", "icons", "app.ico")


class _ModulePlaceholder(QWidget):
    """Простая панель модуля на этапе фундамента: показывает результат scan()."""

    def __init__(self, title: str, rows_fn) -> None:
        super().__init__()
        self._rows_fn = rows_fn
        self._loaded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        head = QLabel(title)
        head.setObjectName("Title")
        layout.addWidget(head)
        area = QScrollArea()
        area.setWidgetResizable(True)
        self._inner = QWidget()
        self._inner_l = QVBoxLayout(self._inner)
        self._inner_l.addWidget(QLabel("Загрузка…"))
        area.setWidget(self._inner)
        layout.addWidget(area)

    def showEvent(self, event) -> None:  # ленивая загрузка при первом показе
        super().showEvent(event)
        if self._loaded:
            return
        self._loaded = True
        for i in reversed(range(self._inner_l.count())):
            w = self._inner_l.itemAt(i).widget()
            if w:
                w.setParent(None)
        try:
            rows = self._rows_fn()
        except Exception as ex:  # pragma: no cover
            rows = [f"ошибка: {ex}"]
        if not rows:
            self._inner_l.addWidget(QLabel("Нет данных (доступно на Windows)."))
        for r in rows:
            lbl = QLabel("• " + r)
            lbl.setWordWrap(True)
            self._inner_l.addWidget(lbl)
        self._inner_l.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Windows Optimizer Pro")
        self.setMinimumSize(1100, 700)
        if _ICON.exists():
            self.setWindowIcon(QIcon(str(_ICON)))

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_header())

        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer.addWidget(body, 1)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(self.sidebar)
        side_l.setContentsMargins(12, 16, 12, 16)
        side_l.setSpacing(6)

        self.stack = QStackedWidget()
        self.stack.setObjectName("WorkArea")

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for title, widget in self._pages():
            self._add_page(side_l, title, widget)
        side_l.addStretch(1)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Откройте «Сканирование», чтобы безопасно оценить систему, или зайдите в нужный раздел.")

        if self._btn_group.buttons():
            self._btn_group.buttons()[0].setChecked(True)
            self.stack.setCurrentIndex(0)

        self.stack.currentChanged.connect(self._fade_in)
        self._apply_style()
        self._setup_tray()

    def _setup_tray(self) -> None:
        try:
            from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

            if not QSystemTrayIcon.isSystemTrayAvailable():
                return
            from app.ui.dashboard import _health_score

            self._tray = QSystemTrayIcon(self._tray_icon_for(_health_score()), self)
            self._tray.setToolTip("Windows Optimizer Pro")
            menu = QMenu()
            menu.addAction("Открыть").triggered.connect(self.showNormal)
            menu.addAction("Выход").triggered.connect(QApplication.quit)
            self._tray.setContextMenu(menu)
            self._tray.activated.connect(lambda _r: self.showNormal())
            self._tray.show()
        except Exception as e:
            _log.debug("Иконка в трее недоступна: %s", e)

    def _tray_icon_for(self, score: int):
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap

        color = "#00D4AA" if score > 70 else ("#FFB547" if score > 40 else "#FF5C8D")
        pm = QPixmap(32, 32)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(4, 4, 24, 24)
        p.end()
        return QIcon(pm)

    def closeEvent(self, event) -> None:
        # Корректно завершаем фоновые потоки, чтобы не было
        # «QThread: Destroyed while thread is still running».
        try:
            from app.ui.widgets.worker import stop_all
            stop_all()
        except Exception as e:
            _log.debug("Остановка воркеров при закрытии не удалась: %s", e)
        super().closeEvent(event)

    def _fade_in(self, index: int) -> None:
        """Плавное появление новой панели при переключении раздела."""
        try:
            from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
            from PyQt6.QtWidgets import QGraphicsOpacityEffect

            widget = self.stack.widget(index)
            if widget is None:
                return
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
            anim = QPropertyAnimation(eff, b"opacity", self)
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start()
            self._fade_anim = anim  # удержать ссылку
        except Exception as e:
            _log.debug("Анимация перехода не запущена: %s", e)

    def _pages(self) -> List[Tuple[str, QWidget]]:
        reg = RegistryModule()
        startup = StartupModule()
        privacy = PrivacyModule()
        network = NetworkModule()
        power = PowerModule()
        memory = MemoryModule()

        gaming = GamingModule()
        gpu = GpuModule()
        cpu = CpuModule()
        security = SecurityModule()

        # Ленивые поставщики строк для заглушек (scan() выполнится при первом показе,
        # а не на старте окна — иначе UI замирал бы на WMI/PowerShell/обходе диска).
        _impact_icon = {"high": "🔴 Высокое влияние", "medium": "🟡 Среднее влияние",
                        "low": "🟢 Низкое влияние"}
        startup_rows = lambda: [
            f"{_impact_icon.get(r.get('impact','medium'),'')} · {r['name']} — {r.get('source','')}"
            for r in startup.scan()
        ]
        gpu_rows = lambda: [f"{r['item']}: {r['value']}" for r in gpu.scan()]
        security_rows = lambda: [f"{r['item']}: {r['value']}" for r in security.scan()]

        # Обёртки «применить рекомендованное» для панелей действий.
        apply_memory = lambda: {"LargeSystemCache": memory.set_large_system_cache(0)}
        apply_cpu = lambda: {"Win32PrioritySeparation (передний план)": cpu.set_priority_separation(0x2A)}
        apply_privacy = lambda: privacy.apply_privacy([t["id"] for t in privacy.privacy_tweaks()])

        return [
            ("🏠 Дашборд", Dashboard()),
            ("🔍 Сканирование", ScanPage()),
            ("🚀 Автозагрузка", _ModulePlaceholder("Автозагрузка", startup_rows)),
            ("⚙️ Службы", ServicesPanel()),
            ("💾 Очистка диска", DiskPanel()),
            ("🌐 Сеть", ActionPanel("Сеть (TCP/IP)", network.scan, network.apply_tcp_tweaks,
                                     "Применить TCP-твики",
                                     hint="DNS-профили и ping доступны в модуле network.")),
            ("⚡ Питание", ActionPanel("Питание", power.scan, power.enable_high_performance,
                                       "Включить «Высокая производительность»",
                                       backup_before=False)),
            ("🧠 Память", ActionPanel("Память", memory.scan, apply_memory,
                                       "Применить (LargeSystemCache=приложения)")),
            ("🎮 Игры", ActionPanel("Игровая оптимизация", gaming.scan, gaming.apply_all,
                                     "Применить игровые твики")),
            ("🖥️ GPU", _ModulePlaceholder("GPU", gpu_rows)),
            ("🖧 Процессор", ActionPanel("Процессор", cpu.scan, apply_cpu,
                                          "Приоритет активному окну")),
            ("🔒 Безопасность", _ModulePlaceholder("Безопасность", security_rows)),
            ("🕵️ Приватность", ActionPanel("Приватность", privacy.scan, apply_privacy,
                                            "Применить твики приватности")),
            ("🧹 Деблоат", DebloatPanel()),
            ("📝 Реестр", TweakPanel(reg, "Реестр — твики")),
            ("📋 История", HistoryPanel()),
            ("🗄️ Бэкапы", BackupsPage()),
            ("⚙️ Настройки", SettingsPage(self.set_theme, getattr(self, "_theme", "dark"))),
            ("❓ О программе", AboutPage()),
        ]

    def _add_page(self, side_layout: QVBoxLayout, title: str, widget: QWidget) -> None:
        idx = self.stack.addWidget(widget)
        btn = QPushButton(title)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _=False, i=idx: self.stack.setCurrentIndex(i))
        self._btn_group.addButton(btn)
        side_layout.addWidget(btn)

    def _apply_style(self) -> None:
        self.set_theme(getattr(self, "_theme", "dark"))

    def set_theme(self, name: str) -> None:
        """Переключить тему ('dark'|'light') без перезапуска.

        QSS генерируется из дизайн-токенов (единый источник). При сбое —
        фолбэк на статический .qss-файл.
        """
        self._theme = name if name in ("dark", "light") else "dark"
        try:
            from app.ui.styles.design_tokens import Colors, ColorsLight, build_qss

            palette = Colors if self._theme == "dark" else ColorsLight
            self.setStyleSheet(build_qss(palette))
            return
        except Exception as e:
            _log.debug("Программная тема не применена, пробую .qss-файл: %s", e)
        qss = _STYLES_DIR / f"{self._theme}_theme.qss"
        try:
            if qss.exists():
                self.setStyleSheet(qss.read_text(encoding="utf-8"))
        except Exception as e:
            _log.debug("Не удалось применить тему из %s: %s", qss, e)

    def _build_header(self) -> QWidget:
        from app.ui.modes import AppMode, mode_manager

        bar = QWidget()
        bar.setObjectName("Header")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        title = QLabel("Windows Optimizer Pro")
        title.setObjectName("Title")
        lay.addWidget(title)
        lay.addStretch(1)

        self._btn_simple = QPushButton("Простой режим")
        self._btn_advanced = QPushButton("Расширенный режим")
        for b in (self._btn_simple, self._btn_advanced):
            b.setCheckable(True)
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self._btn_simple)
        grp.addButton(self._btn_advanced)
        is_simple = mode_manager().is_simple()
        self._btn_simple.setChecked(is_simple)
        self._btn_advanced.setChecked(not is_simple)
        self._btn_simple.clicked.connect(lambda: self._on_mode_change(AppMode.SIMPLE))
        self._btn_advanced.clicked.connect(lambda: self._on_mode_change(AppMode.ADVANCED))
        lay.addWidget(self._btn_simple)
        lay.addWidget(self._btn_advanced)
        return bar

    def _on_mode_change(self, mode) -> None:
        from app.ui.modes import mode_manager

        mode_manager().set_mode(mode)
        # Обновляем панели, умеющие refresh(), чтобы фильтр режима применился сразу.
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if hasattr(w, "refresh"):
                try:
                    w.refresh()
                except Exception as e:
                    _log.debug("Обновление панели %r не удалось: %s", w, e)
        simple = mode_manager().is_simple()
        self.statusBar().showMessage(
            "Простой режим: показаны только понятные безопасные улучшения."
            if simple else "Расширенный режим: доступны все параметры и технические детали."
        )
