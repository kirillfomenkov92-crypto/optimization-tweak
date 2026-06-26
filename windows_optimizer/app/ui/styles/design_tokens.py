"""Дизайн-токены приложения — единый источник истины.

Никаких «магических» цветов в коде: всё берётся отсюда. QSS-файлы
генерируются из этих токенов функцией build_qss().
"""
from __future__ import annotations


class Colors:
    # Фоны — глубокий «космос» с лёгким сине-фиолетовым подтоном (2100/неон)
    BG_VOID = "#04060E"
    BG_BASE = "#080B16"
    BG_SURFACE = "#0E1322"
    BG_ELEVATED = "#161D33"
    BG_OVERLAY = "#1F2945"

    # Акценты — электрик-виолет → неон-циан (голографический градиент)
    ACCENT_PRIMARY = "#7C5CFF"
    ACCENT_SECONDARY = "#22D3FD"
    ACCENT_GLOW = "#7C5CFF55"
    GRADIENT_START = "#7C5CFF"
    GRADIENT_END = "#22D3FD"

    # Семантика — неоновые
    SUCCESS = "#2BF5C8"
    WARNING = "#FFC24B"
    DANGER = "#FF5C8D"
    INFO = "#22D3FD"

    # Текст
    TEXT_PRIMARY = "#EEF2FF"
    TEXT_SECONDARY = "#8A93B2"
    TEXT_TERTIARY = "#4C5780"
    TEXT_ACCENT = "#9B8CFF"

    # Границы
    BORDER_SUBTLE = "#161D33"
    BORDER_DEFAULT = "#222C49"
    BORDER_ACCENT = "#7C5CFF66"

    SELECTION = "#7C5CFF2E"


class ColorsLight:
    BG_VOID = "#E8EAF0"
    BG_BASE = "#F2F4F8"
    BG_SURFACE = "#FFFFFF"
    BG_ELEVATED = "#F8F9FC"
    BG_OVERLAY = "#EEF0F6"

    ACCENT_PRIMARY = "#6A4CF0"
    ACCENT_SECONDARY = "#0FB8E6"
    ACCENT_GLOW = "#6A4CF022"
    GRADIENT_START = "#6A4CF0"
    GRADIENT_END = "#0FB8E6"

    SUCCESS = "#00B894"
    WARNING = "#E8A33D"
    DANGER = "#E84393"
    INFO = "#0FB8E6"

    TEXT_PRIMARY = "#0D1117"
    TEXT_SECONDARY = "#5A6273"
    TEXT_TERTIARY = "#9AA0B0"
    TEXT_ACCENT = "#5B52E8"

    BORDER_SUBTLE = "#E8EAF0"
    BORDER_DEFAULT = "#D8DCE8"
    BORDER_ACCENT = "#5B52E840"

    SELECTION = "#5B52E820"


class Typography:
    FONT_TEXT = '"Segoe UI Variable Text", "Segoe UI", "Noto Sans", sans-serif'
    FONT_MONO = '"Cascadia Code", "Consolas", monospace'
    SIZE_XS = 10
    SIZE_SM = 12
    SIZE_BASE = 14
    SIZE_MD = 16
    SIZE_LG = 20
    SIZE_XL = 28
    SIZE_2XL = 38
    SIZE_3XL = 56
    WEIGHT_REGULAR = 400
    WEIGHT_MEDIUM = 500
    WEIGHT_SEMIBOLD = 600
    WEIGHT_BOLD = 700


class Spacing:
    XS, SM, MD, LG, XL, XXL, XXXL = 4, 8, 12, 16, 24, 32, 48


class Radius:
    SM, MD, LG, XL, FULL = 6, 10, 14, 20, 999


# Активная палитра — чтобы виджеты, рисующие через QPainter (кольцо и т.п.),
# брали цвета текущей темы, а не жёстко тёмной. Обновляется в MainWindow.set_theme.
_ACTIVE = Colors


