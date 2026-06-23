"""Дизайн-токены приложения — единый источник истины.

Никаких «магических» цветов в коде: всё берётся отсюда. QSS-файлы
генерируются из этих токенов функцией build_qss().
"""
from __future__ import annotations


class Colors:
    # Фоны — многослойность глубины
    BG_VOID = "#080B14"
    BG_BASE = "#0D1117"
    BG_SURFACE = "#161B27"
    BG_ELEVATED = "#1E2535"
    BG_OVERLAY = "#252D42"

    # Акценты
    ACCENT_PRIMARY = "#6C63FF"
    ACCENT_SECONDARY = "#4FACFE"
    ACCENT_GLOW = "#6C63FF40"
    GRADIENT_START = "#6C63FF"
    GRADIENT_END = "#4FACFE"

    # Семантика
    SUCCESS = "#00D4AA"
    WARNING = "#FFB547"
    DANGER = "#FF5C8D"
    INFO = "#4FACFE"

    # Текст
    TEXT_PRIMARY = "#F0F2F8"
    TEXT_SECONDARY = "#8B92A5"
    TEXT_TERTIARY = "#4A5268"
    TEXT_ACCENT = "#6C63FF"

    # Границы
    BORDER_SUBTLE = "#1E2535"
    BORDER_DEFAULT = "#252D42"
    BORDER_ACCENT = "#6C63FF50"

    SELECTION = "#6C63FF25"


class ColorsLight:
    BG_VOID = "#E8EAF0"
    BG_BASE = "#F2F4F8"
    BG_SURFACE = "#FFFFFF"
    BG_ELEVATED = "#F8F9FC"
    BG_OVERLAY = "#EEF0F6"

    ACCENT_PRIMARY = "#5B52E8"
    ACCENT_SECONDARY = "#2E9FE8"
    ACCENT_GLOW = "#5B52E820"
    GRADIENT_START = "#5B52E8"
    GRADIENT_END = "#2E9FE8"

    SUCCESS = "#00B894"
    WARNING = "#E8A33D"
    DANGER = "#E84393"
    INFO = "#2E9FE8"

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

QLabel#Title {{ font-size: {Typography.SIZE_XL}px; font-weight: {Typography.WEIGHT_BOLD}; color: {c.TEXT_PRIMARY}; }}
QLabel#Subtitle {{ color: {c.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px; }}

/* Боковое меню и шапка */
#Sidebar {{ background-color: {c.BG_VOID}; }}
#Sidebar QPushButton {{
    text-align: left; padding: 10px 14px; border: none;
    border-radius: {Radius.MD}px; background: transparent; color: {c.TEXT_SECONDARY};
}}
#Sidebar QPushButton:hover {{ background-color: {c.BG_SURFACE}; color: {c.TEXT_PRIMARY}; }}
#Sidebar QPushButton:checked {{ background-color: {c.BG_ELEVATED}; color: {c.TEXT_PRIMARY}; font-weight: {Typography.WEIGHT_SEMIBOLD}; }}

#Header {{ background-color: {c.BG_BASE}; border-bottom: 1px solid {c.BORDER_SUBTLE}; }}
#Header QPushButton {{ padding: 6px 14px; border-radius: {Radius.FULL}px; color: {c.TEXT_SECONDARY}; background: transparent; }}
#Header QPushButton:checked {{ background-color: {c.ACCENT_PRIMARY}; color: #FFFFFF; font-weight: {Typography.WEIGHT_SEMIBOLD}; }}

#WorkArea {{ background-color: {c.BG_BASE}; }}

/* Карточки метрик */
#MetricCard {{ background-color: {c.BG_SURFACE}; border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.LG}px; padding: 14px; }}
#MetricValue {{ font-size: {Typography.SIZE_LG}px; font-weight: {Typography.WEIGHT_BOLD}; color: {c.TEXT_PRIMARY}; }}
#MetricLabel {{ color: {c.TEXT_SECONDARY}; font-size: {Typography.SIZE_SM}px; }}

/* Кнопки */
QPushButton#Primary {{
    background-color: {c.ACCENT_PRIMARY}; color: #FFFFFF; border: none;
    border-radius: {Radius.MD}px; padding: 10px 20px; font-weight: {Typography.WEIGHT_SEMIBOLD};
}}
QPushButton#Primary:hover {{ background-color: {c.ACCENT_SECONDARY}; }}
QPushButton {{
    background-color: {c.BG_ELEVATED}; color: {c.TEXT_PRIMARY};
    border: 1px solid {c.BORDER_DEFAULT}; border-radius: {Radius.MD}px; padding: 8px 16px;
}}
QPushButton:hover {{ background-color: {c.BG_OVERLAY}; border-color: {c.BORDER_ACCENT}; }}
QPushButton:disabled {{ color: {c.TEXT_TERTIARY}; }}

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
