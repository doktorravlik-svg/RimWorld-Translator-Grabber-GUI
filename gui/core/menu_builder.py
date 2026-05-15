# gui/core/menu_builder.py
"""
Построение главного меню для RimWorld Translator Grabber.
"""

import tkinter as tk
from loguru import logger

from gui.styling.icon_manager import HAS_ICONS, get_menu_icons


class MenuBuilder:
    """
    Построитель главного меню.

    Args:
        root: Tk root
        config: Словарь конфигурации
        callbacks: Словарь callback-функций
            Ожидает:
            - open_mods
            - save_settings
            - clear_log
            - show_history
            - show_all_tabs
            - change_theme
            - start_verification
            - start_full_verification
            - run_integrity_check
            - run_game_data_load
            - show_documentation
            - show_about
            - show_shortcuts
            - show_language_selector
            - get_theme_names
            - log_panel (объект с методом clear)
    """

    def __init__(self, root, config: dict, callbacks: dict):
        self.root = root
        self.config = config
        self.callbacks = callbacks

        self._theme_var = None
        self._tabs_menu = None
        self.menubar = None

    def build(self) -> tk.Menu:
        """
        Построить главное меню.

        Returns:
            tk.Menu — главное меню
        """
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.menu_icons = get_menu_icons() if HAS_ICONS else {}

        self._build_file_menu()
        self._build_view_menu()
        self._build_tools_menu()
        self._build_help_menu()

        return self.menubar

    def get_theme_var(self) -> tk.StringVar:
        """Получить StringVar для выбора темы"""
        return self._theme_var

    def get_tabs_menu(self) -> tk.Menu:
        """Получить меню управления вкладками"""
        return self._tabs_menu

    def _build_file_menu(self):
        """Меню "Файл" """
        from gui.gui_i18n import i18n

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_file", "Файл"), menu=file_menu)
        file_menu.add_command(
            label=i18n.tr("menu_open_mods", "Открыть папку модов"),
            command=self.callbacks.get("open_mods"),
            accelerator="Ctrl+O",
            image=self.menu_icons.get("open_mods").image
            if HAS_ICONS and self.menu_icons.get("open_mods")
            else None,
            compound="left",
        )
        file_menu.add_command(
            label=i18n.tr("menu_save_settings", "Сохранить настройки"),
            command=self.callbacks.get("save_settings"),
            accelerator="Ctrl+S",
            image=self.menu_icons.get("save").image
            if HAS_ICONS and self.menu_icons.get("save")
            else None,
            compound="left",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=i18n.tr("menu_exit", "Выход"),
            command=self.root.quit,
            accelerator="Alt+F4",
            image=self.menu_icons.get("exit").image
            if HAS_ICONS and self.menu_icons.get("exit")
            else None,
            compound="left",
        )

    def _build_view_menu(self):
        """Меню "Вид" """
        from gui.gui_i18n import i18n

        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_view", "Вид"), menu=view_menu)

        # Подменю тем
        self._build_theme_submenu(view_menu)

        view_menu.add_separator()

        # Подменю управления вкладками
        self._build_tabs_submenu(view_menu)

        view_menu.add_separator()

        view_menu.add_command(
            label=i18n.tr("menu_clear_log", "Очистить лог"),
            command=self.callbacks.get("clear_log"),
            accelerator="Ctrl+L",
            image=self.menu_icons.get("clear_log").image
            if HAS_ICONS and self.menu_icons.get("clear_log")
            else None,
            compound="left",
        )
        view_menu.add_command(
            label=i18n.tr("menu_history", "История операций"),
            command=self.callbacks.get("show_history"),
            accelerator="Ctrl+H",
            image=self.menu_icons.get("history").image
            if HAS_ICONS and self.menu_icons.get("history")
            else None,
            compound="left",
        )

    def _build_theme_submenu(self, view_menu):
        """Подменю тем оформления"""
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(
            label=self._get_i18n("menu_theme", "Тема"),
            menu=theme_menu,
        )

        current_theme = self.config.get("theme", "light")
        # Используем THEME_DESCRIPTIONS из theme_manager если доступно
        try:
            from gui.styling.theme_manager import THEME_DESCRIPTIONS

            theme_display = THEME_DESCRIPTIONS
        except ImportError:
            # Fallback на i18n переводы
            theme_display = {
                "light": self._get_i18n("theme_light", "🌞 Светлая"),
                "dark": self._get_i18n("theme_dark", "🌙 Темная"),
                "ocean": self._get_i18n("theme_ocean", "🌊 Океан"),
                "forest": self._get_i18n("theme_forest", "🌲 Лес"),
                "solar": self._get_i18n("theme_solar", "🔆 Солнечная"),
                "vapor": self._get_i18n("theme_vapor", "💨 Пар"),
                "cyborg": self._get_i18n("theme_cyborg", "🤖 Киборг"),
                "superhero": self._get_i18n("theme_superhero", "🦸 Супергерой"),
            }

        self._theme_var = tk.StringVar(value=current_theme)

        get_theme_names = self.callbacks.get("get_theme_names", lambda: theme_display.keys())
        for theme_key in get_theme_names():
            display_name = theme_display.get(theme_key, theme_key)
            theme_menu.add_radiobutton(
                label=display_name,
                variable=self._theme_var,
                value=theme_key,
                command=lambda t=theme_key: self.callbacks.get("change_theme")(t),
            )

    def _build_tabs_submenu(self, view_menu):
        """Подменю управления вкладками"""
        self._tabs_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(
            label=self._get_i18n("menu_tabs", "Вкладки"),
            menu=self._tabs_menu,
        )
        self._tabs_menu.add_command(
            label=self._get_i18n("menu_show_all_tabs", "Показать все вкладки"),
            command=self.callbacks.get("show_all_tabs"),
            image=self.menu_icons.get("show_tabs").image
            if HAS_ICONS and self.menu_icons.get("show_tabs")
            else None,
            compound="left",
        )
        self._tabs_menu.add_separator()

    def _build_tools_menu(self):
        """Меню "Инструменты" """
        from gui.gui_i18n import i18n

        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_tools", "Инструменты"), menu=tools_menu)
        tools_menu.add_command(
            label=i18n.tr("menu_verification", "Верификация модов"),
            command=self.callbacks.get("start_verification"),
            accelerator="F5",
            image=self.menu_icons.get("verification").image
            if HAS_ICONS and self.menu_icons.get("verification")
            else None,
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_full_check", "Полная проверка"),
            command=self.callbacks.get("start_full_verification"),
            accelerator="F6",
            image=self.menu_icons.get("full_check").image
            if HAS_ICONS and self.menu_icons.get("full_check")
            else None,
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_integrity", "Проверка целостности"),
            command=self.callbacks.get("run_integrity_check"),
            image=self.menu_icons.get("integrity").image
            if HAS_ICONS and self.menu_icons.get("integrity")
            else None,
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_load_game_data", "Загрузить данные игры"),
            command=self.callbacks.get("run_game_data_load"),
            image=self.menu_icons.get("load_game").image
            if HAS_ICONS and self.menu_icons.get("load_game")
            else None,
            compound="left",
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label=i18n.tr("menu_import_translations", "📥 Импорт переводов"),
            command=self.callbacks.get("import_translations"),
            image=self.menu_icons.get("import").image
            if HAS_ICONS and self.menu_icons.get("import")
            else None,
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_glossary_editor", "📖 Редактор глоссария"),
            command=self.callbacks.get("show_glossary_editor"),
            image=self.menu_icons.get("glossary").image
            if HAS_ICONS and self.menu_icons.get("glossary")
            else None,
            compound="left",
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label=i18n.tr("menu_load_mod_glossary", "📂 Загрузить глоссарь мода"),
            command=self.callbacks.get("load_mod_glossary"),
            image=self.menu_icons.get("glossary").image
            if HAS_ICONS and self.menu_icons.get("glossary")
            else None,
            compound="left",
        )
        # ✅ ДОБАВЛЕНО: Логирование для отладки меню
        cb = self.callbacks.get("show_glossary_editor")
        logger.debug(f"show_glossary_editor callback: {cb}")
        if cb:
            logger.debug("✅ Callback show_glossary_editor установлен")
        else:
            logger.warning("❌ Callback show_glossary_editor НЕ установлен!")

    def _build_help_menu(self):
        """Меню "Справка" """
        from gui.gui_i18n import i18n

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_help", "Справка"), menu=help_menu)
        help_menu.add_command(
            label=i18n.tr("menu_documentation", "Документация"),
            command=self.callbacks.get("show_documentation"),
            image=self.menu_icons.get("documentation").image
            if HAS_ICONS and self.menu_icons.get("documentation")
            else None,
            compound="left",
        )
        help_menu.add_command(
            label=i18n.tr("menu_about", "О программе"),
            command=self.callbacks.get("show_about"),
            image=self.menu_icons.get("about").image
            if HAS_ICONS and self.menu_icons.get("about")
            else None,
            compound="left",
        )
        help_menu.add_command(
            label=i18n.tr("menu_shortcuts", "Горячие клавиши"),
            command=self.callbacks.get("show_shortcuts"),
            accelerator="F1",
            image=self.menu_icons.get("shortcuts").image
            if HAS_ICONS and self.menu_icons.get("shortcuts")
            else None,
            compound="left",
        )
        help_menu.add_separator()
        help_menu.add_command(
            label=i18n.tr("menu_language", "Язык интерфейса"),
            command=self.callbacks.get("show_language_selector"),
            image=self.menu_icons.get("language").image
            if HAS_ICONS and self.menu_icons.get("language")
            else None,
            compound="left",
        )
        help_menu.add_separator()
        help_menu.add_command(
            label=self._get_i18n("menu_debug_toggle", "Debug-режим"),
            command=self.callbacks.get("toggle_debug_mode"),
            image=self.menu_icons.get("debug_toggle").image
            if HAS_ICONS and self.menu_icons.get("debug_toggle")
            else None,
            compound="left",
        )
        help_menu.add_command(
            label=self._get_i18n("menu_debug_log", "Просмотреть лог"),
            command=self.callbacks.get("show_debug_log"),
            image=self.menu_icons.get("debug_log").image
            if HAS_ICONS and self.menu_icons.get("debug_log")
            else None,
            compound="left",
        )

    def _get_i18n(self, key: str, default: str) -> str:
        """Получить переведённую строку"""
        try:
            from gui.gui_i18n import i18n

            return i18n.tr(key, default)
        except Exception:
            return default
