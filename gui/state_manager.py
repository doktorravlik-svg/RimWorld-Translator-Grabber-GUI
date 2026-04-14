"""
State Manager - модуль управления состоянием GUI.

Отвечает за:
- Загрузку/сохранение конфигурации
- Историю операций
- Систему i18n (интернационализация)
- Язык интерфейса
"""

import os
import sys
from collections import deque
from typing import Any, Optional


class GUIStateManager:
    """Управление состоянием GUI приложения."""

    def __init__(self, config_path: str = None):
        """
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config = {}
        self.operation_history: deque = deque(maxlen=100)
        self._config_path = config_path
        self._i18n_manager = None
        self._current_language = "ru"

    def load_config(self) -> dict:
        """
        Загружает конфигурацию из файла.

        Returns:
            Словарь конфигурации
        """
        try:
            from config.config_manager import get_config_manager
            config_manager = get_config_manager()
            self.config = config_manager.load_config()
            return self.config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            self.config = {}
            return self.config

    def save_config(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """
        Сохраняет конфигурацию с повторными попытками.

        Args:
            max_retries: Максимум попыток сохранения
            retry_delay: Задержка между попытками (секунды)

        Returns:
            True если успешно, False иначе
        """
        import time

        for attempt in range(max_retries):
            try:
                from config.config_manager import get_config_manager
                config_manager = get_config_manager()
                config_manager.save_config(self.config)
                return True
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    print(
                        f"Не удалось сохранить конфигуровку: "
                        f"файл заблокирован после {max_retries} попыток"
                    )
                    return False
            except Exception as e:
                print(f"Ошибка сохранения конфигурации: {e}")
                return False

        return False

    def add_to_history(self, operation: str, details: Any = None) -> None:
        """
        Добавляет операцию в историю.

        Args:
            operation: Название операции
            details: Дополнительные детали
        """
        import datetime

        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "operation": operation,
            "details": details,
        }
        self.operation_history.append(entry)

    def show_history(self) -> list:
        """
        Показывает историю операций.

        Returns:
            Список записей истории
        """
        return list(self.operation_history)

    def init_i18n_system(self, locales_dir: str) -> None:
        """
        Инициализирует систему интернационализации.

        Args:
            locales_dir: Путь к папке с локалями
        """
        try:
            from gui.core.i18n_manager import I18nManager
            self._i18n_manager = I18nManager(locales_dir)
        except Exception as e:
            print(f"Ошибка инициализации i18n: {e}")

    def load_saved_language(self) -> str:
        """
        Загружает сохранённый язык из конфигурации.

        Returns:
            Код языка (ru, en, ua, ja)
        """
        self._current_language = self.config.get("language", "ru")
        return self._current_language

    def save_current_language(self) -> None:
        """Сохраняет текущий язык в конфигурацию."""
        self.config["language"] = self._current_language

    def apply_ui_language(self) -> None:
        """Применяет язык к интерфейсу через i18n менеджер."""
        if self._i18n_manager:
            self._i18n_manager.apply_language(self._current_language)

    @property
    def current_language(self) -> str:
        return self._current_language

    @current_language.setter
    def current_language(self, lang: str) -> None:
        self._current_language = lang

    @property
    def i18n_manager(self):
        return self._i18n_manager

    def restart_application(self) -> None:
        """Перезапускает приложение."""
        self.save_config()
        python = sys.executable
        os.execl(python, python, *sys.argv)
