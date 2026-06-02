"""
Построение главного меню для RimWorld Translator Grabber.
"""

import tkinter as tk

from gui.styling.icon_manager import HAS_ICONS, get_menu_icons, set_theme_mode
from loguru import logger


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
            - import_translations
            - show_glossary_editor
            - load_mod_glossary
            - toggle_debug_mode
            - show_debug_log
            - log_panel (объект с методом clear)
    """

    def __init__(self, root, config: dict, callbacks: dict):
        self.root = root
        self.config = config
        self.callbacks = callbacks

        self._theme_var = None
        self._tabs_menu = None
        self.menubar = None
        self._image_refs = []  # 🛡️ КРИТИЧНО: Жёсткое удержание ссылок на PhotoImage

        self.menu_icons = get_menu_icons() if HAS_ICONS else {}

    def build(self) -> tk.Menu:
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        self._image_refs.clear()

        self._build_file_menu()
        self._build_view_menu()
        self._build_tools_menu()
        self._build_help_menu()  # Исправлена опечатка в имени метода

        return self.menubar

    def get_theme_var(self) -> tk.StringVar | None:
        return self._theme_var

    def get_tabs_menu(self) -> tk.Menu | None:
        return self._tabs_menu

    def _safe_callback(self, name: str):
        """Безопасная обёртка: если callback отсутствует, подставляет заглушку."""
        cb = self.callbacks.get(name)
        return cb if callable(cb) else lambda: logger.warning(f"Callback '{name}' не найден")

    def _get_icon_image(self, icon_name: str):
        if not HAS_ICONS or not self.menu_icons:
            return None
        icon = self.menu_icons.get(icon_name)
        if icon is None:
            placeholder = tk.PhotoImage(width=1, height=1)
            self.menu_icons[icon_name] = placeholder
            self._image_refs.append(placeholder)
            return placeholder

        # 🛡️ Добавляем в список сильных ссылок, чтобы GC не убил PhotoImage
        self._image_refs.append(icon)
        return icon

    def update_theme(self, theme_name: str):
        set_theme_mode(theme_name)
        self.menu_icons = get_menu_icons() if HAS_ICONS else {}
        # Tkinter не обновляет картинки в меню динамически. Пересобираем меню.
        if self.menubar:
            self.build()

    def _build_file_menu(self):
        from gui.gui_i18n import i18n

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_file", "Файл"), menu=file_menu)

        file_menu.add_command(
            label=i18n.tr("menu_open_mods", "Открыть папку модов"),
            command=self._safe_callback("open_mods"),
            accelerator="Ctrl+O",
            image=self._get_icon_image("open_mods"),
            compound="left",
        )
        file_menu.add_command(
            label=i18n.tr("menu_save_settings", "Сохранить настройки"),
            command=self._safe_callback("save_settings"),
            accelerator="Ctrl+S",
            image=self._get_icon_image("save"),
            compound="left",
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=i18n.tr("menu_exit", "Выход"),
            command=self.root.quit,
            accelerator="Alt+F4",
            image=self._get_icon_image("exit"),
            compound="left",
        )

    def _build_view_menu(self):
        from gui.gui_i18n import i18n

        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_view", "Вид"), menu=view_menu)

        self._build_theme_submenu(view_menu)
        view_menu.add_separator()
        self._build_tabs_submenu(view_menu)
        view_menu.add_separator()

        view_menu.add_command(
            label=i18n.tr("menu_clear_log", "Очистить лог"),
            command=self._safe_callback("clear_log"),
            accelerator="Ctrl+L",
            image=self._get_icon_image("clear_log"),
            compound="left",
        )
        view_menu.add_command(
            label=i18n.tr("menu_history", "История операций"),
            command=self._safe_callback("show_history"),
            accelerator="Ctrl+H",
            image=self._get_icon_image("history"),
            compound="left",
        )

    def _build_theme_submenu(self, view_menu):
        from gui.gui_i18n import i18n

        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label=i18n.tr("menu_theme", "Тема"), menu=theme_menu)

        current_theme = self.config.get("theme", "light")
        try:
            from gui.styling.theme_manager import THEME_DESCRIPTIONS

            theme_display = THEME_DESCRIPTIONS
        except ImportError:
            theme_display = {
                "light": i18n.tr("theme_light", "🌞 Светлая"),
                "dark": i18n.tr("theme_dark", "🌙 Темная"),
                "ocean": i18n.tr("theme_ocean", "🌊 Океан"),
                "forest": i18n.tr("theme_forest", "🌲 Лес"),
                "solar": i18n.tr("theme_solar", "🔆 Солнечная"),
                "vapor": i18n.tr("theme_vapor", "💨 Пар"),
                "cyborg": i18n.tr("theme_cyborg", "🤖 Киборг"),
                "superhero": i18n.tr("theme_superhero", "🦸 Супергерой"),
            }

        self._theme_var = tk.StringVar(value=current_theme)
        get_theme_names = self.callbacks.get("get_theme_names", lambda: theme_display.keys())

        for theme_key in get_theme_names():
            display_name = theme_display.get(theme_key, theme_key)
            theme_menu.add_radiobutton(
                label=display_name,
                variable=self._theme_var,
                value=theme_key,
                command=lambda t=theme_key: self._change_theme_callback(t),
            )

    def _change_theme_callback(self, theme_name: str):
        """Callback для изменения темы с передачей имени темы."""
        cb = self.callbacks.get("change_theme")
        if callable(cb):
            cb(theme_name)

    def _build_tabs_submenu(self, view_menu):
        from gui.gui_i18n import i18n

        self._tabs_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label=i18n.tr("menu_tabs", "Вкладки"), menu=self._tabs_menu)
        self._tabs_menu.add_command(
            label=i18n.tr("menu_show_all_tabs", "Показать все вкладки"),
            command=self._safe_callback("show_all_tabs"),
            image=self._get_icon_image("show_tabs"),
            compound="left",
        )
        self._tabs_menu.add_separator()

    def _build_tools_menu(self):
        from gui.gui_i18n import i18n

        tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_tools", "Инструменты"), menu=tools_menu)

        tools_menu.add_command(
            label=i18n.tr("menu_verification", "Верификация модов"),
            command=self._safe_callback("start_verification"),
            accelerator="F5",
            image=self._get_icon_image("verification"),
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_full_check", "Полная проверка"),
            command=self._safe_callback("start_full_verification"),
            accelerator="F6",
            image=self._get_icon_image("full_check"),
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_integrity", "Проверка целостности"),
            command=self._safe_callback("run_integrity_check"),
            image=self._get_icon_image("integrity"),
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_load_game_data", "Загрузить данные игры"),
            command=self._safe_callback("run_game_data_load"),
            image=self._get_icon_image("load_game"),
            compound="left",
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label=i18n.tr("menu_import_translations", "📥 Импорт переводов"),
            command=self._safe_callback("import_translations"),
            image=self._get_icon_image("import"),
            compound="left",
        )
        tools_menu.add_command(
            label=i18n.tr("menu_glossary_editor", "📖 Редактор глоссария"),
            command=self._safe_callback("show_glossary_editor"),
            image=self._get_icon_image("glossary"),
            compound="left",
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label=i18n.tr("menu_load_mod_glossary", "📂 Загрузить глоссарий мода"),
            command=self._safe_callback("load_mod_glossary"),
            image=self._get_icon_image("glossary"),
            compound="left",
        )

    def _build_help_menu(self):
        from gui.gui_i18n import i18n

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=i18n.tr("menu_help", "Справка"), menu=help_menu)

        help_menu.add_command(
            label=i18n.tr("menu_documentation", "Документация"),
            command=self._safe_callback("show_documentation"),
            image=self._get_icon_image("documentation"),
            compound="left",
        )
        help_menu.add_command(
            label=i18n.tr("menu_about", "О программе"),
            command=self._safe_callback("show_about"),
            image=self._get_icon_image("about"),
            compound="left",
        )
        help_menu.add_command(
            label=i18n.tr("menu_shortcuts", "Горячие клавиши"),
            command=self._safe_callback("show_shortcuts"),
            accelerator="F1",
            image=self._get_icon_image("shortcuts"),
            compound="left",
        )
        help_menu.add_separator()
        help_menu.add_command(
            label=i18n.tr("menu_language", "Язык интерфейса"),
            command=self._safe_callback("show_language_selector"),
            image=self._get_icon_image("language"),
            compound="left",
        )
        help_menu.add_separator()
        help_menu.add_command(
            label=i18n.tr("menu_debug_toggle", "Debug-режим"),
            command=self._safe_callback("toggle_debug_mode"),
            image=self._get_icon_image("debug_toggle"),
            compound="left",
        )
        help_menu.add_command(
            label=i18n.tr("menu_debug_log", "Просмотреть лог"),
            command=self._safe_callback("show_debug_log"),
            image=self._get_icon_image("debug_log"),
            compound="left",
        )

    def _get_i18n(self, key: str, default: str) -> str:
        try:
            from gui.gui_i18n import i18n

            return i18n.tr(key, default)
        except Exception:
            return default
