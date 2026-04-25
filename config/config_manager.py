# config/config_manager.py
"""
Централизованный менеджер конфигурации для предотвращения гонок данных.

Все компоненты должны использовать этот класс для чтения/записи gui_config.json.
"""

import json
import os
import threading
from typing import Any

_CONFIG_FILE = "gui_config.json"
_lock = threading.Lock()


class ConfigManager:
    """
    Синглтон для управления конфигурацией GUI.

    Использование:
        from config.config_manager import get_config_manager

        config_mgr = get_config_manager()
        value = config_mgr.get("key", "default")
        config_mgr.set("key", "value")
    """

    _instance = None
    _config: dict[str, Any] = {}
    _file_path: str = _CONFIG_FILE

    @classmethod
    def get_instance(cls, config_file: str = _CONFIG_FILE) -> "ConfigManager":
        """Получить экземпляр синглтона"""
        if cls._instance is None or cls._file_path != config_file:
            cls._instance = cls(config_file)
        return cls._instance

    def __init__(self, config_file: str = _CONFIG_FILE):
        """Инициализация менеджера конфигурации"""
        self._file_path = config_file
        self._load()

    def _load(self):
        """Загрузить конфигурацию из файла"""
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, OSError, IOError) as e:
                print(f"Ошибка загрузки конфигурации: {e}")
                self._config = {}
        else:
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу"""
        return self._config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        """
        Установить значение.

        Args:
            key: Ключ конфигурации
            value: Значение
            save: Сохранить сразу в файл (по умолчанию True)
        """
        self._config[key] = value
        if save:
            self.save()

    def update(self, data: dict, save: bool = True):
        """
        Обновить несколько значений.

        Args:
            data: Словарь с новыми значениями
            save: Сохранить сразу в файл (по умолчанию True)
        """
        self._config.update(data)
        if save:
            self.save()

    def save(self):
        """Сохранить конфигурацию в файл с блокировкой"""
        with _lock:
            try:
                with open(self._file_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=4, ensure_ascii=False)
            except (OSError, IOError) as e:
                print(f"Ошибка сохранения конфигурации: {e}")

    def reload(self):
        """Перезагрузить конфигурацию из файла"""
        self._load()

    def get_all(self) -> dict[str, Any]:
        """Получить всю конфигурацию"""
        return self._config.copy()


# Глобальный экземпляр для удобства
def get_config_manager(config_file: str = _CONFIG_FILE) -> ConfigManager:
    """Получить менеджер конфигурации"""
    return ConfigManager.get_instance(config_file)
