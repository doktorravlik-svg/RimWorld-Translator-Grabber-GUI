# config/debug_config.py
"""
Конфигурация debug-режима для RimWorld Translator Grabber.

Debug-режим записывает подробный лог всех действий в файл
для выявления проблем и отладки.
"""

import os


class DebugConfig:
    """
    Конфигурация debug-режима.

    Атрибуты:
        enabled: Включён ли debug-режим
        log_file: Путь к файлу лога
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Записывать ли в файл
        log_to_console: Выводить ли в консоль
        log_gui_events: Логировать события GUI
        log_config_changes: Логировать изменения конфигурации
        log_file_operations: Логировать файловые операции
        log_exceptions: Логировать исключения с traceback
        max_log_size: Максимальный размер лога в МБ
    """

    def __init__(self):
        self.enabled = False
        # Абсолютный путь к файлу лога в корне проекта
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_file = os.path.join(project_root, "debug.log")
        self.log_level = "DEBUG"
        self.log_to_file = True
        self.log_to_console = False
        self.log_gui_events = True
        self.log_config_changes = True
        self.log_file_operations = True
        self.log_exceptions = True
        self.max_log_size = 10  # МБ

    def to_dict(self) -> dict:
        """Сериализовать в словарь"""
        return {
            "enabled": self.enabled,
            "log_file": self.log_file,
            "log_level": self.log_level,
            "log_to_file": self.log_to_file,
            "log_to_console": self.log_to_console,
            "log_gui_events": self.log_gui_events,
            "log_config_changes": self.log_config_changes,
            "log_file_operations": self.log_file_operations,
            "log_exceptions": self.log_exceptions,
            "max_log_size": self.max_log_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DebugConfig":
        """Десериализовать из словаря"""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


def get_default_debug_config() -> DebugConfig:
    """Получить конфигурацию debug по умолчанию"""
    return DebugConfig()
