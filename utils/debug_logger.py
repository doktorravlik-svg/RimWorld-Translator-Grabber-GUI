# utils/debug_logger.py
"""
Система debug-логирования для RimWorld Translator Grabber.

Записывает подробный лог всех действий в файл для отладки.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Any

from config.debug_config import DebugConfig


class DebugLogger:
    """
    Централизованный logger для debug-режима.

    Пример использования:
        logger = DebugLogger.get_instance()
        logger.debug("Инициализация GUI")
        logger.info("Загружено 500 модов")
        logger.warning("Файл не найден, используем значение по умолчанию")
        logger.error("Ошибка подключения", exc_info=True)
    """

    _instance = None
    _initialized = False

    def __init__(self, config: DebugConfig = None):
        if self._initialized:
            return

        self.config = config or DebugConfig()
        self.logger = logging.getLogger("rimworld_translator")
        self.logger.setLevel(getattr(logging, self.config.log_level, logging.DEBUG))

        # Формат сообщений
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Файловый handler
        if self.config.log_to_file:
            # Проверяем размер файла и ротируем если нужно
            self._rotate_if_too_large()

            file_handler = logging.FileHandler(self.config.log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Консольный handler
        if self.config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self._initialized = True

    @classmethod
    def get_instance(cls, config: DebugConfig = None) -> "DebugLogger":
        """Получить экземпляр синглтона"""
        if cls._instance is None or not cls._initialized:
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls):
        """Сбросить экземпляр (для тестов)"""
        cls._instance = None
        cls._initialized = False

    def debug(self, message: str, **kwargs):
        """Записать сообщение уровня DEBUG"""
        if self.config.enabled:
            self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Записать сообщение уровня INFO"""
        if self.config.enabled:
            self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Записать сообщение уровня WARNING"""
        if self.config.enabled:
            self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Записать сообщение уровня ERROR"""
        if self.config.enabled:
            self._log(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, exc: Exception = None, **kwargs):
        """Записать исключение с traceback"""
        if self.config.enabled and self.config.log_exceptions:
            if exc:
                tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                self._log(logging.ERROR, f"{message}\n{tb}")
            else:
                self._log(logging.ERROR, message, exc_info=True)

    def gui_event(self, event_type: str, widget: str, details: str = ""):
        """Записать событие GUI"""
        if self.config.enabled and self.config.log_gui_events:
            msg = f"[GUI] {event_type} | {widget}"
            if details:
                msg += f" | {details}"
            self.debug(msg)

    def config_change(self, key: str, old_value: Any, new_value: Any):
        """Записать изменение конфигурации"""
        if self.config.enabled and self.config.log_config_changes:
            self.info(f"[CONFIG] {key}: {old_value!r} → {new_value!r}")

    def file_operation(self, operation: str, path: str, details: str = ""):
        """Записать файловую операцию"""
        if self.config.enabled and self.config.log_file_operations:
            msg = f"[FILE] {operation}: {path}"
            if details:
                msg += f" | {details}"
            self.debug(msg)

    def _log(self, level: int, message: str, **kwargs):
        """Внутренний метод логирования"""
        self.logger.log(level, message, **kwargs)

    def _rotate_if_too_large(self):
        """Ротация лога если он слишком большой"""
        if not os.path.exists(self.config.log_file):
            return

        max_bytes = self.config.max_log_size * 1024 * 1024
        try:
            size = os.path.getsize(self.config.log_file)
            if size > max_bytes:
                # Переименовываем старый лог
                backup = self.config.log_file + ".old"
                if os.path.exists(backup):
                    os.remove(backup)
                os.rename(self.config.log_file, backup)
                self.info("Лог рротирован из-за превышения размера")
        except OSError:
            pass

    def get_log_content(self, lines: int = 100) -> str:
        """Получить последние N строк лога"""
        if not os.path.exists(self.config.log_file):
            return "Лог-файл не найден"

        try:
            with open(self.config.log_file, encoding="utf-8") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except OSError as e:
            return f"Ошибка чтения лога: {e}"

    def clear_log(self):
        """Очистить лог-файл"""
        if os.path.exists(self.config.log_file):
            try:
                with open(self.config.log_file, "w", encoding="utf-8") as f:
                    f.write(f"Лог очищен: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            except OSError:
                pass

    def _reconfigure_handlers(self):
        """
        Перенастроить handlers при изменении конфигурации.
        Вызывается когда enabled меняется с False на True.
        """
        # Очищаем старые handlers
        self.logger.handlers.clear()

        # Формат сообщений
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Файловый handler
        if self.config.log_to_file:
            self._rotate_if_too_large()
            file_handler = logging.FileHandler(self.config.log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Консольный handler
        if self.config.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)


# Глобальный экземпляр для удобства
_debug_logger = None


def get_debug_logger(config: DebugConfig = None) -> DebugLogger:
    """Получить debug logger, обновляя конфигурацию если нужно"""
    global _debug_logger

    # Если logger не существует или не инициализирован - создаём новый
    if _debug_logger is None or not _debug_logger._initialized:
        DebugLogger.reset()
        _debug_logger = DebugLogger.get_instance(config)
    elif config is not None:
        # ✅ ОБНОВЛЯЕМ конфигурацию существующего logger
        _debug_logger.config = config
        _debug_logger._reconfigure_handlers()

    return _debug_logger


def log_debug(message: str):
    """Быстрый вызов для debug"""
    logger = get_debug_logger()
    logger.debug(message)


def log_info(message: str):
    """Быстрый вызов для info"""
    logger = get_debug_logger()
    logger.info(message)


def log_error(message: str, exc: Exception = None):
    """Быстрый вызов для error"""
    logger = get_debug_logger()
    logger.error(message, exc_info=exc is not None)
    if exc:
        logger.exception(message, exc)
