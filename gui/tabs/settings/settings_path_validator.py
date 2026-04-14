"""
Settings Path Validator - валидация путей и история в настройках GUI.

Отвечает за:
- Валидацию пути к папке модов
- Валидацию пути к папке вывода
- Валидацию пути к игре
- Историю выбранных путей
- Выбор файла пресета
"""

import os
from typing import Callable, List, Optional

import ttkbootstrap as ttk
from tkinter import filedialog
from ttkbootstrap.constants import *


class SettingsPathValidator:
    """Валидатор путей для вкладки настроек."""

    def __init__(self, config: dict):
        """
        Args:
            config: Словарь конфигурации
        """
        self.config = config
        self._history: List[str] = []
        self._history_var: Optional[ttk.StringVar] = None
        self._history_listbox: Optional[ttk.Widget] = None

    def load_path_history(self) -> None:
        """Загружает историю путей из конфига."""
        self._history = self.config.get("path_history", [])

    def save_path_history(self) -> None:
        """Сохраняет историю путей в конфиг."""
        self.config["path_history"] = self._history

    def add_to_history(self, path: str) -> None:
        """
        Добавляет путь в историю (максимум 10).

        Args:
            path: Путь для добавления
        """
        if path in self._history:
            self._history.remove(path)
        self._history.insert(0, path)
        self._history = self._history[:10]  # Ограничиваем 10 записями

    def validate_mods_path(self, path: str) -> tuple[bool, str]:
        """
        Проверяет путь к папке модов.

        Args:
            path: Путь для проверки

        Returns:
            (успех, сообщение)
        """
        if not path:
            return False, "Путь не указан"

        if not os.path.exists(path):
            return False, f"Папка не существует: {path}"

        if not os.path.isdir(path):
            return False, f"Указан файл, а не папка: {path}"

        # Считаем количество модов
        mod_count = 0
        for item in os.listdir(path):
            mod_path = os.path.join(path, item)
            if os.path.isdir(mod_path):
                about_path = os.path.join(mod_path, "About", "About.xml")
                if os.path.exists(about_path):
                    mod_count += 1

        if mod_count == 0:
            return False, f"Папка существует, но моды не найдены"

        return True, f"Найдено модов: {mod_count}"

    def validate_output_path(self, path: str) -> tuple[bool, str]:
        """
        Проверяет/создаёт путь к папке вывода.

        Args:
            path: Путь для проверки

        Returns:
            (успех, сообщение)
        """
        if not path:
            return False, "Путь не указан"

        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                return True, f"Папка создана: {path}"

            if not os.path.isdir(path):
                return False, f"Указан файл, а не папка: {path}"

            return True, f"Папка существует: {path}"
        except PermissionError:
            return False, f"Нет прав для создания папки: {path}"
        except Exception as e:
            return False, f"Ошибка: {e}"

    def validate_game_path(self, path: str) -> tuple[bool, str]:
        """
        Проверяет путь к игре.

        Args:
            path: Путь для проверки

        Returns:
            (успех, сообщение)
        """
        if not path:
            return False, "Путь не указан"

        if not os.path.exists(path):
            return False, f"Путь не существует: {path}"

        # Проверяем наличие RimWorld.exe или RimWorldMac.app
        exe_files = ["RimWorld.exe", "RimWorldWin64.exe", "RimWorldMac.app"]
        found = any(os.path.exists(os.path.join(path, exe)) for exe in exe_files)

        if not found:
            # Проверяем на уровень выше
            parent = os.path.dirname(path)
            found = any(os.path.exists(os.path.join(parent, exe)) for exe in exe_files)
            if found:
                return True, f"Игра найдена в родительской папке"

        if found:
            return True, f"Игра найдена: {path}"

        return False, f"RimWorld.exe не найден в: {path}"

    def browse_preset(self, initial_dir: str = "") -> Optional[str]:
        """
        Открывает диалог выбора файла пресета.

        Args:
            initial_dir: Начальная директория

        Returns:
            Путь к файлу пресета или None
        """
        return filedialog.askopenfilename(
            title="Выберите файл пресета",
            initialdir=initial_dir,
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )

    def create_history_widget(
        self,
        parent: ttk.Frame,
        history_var: ttk.StringVar,
        history_listbox: ttk.Widget
    ) -> None:
        """
        Создаёт виджет истории путей.

        Args:
            parent: Родительский виджет
            history_var: Переменная для отображения
            history_listbox: Виджет списка истории
        """
        self._history_var = history_var
        self._history_listbox = history_listbox
        self.update_history_display()

    def update_history_display(self) -> None:
        """Обновляет отображение истории путей."""
        if self._history_var:
            self._history_var.set("\n".join(self._history) if self._history else "Нет сохранённых путей")

        if self._history_listbox:
            self._history_listbox.delete(0, "end")
            for path in self._history:
                self._history_listbox.insert("end", path)
