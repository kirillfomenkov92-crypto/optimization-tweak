"""Точка входа Windows Optimizer Pro.

Проверяет права администратора (предлагает повышение), затем поднимает
GUI на PyQt6. На не-Windows запускается в ограниченном режиме (для
разработки/проверки импорта).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Гарантируем, что корень проекта в sys.path при запуске из любого места.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.logger import get_logger
from app.utils.admin import is_admin, run_as_admin, IS_WINDOWS

log = get_logger()


def main() -> int:
    log.info("Запуск Windows Optimizer Pro (admin=%s, windows=%s)", is_admin(), IS_WINDOWS)

    # На Windows без прав администратора — предлагаем перезапуск с повышением.
    if IS_WINDOWS and not is_admin():
        if run_as_admin():
            log.info("Запущена копия с повышением прав, завершаю текущий процесс.")
            return 0
        log.warning("Работаем без прав администратора — изменения системы будут недоступны.")

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QIcon
    except Exception as e:  # pragma: no cover
        log.error("PyQt6 не установлен: %s", e)
        print("Требуется PyQt6: pip install -r requirements.txt")
        return 2

    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Windows Optimizer Pro")
    icon = Path(__file__).resolve().parent / "resources" / "icons" / "app.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
