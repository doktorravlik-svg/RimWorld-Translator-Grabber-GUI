# config/config_manager.py
"""
Централизованный менеджер конфигурации для предотвращения гонок данных.

Все компоненты должны использовать этот класс для чтения/записи gui_config.json.
"""

import json
import os
import shutil
import threading
from typing import Any
from loguru import logger

from utils.locks import config_lock

_CONFIG_FILE = "gui_config.json"


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
    _lock = threading.RLock()

    @classmethod
    def get_instance(cls, config_file: str = _CONFIG_FILE) -> "ConfigManager":
        """
        Получить экземпляр синглтона.

        ВАЖНО: При смене config_file создаётся новый экземпляр.
        Старые ссылки остаются валидными и указывают на прежний файл.
        """
        with cls._lock:
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
            except json.JSONDecodeError as e:
                # Создаём бэкап повреждённого файла
                backup_path = f"{self._file_path}.bak"
                try:
                    shutil.copy2(self._file_path, backup_path)
                    logger.warning(f"Повреждённый конфиг создан бэкап: {backup_path}")
                except Exception:
                    pass
                logger.error(f"Ошибка загрузки конфигурации: {e}")
                self._config = {}
            except (OSError, IOError) as e:
                logger.error(f"Ошибка загрузки конфигурации: {e}")
                self._config = {}
        else:
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу (потокобезопасно)"""
        with config_lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True):
        """
        Установить значение.

        Args:
            key: Ключ конфигурации
            value: Значение
            save: Сохранить сразу в файл (по умолчанию True)
        """
        with config_lock:
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
        with config_lock:
            self._config.update(data)
        if save:
            self.save()

    def save(self):
        """Сохранить конфигурацию в файл с блокировкой"""
        with config_lock:
            try:
                with open(self._file_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, indent=4, ensure_ascii=False)
            except (OSError, IOError) as e:
                logger.error(f"Ошибка сохранения конфигурации: {e}")

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