def set_active(c) -> None:
    global _ACTIVE
    _ACTIVE = c


def active():
    return _ACTIVE


def build_qss(c) -> str:
    """Собрать полный QSS из набора цветов c (Colors или ColorsLight)."""
    return f"""
QWidget {{
    background-color: {c.BG_BASE};
    color: {c.TEXT_PRIMARY};
    font-family: {Typography.FONT_TEXT};
    font-size: {Typography.SIZE_BASE}px;
    border: none;
    outline: none;
}}

/* Подписи прозрачны, иначе на карточках (светлый фон) появляются тёмные полосы. */
QLabel {{ background: transparent; }}
QLabel#Title {{ font-size: {Typography.SIZE_XL}px; font-weight: {Typography.WEIGHT_BOLD}; color: {c.TEXT_PRIMARY}; }}
QLabel#CardTitle {{ font-size: {Typography.SIZE_MD}px; font-weight: {Typography.WEIGHT_SEMIBOLD}; color: {c.TEXT_PRIMARY}; }}
QLabel#Subtitle {{ color: {c.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px; }}

/* Боковое меню и шапка */
#Sidebar {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {c.BG_VOID}, stop:1 {c.BG_BASE});
    border-right: 1px solid {c.BORDER_SUBTLE};
}}
#Sidebar QPushButton {{
    text-align: left; padding: 10px 14px; border: none;
    border-radius: {Radius.MD}px; background: transparent; color: {c.TEXT_SECONDARY};
}}
#Sidebar QPushButton:hover {{ background-color: {c.BG_SURFACE}; color: {c.TEXT_PRIMARY}; }}
#Sidebar QPushButton:checked {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c.SELECTION}, stop:1 transparent);
    border-left: 2px solid {c.ACCENT_SECONDARY};
    color: {c.TEXT_PRIMARY}; font-weight: {Typography.WEIGHT_SEMIBOLD};
}}

#Header {{ background-color: {c.BG_BASE}; border-bottom: 1px solid {c.BORDER_SUBTLE}; }}
#Header QPushButton {{ padding: 6px 14px; border-radius: {Radius.FULL}px; color: {c.TEXT_SECONDARY}; background: transparent; }}
#Header QPushButton:checked {{ background-color: {c.ACCENT_PRIMARY}; color: #FFFFFF; font-weight: {Typography.WEIGHT_SEMIBOLD}; }}

#WorkArea {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {c.BG_BASE}, stop:0.55 {c.BG_VOID}, stop:1 {c.BG_BASE});
}}

/* Строки улучшений */
#TweakRow {{ background-color: transparent; border-radius: {Radius.MD}px; }}
#TweakRow:hover {{ background-color: {c.BG_SURFACE}; }}

/* Карточки метрик — «стекло» с лёгким градиентом и акцентной кромкой */
#MetricCard {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c.BG_SURFACE}, stop:1 {c.BG_ELEVATED});
    border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.XL}px; padding: 22px 24px;
}}
#MetricValue {{ font-size: {Typography.SIZE_XL}px; font-weight: {Typography.WEIGHT_SEMIBOLD}; color: {c.TEXT_PRIMARY}; }}
#MetricLabel {{ color: {c.TEXT_TERTIARY}; font-size: {Typography.SIZE_XS}px; font-weight: {Typography.WEIGHT_SEMIBOLD}; }}

/* Кнопки */
QPushButton#Primary {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c.GRADIENT_START}, stop:1 {c.GRADIENT_END});
    color: #FFFFFF; border: none;
    border-radius: {Radius.MD}px; padding: 10px 22px; font-weight: {Typography.WEIGHT_SEMIBOLD};
}}
QPushButton#Primary:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c.ACCENT_SECONDARY}, stop:1 {c.GRADIENT_END});
}}
QPushButton#Primary:disabled {{ background: {c.BG_OVERLAY}; color: {c.TEXT_TERTIARY}; }}
QPushButton#Danger {{
    background: transparent; color: {c.DANGER};
    border: 1px solid {c.DANGER}; border-radius: {Radius.MD}px; padding: 8px 18px;
    font-weight: {Typography.WEIGHT_MEDIUM};
}}
QPushButton#Danger:hover {{ background: {c.DANGER}; color: #FFFFFF; }}
QPushButton {{
    background-color: {c.BG_ELEVATED}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px; padding: 8px 16px;
}}
QPushButton:hover {{ background-color: {c.BG_OVERLAY}; border-color: {c.BORDER_ACCENT}; }}
QPushButton:disabled {{ color: {c.TEXT_TERTIARY}; }}
/* Видимый фокус с клавиатуры (доступность). */
QPushButton:focus {{ border: 2px solid {c.ACCENT_SECONDARY}; }}
#Sidebar QPushButton:focus {{ border: none; border-left: 3px solid {c.ACCENT_SECONDARY}; }}

/* Карточки (профили деблоата и т.п.) — стеклянные */
#Card {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c.BG_SURFACE}, stop:1 {c.BG_ELEVATED});
    border: 1px solid {c.BORDER_DEFAULT};
    border-radius: {Radius.LG}px; padding: 18px;
}}
#Card:hover {{ border: 1px solid {c.ACCENT_SECONDARY}; }}

/* Таблицы / списки / деревья */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {c.BG_SURFACE}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.LG}px;
    gridline-color: {c.BORDER_SUBTLE};
}}
QHeaderView::section {{ background-color: {c.BG_ELEVATED}; color: {c.TEXT_SECONDARY}; border: none; padding: 8px; }}
QTableWidget::item:selected, QListWidget::item:selected, QTreeWidget::item:selected {{
    background-color: {c.SELECTION}; color: {c.TEXT_PRIMARY};
}}

/* Поля ввода */
QComboBox, QLineEdit, QSpinBox {{
    background: {c.BG_SURFACE}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px;
    padding: 8px 12px; color: {c.TEXT_PRIMARY}; min-height: 20px;
}}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color: {c.BORDER_ACCENT}; }}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{ border-color: {c.ACCENT_PRIMARY}; }}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {c.BG_ELEVATED}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px;
    selection-background-color: {c.SELECTION}; selection-color: {c.TEXT_PRIMARY}; outline: none;
}}

/* Чекбоксы */
QCheckBox {{ spacing: 10px; color: {c.TEXT_PRIMARY}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {c.BORDER_DEFAULT}; background: {c.BG_SURFACE}; }}
QCheckBox::indicator:hover {{ border-color: {c.ACCENT_PRIMARY}; }}
QCheckBox::indicator:checked {{ background: {c.ACCENT_PRIMARY}; border-color: {c.ACCENT_PRIMARY}; }}

/* Прогресс */
QProgressBar {{ background: {c.BG_ELEVATED}; border-radius: {Radius.FULL}px; height: 6px; text-align: center; color: {c.TEXT_SECONDARY}; }}
QProgressBar::chunk {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {c.GRADIENT_START}, stop:1 {c.GRADIENT_END}); border-radius: {Radius.FULL}px; }}

/* Статусбар / меню / тултип */
QStatusBar {{ background-color: {c.BG_SURFACE}; color: {c.TEXT_SECONDARY}; }}
QToolTip {{ background: {c.BG_ELEVATED}; color: {c.TEXT_PRIMARY}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px; padding: 8px 12px; font-size: {Typography.SIZE_SM}px; }}
QMenu {{ background: {c.BG_ELEVATED}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px; padding: 6px; }}
QMenu::item {{ padding: 8px 16px; border-radius: 8px; color: {c.TEXT_PRIMARY}; }}
QMenu::item:selected {{ background: {c.SELECTION}; }}

/* Скроллбары */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c.BORDER_DEFAULT}; border-radius: 4px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: {c.TEXT_TERTIARY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{ background: {c.BORDER_DEFAULT}; border-radius: 4px; min-width: 40px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""
