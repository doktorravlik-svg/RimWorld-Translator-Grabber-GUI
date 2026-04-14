# gui/debug_manager.py
"""
Централизованный менеджер debug режима для GUI.

Обеспечивает:
- Включение/выключение debug режима
- Логирование всех действий пользователя
- Визуальные индикаторы (заголовок окна)
- Сохранение настроек в конфигурацию
- Интеграцию с DebugLogger

Пример использования:
    debug_mgr = DebugManager(root, config, log_callback, save_callback)
    debug_mgr.toggle()  # Включить/выключить
    debug_mgr.log_event("Перевод запущен", details="English -> Russian")
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import datetime
from typing import Any

import ttkbootstrap as ttk
from config.debug_config import DebugConfig
from utils.debug_logger import DebugLogger, get_debug_logger


class DebugManager:
    """
    Менеджер debug режима.

    Управляет состоянием debug режима, логированием действий
    и визуальными индикаторами.

    Args:
        root: Tkinter root окно
        config: Словарь конфигурации приложения
        log_callback: Функция для добавления сообщений в UI лог
        save_callback: Функция для сохранения конфигурации
    """

    def __init__(
        self,
        root: ttk.Window,
        config: dict[str, Any],
        log_callback: Callable[[str], None],
        save_callback: Callable[[], None],
    ) -> None:
        self.root = root
        self.config = config
        self.log_callback = log_callback
        self.save_callback = save_callback

        # Загружаем настройки debug из конфига
        debug_data = config.get("debug", {})
        self.debug_config = DebugConfig.from_dict(debug_data) if debug_data else DebugConfig()

        # Создаём logger
        self.debug_logger: DebugLogger | None = None
        if self.debug_config.enabled:
            self.debug_logger = get_debug_logger(self.debug_config)

    @property
    def is_enabled(self) -> bool:
        """Включён ли debug режим"""
        return self.debug_config.enabled

    def toggle(self) -> bool:
        """
        Переключить debug режим.

        Returns:
            Новое состояние (True = включён)
        """
        self.debug_config.enabled = not self.debug_config.enabled
        self.config["debug"] = self.debug_config.to_dict()

        if self.debug_config.enabled:
            self._enable_debug()
        else:
            self._disable_debug()

        # Обновляем UI и сохраняем
        self._update_window_title()
        self.save_callback()

        return self.debug_config.enabled

    def enable(self) -> None:
        """Включить debug режим"""
        if not self.debug_config.enabled:
            self.toggle()

    def disable(self) -> None:
        """Выключить debug режим"""
        if self.debug_config.enabled:
            self.toggle()

    def log_action(self, message: str, category: str = "general") -> None:
        """
        Записать действие в логи (UI + debug).

        Args:
            message: Сообщение для логирования
            category: Категория действия (например, "gui", "translation", "config")
        """
        # Всегда пишем в UI лог
        self.log_callback(message)

        # Если debug включён - пишем в debug.log с категорией
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[{category.upper()}] {message}")

    def log_event(self, event_type: str, widget: str, details: str = "") -> None:
        """
        Записать событие GUI.

        Args:
            event_type: Тип события (например, "button_click")
            widget: Виджет, вызвавший событие
            details: Дополнительные детали
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.gui_event(event_type, widget, details)

    def log_app_start(self) -> None:
        """Записать запуск приложения"""
        if self.debug_config.enabled and self.debug_logger:
            import sys

            self.debug_logger.info("=" * 70)
            self.debug_logger.info("ПРИЛОЖЕНИЕ ЗАПУЩЕНО")
            self.debug_logger.info("Версия: RimWorld Translator Grabber V2+")
            self.debug_logger.info(f"Python: {sys.version}")
            self.debug_logger.info(f"Платформа: {sys.platform}")
            self.debug_logger.info(f"Кодировка: {sys.getdefaultencoding()}")
            self.debug_logger.info("=" * 70)

    def log_app_exit(self) -> None:
        """Записать завершение приложения"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info("Приложение завершает работу")

    def log_theme_change(self, old_theme: str, new_theme: str) -> None:
        """Записать изменение темы"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[THEME] Тема изменена: {old_theme} -> {new_theme}")

    def log_language_change(self, old_lang: str, new_lang: str) -> None:
        """Записать изменение языка интерфейса"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(f"[LANGUAGE] Язык интерфейса: {old_lang} -> {new_lang}")

    def log_tab_switch(self, tab_name: str) -> None:
        """Записать переключение вкладки"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.debug(f"[TAB] Переключение на вкладку: {tab_name}")

    def log_translation_start(self, source: str, target: str, mode: str, mods_count: int) -> None:
        """Записать запуск перевода"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(
                f"[TRANSLATION] Запуск: {source} -> {target}, режим: {mode}, модов: {mods_count}"
            )

    def log_translation_complete(
        self, success: bool, duration: float, translated_count: int
    ) -> None:
        """Записать завершение перевода"""
        if self.debug_config.enabled and self.debug_logger:
            status = "УСПЕШНО" if success else "С ОШИБКАМИ"
            self.debug_logger.info(
                f"[TRANSLATION] Завершён: {status}, время: {duration:.1f}с, переведено: {translated_count}"
            )

    def log_verification_start(self, mods_count: int, checks: list[str]) -> None:
        """Записать запуск верификации"""
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.info(
                f"[VERIFICATION] Запуск: модов: {mods_count}, проверки: {', '.join(checks)}"
            )

    def log_file_operation(self, operation: str, path: str, details: str = "") -> None:
        """
        Записать файловую операцию.

        Args:
            operation: Тип операции (например, "open_file")
            path: Путь к файлу/папке
            details: Дополнительные детали
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.file_operation(operation, path, details)

    def log_config_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """
        Записать изменение конфигурации.

        Args:
            key: Ключ конфигурации
            old_value: Старое значение
            new_value: Новое значение
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.config_change(key, old_value, new_value)

    def log_status_change(self, message: str) -> None:
        """
        Записать изменение статуса.

        Args:
            message: Новое сообщение статуса
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.gui_event("status_change", "StatusBar", message)

    def log_progress(self, action: str, value: int | None = None) -> None:
        """
        Записать действие с прогресс-баром.

        Args:
            action: Действие ("start", "stop", "update")
            value: Значение прогресса (0-100)
        """
        if self.debug_config.enabled and self.debug_logger:
            if value is not None:
                self.debug_logger.debug(f"Прогресс: {action} - {value}%")
            else:
                self.debug_logger.debug(f"Прогресс-бар: {action}")

    def log_error(self, message: str, exc: Exception | None = None) -> None:
        """
        Записать ошибку.

        Args:
            message: Сообщение об ошибке
            exc: Исключение (опционально)
        """
        if self.debug_config.enabled and self.debug_logger:
            self.debug_logger.error(message, exc_info=exc is not None)
            if exc:
                self.debug_logger.exception(message, exc)

    def get_log_content(self, lines: int = 100) -> str:
        """
        Получить последние N строк лога.

        Args:
            lines: Количество строк для получения

        Returns:
            Содержимое лога
        """
        if self.debug_logger:
            return self.debug_logger.get_log_content(lines)
        return "Debug логгер не инициализирован"

    def clear_log(self) -> None:
        """Очистить лог-файл"""
        if self.debug_logger:
            self.debug_logger.clear_log()

    def _enable_debug(self) -> None:
        """Включить debug режим"""
        # Пересоздаём logger с новыми настройками
        self.debug_logger = get_debug_logger(self.debug_config)
        self.debug_logger.info("=" * 60)
        self.debug_logger.info("Debug-режим ВКЛЮЧЁН")
        self.debug_logger.info(f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_logger.info(f"Python: {sys.version}")
        self.debug_logger.info(f"Платформа: {sys.platform}")
        self.debug_logger.info("=" * 60)

    def _disable_debug(self) -> None:
        """Выключить debug режим"""
        if self.debug_logger:
            self.debug_logger.info("Debug-режим ВЫКЛЮЧЕН")

    def _update_window_title(self) -> None:
        """Обновить заголовок окна с пометкой [DEBUG]"""
        try:
            from gui.gui_i18n import i18n

            title = i18n.tr("gui_root_title", "RimWorld Translator Grabber V2+")
            if self.debug_config.enabled:
                title += " [🔧 DEBUG]"
            self.root.title(title)
        except Exception:
            pass

    def get_status_text(self) -> str:
        """
        Получить текст статуса debug режима.

        Returns:
            Текст для отображения в статус-баре
        """
        if self.debug_config.enabled:
            return "🔧 DEBUG активен"
        return ""
