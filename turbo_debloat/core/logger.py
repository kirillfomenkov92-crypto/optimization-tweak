"""Логирование TurboDebloat: файл с ротацией + консоль.

Без логгера сбои (особенно при восстановлении) исчезали молча. Здесь —
единый логгер, чтобы любой пропущенный шаг был виден при разборе.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOGGER_NAME = "turbo_debloat"
_configured = False


def _ensure_dir() -> Path:
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        return _LOG_DIR
    except Exception:
        tmp = Path(os.environ.get("TEMP", "/tmp")) / "turbo_debloat_logs"
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp


def get_logger() -> logging.Logger:
    """Вернуть настроенный логгер (идемпотентно)."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file = _ensure_dir() / "turbo_debloat.log"
    fh = RotatingFileHandler(log_file, maxBytes=20 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.propagate = False
    _configured = True
    return logger
