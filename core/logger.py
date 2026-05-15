# core/logger.py
"""
Модуль логирования для RimWorld Translator.

Предоставляет класс Logger для совместимости со старым кодом.
Внутренняя реализация использует loguru.

ВАЖНО: Для вывода в GUI используйте loguru sinks (см. gui.py ui_sink).
gui_callback оставлен для совместимости, но НЕ вызывается автоматически,
чтобы избежать дублирования с loguru sinks.
"""

from typing import Callable

from loguru import logger as loguru_logger


class Logger:
    """
    Логгер для записи событий (обертка над loguru).

    Сохраняет интерфейс для совместимости со старым кодом.
    Внутри использует loguru для всех операций логирования.

    ВАЖНО: gui_callback НЕ вызывается автоматически в методах логирования,
    чтобы избежать дублирования, если используются loguru sinks для GUI.
    """

    def __init__(self, enabled=True, debug=False, path="translator.log", gui_callback: Callable | None = None):
        """
        Инициализация логгера.

        Args:
            enabled: Включить логирование (для совместимости)
            debug: Включить режим отладки
            path: Путь к лог-файлу (не используется напрямую, настройка через setup_logging)
            gui_callback: Callback для отправки сообщений в GUI (НЕ используется автоматически)
        """
        self.enabled = enabled
        self.debug_mode = debug
        self.gui_callback = gui_callback
        self._logger = loguru_logger

    def info(self, msg: str):
        """Записать информационное сообщение."""
        self._logger.info(msg)

    def warn(self, msg: str):
        """Записать предупреждение."""
        self._logger.warning(msg)

    def warning(self, msg: str):
        """Записать предупреждение (алиас для warn)."""
        self.warn(msg)

    def error(self, msg: str):
        """Записать сообщение об ошибке."""
        self._logger.error(msg)

    def debug(self, msg: str):
        """Записать отладочное сообщение (только при включенном debug)."""
        if self.debug_mode:
            self._logger.debug(msg)

    def exception(self, exc: Exception):
        """Записать информацию об исключении с traceback."""
        self._logger.exception(exc)

    def set_level(self, level: str):
        """
        Установить уровень логирования.

        Args:
            level: Уровень ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        from utils.loguru_setup import set_debug_mode

        set_debug_mode(level.upper() == "DEBUG")
        self.debug_mode = level.upper() == "DEBUG"

    def log_to_gui(self, msg: str):
        """
        Явно отправить сообщение в GUI через gui_callback.

        Используйте этот метод только если нужно явно обновить GUI
        и вы уверены, что loguru sink не справляется с этим.

        Args:
            msg: Сообщение для отправки в GUI
        """
        if self.gui_callback:
            self.gui_callback(msg)
