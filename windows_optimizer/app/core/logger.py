"""Логирование всех действий приложения.

Пишет в файл (с ротацией) и в консоль. Структурированный помощник
``log_change`` фиксирует каждое изменение системы: модуль, действие,
старое и новое значение, результат — это основа для аудита и отката.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOGGER_NAME = "windows_optimizer"
_configured = False


def _ensure_dir() -> Path:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        return _LOG_DIR
    except Exception:
        # Фолбэк во временную папку, если нет прав на каталог приложения.
        tmp = Path(os.environ.get("TEMP", "/tmp")) / "windows_optimizer_logs"
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp


def get_logger() -> logging.Logger:
    """Вернуть настроенный логгер приложения (идемпотентно)."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file = _ensure_dir() / "optimizer.log"
    fh = RotatingFileHandler(log_file, maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.propagate = False
    _configured = True
    logger.info("Логгер инициализирован: %s", log_file)
    return logger


def log_change(module: str, action: str, old=None, new=None, status: str = "SUCCESS") -> None:
    """Зафиксировать изменение системы в едином формате."""
    get_logger().info(
        "[%s] %s | было=%r -> стало=%r | %s", module, action, old, new, status
    )
