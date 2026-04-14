"""
Event Handlers - модуль обработчиков событий GUI.

Отвечает за:
- Действия меню (открыть, сохранить, о программе)
- Обработка вкладок
- Действия пользователя
"""

import os
from tkinter import filedialog, messagebox
from typing import Any, Callable, Dict, Optional


class GUIEventHandlers:
    """Обработчики событий GUI приложения."""

    def __init__(
        self,
        main_window,
        state_manager,
        window_manager,
        error_handler,
        log_callback: Callable = None
    ):
        """
        Args:
            main_window: Экземпляр главного окна
            state_manager: Менеджер состояния
            window_manager: Менеджер окна
            error_handler: Обработчик ошибок
            log_callback: Функция логирования
        """
        self.main_window = main_window
        self.state_manager = state_manager
        self.window_manager = window_manager
        self.error_handler = error_handler
        self.log_callback = log_callback

    def menu_open_mods(self) -> None:
        """Открыть папку модов через диалог выбора."""
        from config.paths_config import get_paths_config

        paths_config = get_paths_config()
        initial_dir = paths_config.get_mods_folder() or os.path.expanduser("~")

        folder_path = filedialog.askdirectory(
            title="Выберите папку модов",
            initialdir=initial_dir
        )

        if folder_path:
            # Сохраняем путь в конфиг
            self.state_manager.config["mods_folder"] = folder_path
            self.state_manager.save_config()

            # Обновляем все вкладки
            if hasattr(self.main_window, "tab_manager"):
                self.main_window.tab_manager.refresh_all_tabs(folder_path)

            self.window_manager.set_status(f"Папка модов: {folder_path}")

    def menu_save_settings(self) -> None:
        """Сохранить настройки."""
        if self.state_manager.save_config():
            messagebox.showinfo("OK", "Настройки сохранены")
            self.window_manager.set_status("Настройки сохранены")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить настройки")
            self.window_manager.set_status("Ошибка сохранения настроек")

    def on_tab_changed(self, event=None) -> None:
        """Обработчик переключения вкладки."""
        try:
            notebook = self.main_window.notebook
            current_tab = notebook.tab(notebook.select(), "text")
            self.error_handler.log(f"Переключено на вкладку: {current_tab}")
        except Exception:
            pass  # Вкладка может не существовать при закрытии

    def on_save_settings(self, options: dict) -> None:
        """
        Сохранение настроек из вкладки настроек.

        Args:
            options: Словарь с настройками
        """
        self.state_manager.config.update(options)
        if self.state_manager.save_config():
            self.window_manager.set_status("Настройки сохранены")
        else:
            self.window_manager.set_status("Ошибка сохранения настроек")

    def on_save_filters_config(self, filters_config: dict) -> None:
        """
        Сохранение конфигурации фильтров.

        Args:
            filters_config: Словарь с настройками фильтров
        """
        try:
            import json
            from config.paths_config import get_paths_config

            filters_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "filters_config.json"
            )

            with open(filters_path, "w", encoding="utf-8") as f:
                json.dump(filters_config, f, ensure_ascii=False, indent=2)

            self.window_manager.set_status("Настройки фильтров сохранены")
        except Exception as e:
            self.error_handler.log(f"Ошибка сохранения фильтров: {e}")
            self.window_manager.set_status("Ошибка сохранения фильтров")

    def on_load_settings(self) -> dict:
        """
        Загрузка настроек для вкладки настроек.

        Returns:
            Словарь настроек
        """
        return self.state_manager.config.copy()

    def show_about(self) -> None:
        """Показать окно "О программе"."""
        try:
            from gui.dialogs.about_dialog import show_about
            show_about(self.main_window.root)
        except ImportError:
            messagebox.showinfo(
                "О программе",
                "RimWorld Translator Grabber\nВерсия 4.0"
            )

    def show_shortcuts(self) -> None:
        """Показать окно горячих клавиш."""
        try:
            from gui.dialogs.shortcuts_dialog import show_shortcuts
            show_shortcuts(self.main_window.root)
        except ImportError:
            messagebox.showinfo(
                "Горячие клавиши",
                "Ctrl+O - Открыть моды\n"
                "Ctrl+S - Сохранить\n"
                "Ctrl+L - Лог\n"
                "F1 - Помощь"
            )

    def show_documentation(self) -> None:
        """Показать документацию."""
        try:
            from gui.dialogs.documentation_dialog import show_documentation
            show_documentation(self.main_window.root)
        except ImportError:
            messagebox.showinfo("Документация", "Файл документации не найден")

    def show_import_translations(self) -> None:
        """Показать диалог импорта переводов."""
        try:
            from gui.dialogs.import_translations_dialog import ImportTranslationsDialog
            ImportTranslationsDialog(self.main_window.root, self.state_manager.config)
        except ImportError:
            messagebox.showinfo("Импорт", "Модуль импорта недоступен")

    def show_glossary_editor(self) -> None:
        """Показать редактор глоссария."""
        try:
            from gui.dialogs.glossary_editor_dialog import GlossaryEditorDialog
            GlossaryEditorDialog(self.main_window.root, self.state_manager.config)
        except ImportError:
            messagebox.showinfo("Глоссарий", "Редактор глоссария недоступен")

    def rebuild_menu(self) -> None:
        """Перестроить главное меню."""
        if hasattr(self.main_window, "_rebuild_menu"):
            self.main_window._rebuild_menu()

    def rebuild_tabs(self) -> None:
        """Обновить названия всех вкладок через i18n."""
        if hasattr(self.main_window, "_rebuild_tabs"):
            self.main_window._rebuild_tabs()
