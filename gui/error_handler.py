"""
Error Handler - модуль логирования и отладки для GUI.

Отвечает за:
- Логирование сообщений
- Debug режим
- Показ debug лога
"""

from typing import Optional


class GUIErrorHandler:
    """Обработчик ошибок и логирования для GUI приложения."""

    def __init__(self, log_callback=None, debug_callback=None):
        """
        Args:
            log_callback: Функция для вывода лого (например, set_status)
            debug_callback: Функция для debug логов
        """
        self._log_callback = log_callback
        self._debug_callback = debug_callback
        self._debug_mode = False

    def log(self, message: str) -> None:
        """
        Добавляет сообщение в лог.

        Args:
            message: Текст сообщения
        """
        if self._log_callback:
            self._log_callback(message)
        if self._debug_callback and self._debug_mode:
            self._debug_callback(f"[DEBUG] {message}")

    def log_to_panel(self, message: str) -> None:
        """
        Передаёт сообщение напрямую в лог-панель.

        Args:
            message: Текст сообщения
        """
        if self._log_callback:
            self._log_callback(message)

    def flush_log(self) -> None:
        """Принудительное обновление лога."""
        if self._log_callback:
            self._log_callback("")  # Пустое сообщение для обновления

    def show_debug_log(self) -> None:
        """Показать окно debug-лога."""
        if self._debug_callback:
            self._debug_callback("SHOW_DEBUG_LOG")

    def toggle_debug_mode(self) -> bool:
        """
        Переключить debug-режим.

        Returns:
            Новое состояние debug режима
        """
        self._debug_mode = not self._debug_mode
        status = "включён" if self._debug_mode else "выключен"
        self.log(f"Debug-режим {status}")
        return self._debug_mode

    @property
    def debug_mode(self) -> bool:
        """Текущее состояние debug режима."""
        return self._debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        self._debug_mode = value
