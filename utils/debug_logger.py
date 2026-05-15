# utils/debug_logger.py
"""
Система debug-логирования для RimWorld Translator Grabber.

Записывает подробный лог всех действий в файл для отладки.
Использует loguru внутри для всех операций логирования.
"""

from datetime import datetime
from typing import Any

from config.debug_config import DebugConfig
from loguru import logger as loguru_logger

from utils.loguru_setup import is_logging_setup, setup_logging, set_debug_mode


class DebugLogger:
    """
    Централизованный logger для debug-режима.

    Обертка над loguru для сохранения совместимости со старым кодом.

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
        self._logger = loguru_logger

        if self.config.enabled:
            # Проверяем, нужно ли настраивать логирование
            if not is_logging_setup():
                setup_logging(
                    debug_mode=(self.config.log_level == "DEBUG"),
                    log_file=self.config.log_file if self.config.log_to_file else None,
                )
            else:
                # Логирование уже настроено, просто обновляем режим
                set_debug_mode(self.config.log_level == "DEBUG")

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
            self._logger.debug(message)

    def info(self, message: str, **kwargs):
        """Записать сообщение уровня INFO"""
        if self.config.enabled:
            self._logger.info(message)

    def warning(self, message: str, **kwargs):
        """Записать сообщение уровня WARNING"""
        if self.config.enabled:
            self._logger.warning(message)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        """Записать сообщение уровня ERROR"""
        if self.config.enabled:
            if exc_info:
                self._logger.exception(message)
            else:
                self._logger.error(message)

    def exception(self, message: str, exc: Exception = None, **kwargs):
        """Записать исключение с traceback"""
        if self.config.enabled and self.config.log_exceptions:
            if exc:
                self._logger.exception(f"{message}: {exc}")
            else:
                self._logger.exception(message)

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

    def get_log_content(self, lines: int = 100) -> str:
        """Получить последние N строк лога"""
        if not self.config.log_to_file or not self.config.log_file:
            return "Логирование в файл отключено"

        try:
            with open(self.config.log_file, encoding="utf-8") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except OSError as e:
            return f"Ошибка чтения лога: {e}"

    def clear_log(self):
        """Очистить лог-файл"""
        if self.config.log_file and self.config.log_to_file:
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
        if self.config.enabled:
            # Проверяем, нужно ли обновлять
            from utils.loguru_setup import is_logging_setup, set_debug_mode, setup_logging

            debug_mode = self.config.log_level == "DEBUG"
            log_file = self.config.log_file if self.config.log_to_file else None

            if not is_logging_setup():
                # Логирование еще не настроено, настраиваем
                setup_logging(debug_mode=debug_mode, log_file=log_file)
            else:
                # Обновляем только режим (DEBUG/INFO)
                set_debug_mode(debug_mode)


# Глобальный экземпляр для удобства
_debug_logger = None


def get_debug_logger(config: DebugConfig = None) -> DebugLogger:
    """Получить debug logger, обновляя конфигурацию если нужно"""
    global _debug_logger

    if _debug_logger is None or not _debug_logger._initialized:
        DebugLogger.reset()
        _debug_logger = DebugLogger.get_instance(config)
    elif config is not None:
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
