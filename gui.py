import os
import sys
import threading
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from loguru import logger
from ttkbootstrap.constants import *

# Импорт модулей проекта
try:
    from config.config_manager import get_config_manager
    from config.paths_config import get_paths_config
    from duplicates import duplicate_merger  # noqa: F401
    from integrity import game_data_processor, integrity_checker, mod_verifier  # noqa: F401
    from translation import translator  # noqa: F401
except ImportError as e:
    try:
        from gui.gui_i18n import tr
    except ImportError:

        def tr(key, default=""):
            return default

    messagebox.showerror(
        tr("gui_import_error", "Ошибка импорта"), f"Не удалось импортировать модули: {e}"
    )
    sys.exit(1)

# Компоненты GUI
from gui.actions import GameDataLoader
from gui.constants import (
    DEFAULT_WINDOW_GEOMETRY,
    MAX_SAVE_RETRIES,
    MIN_WINDOW_SIZE,
    SAVE_RETRY_DELAY,
)
from gui.core import MenuBuilder, TabManager, UIBuilder
from gui.debug_manager import DebugManager
from gui.dialogs import show_about, show_documentation, show_history, show_shortcuts
from gui.dialogs.glossary_editor_dialog import GlossaryEditorDialog
from gui.dialogs.import_translations_dialog import ImportTranslationsDialog
from gui.dialogs.mod_glossary_import_dialog import ModGlossaryImportDialog
from gui.gui_i18n import i18n
from gui.handlers.gui_handlers import (
    DuplicateMergeHandler,
    IntegrityCheckHandler,
    TranslationHandler,
    VerificationHandler,
)
from gui.keyboard import HotkeyManager, setup_default_hotkeys
from gui.styling import (
    apply_colors,
    apply_fonts,
    apply_theme,
    change_theme,
    get_font_tuple,
    get_theme_names,
)
from gui.styling.theme_manager import TTKBOOTSTRAP_THEMES
from signals import SignalBus
from utils.path_utils import ensure_project_root_in_path
from workers import TranslationWorker, VerificationWorker
from workers.duplicate_worker import DuplicateWorker
from workers.integrity_worker import IntegrityWorker

ensure_project_root_in_path()


class ImprovedGUI:
    def __init__(self, root=None):
        # Если root не передан, создаем ttkbootstrap Window
        if root is None:
            theme_name = TTKBOOTSTRAP_THEMES.get("light", "cosmo")
            self.root = ttk.Window(themename=theme_name)
        else:
            self.root = root

        self.root.title(i18n.tr("gui_root_title", "RimWorld Translator Grabber V2+"))
        self.root.geometry(DEFAULT_WINDOW_GEOMETRY)
        self.root.minsize(*MIN_WINDOW_SIZE)  # Минимальный размер окна

        # ✅ Принудительно показываем окно
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # Настройка стилей
        self.style = ttk.Style()

        # Настройки по умолчанию
        self.config = {
            "source_language": "English",
            "target_language": "Russian",
            "mods_folder": "",
            "output_folder": "",
            "preset_file": "",
            "theme": "light",
            "max_history": 100,
        }

        # История операций
        self.operation_history = deque(maxlen=self.config.get("max_history", 100))

        # Инициализация SignalBus
        self.signal_bus = SignalBus.get_instance()

        # Инициализация debug-режима через централизованный менеджер
        self.debug_manager = DebugManager(
            root=self.root,
            config=self.config,
            log_callback=self._log_to_panel,
            save_callback=self.save_config,
        )

        # Инициализация обработчиков
        self.verification_handler = None
        self.translation_handler = None
        self.duplicate_handler = None
        self.integrity_handler = None

        # ✅ ИСПРАВЛЕНО: Создаём self.callbacks ДО setup_ui()
        self.callbacks = {
            "open_mods": self._menu_open_mods,
            "save_settings": self._menu_save_settings,
            "clear_log": self._menu_clear_log,
            "show_history": self.show_history,
            "show_all_tabs": self._show_all_tabs,
            "change_theme": self._change_theme,
            "start_verification": self.start_verification,
            "start_full_verification": self.start_full_verification,
            "run_integrity_check": self.run_integrity_check,
            "run_game_data_load": self.run_game_data_load,
            "show_documentation": self._show_documentation,
            "show_about": self._show_about,
            "show_shortcuts": self._show_shortcuts,
            "show_language_selector": self._show_language_selector,
            "show_debug_log": self.show_debug_log,
            "toggle_debug_mode": self.toggle_debug_mode,
            "get_theme_names": get_theme_names,
            "import_translations": self._show_import_translations,
            "show_glossary_editor": self._show_glossary_editor,
            "load_mod_glossary": self._show_mod_glossary_import,
            "save_config": self.save_config,
            "start_translation": self.start_translation,
            "cancel_translation": self.cancel_translation,
            "start_duplicate_merge": self.start_duplicate_merge,
            "apply_fonts": self._apply_fonts,
            "apply_colors": self._apply_colors,
            "log": self.log,
            "set_status": self.set_status,
            "start_progress": self.start_progress,
            "stop_progress": self.stop_progress,
            "set_progress": self.set_progress,
            "on_save_settings": self._on_save_settings,
            "on_load_settings": self.load_config,
            "on_save_filters_config": self._save_filters_config,
        }

        # ✅ ИСПРАВЛЕНО: Создаём self.tab_manager ДО setup_ui()
        # (иначе setup_ui() использует несуществующий tab_manager)
        # Сначала создаём главный Panedwindow (не запаковываем - это сделает UIBuilder)
        self.main_paned = ttk.Panedwindow(self.root, orient="vertical")

        # Сначала создаём TabManager и notebook (ttk уже импортирован в начале файла)
        self.notebook = ttk.Notebook(self.main_paned)
        self.main_paned.add(self.notebook, weight=3)

        self.tab_manager = TabManager(self.notebook, self.config, self.save_config, self.log)
        self.tab_manager.set_tabs_menu(None)  # будет установлено в setup_menu()

        self.load_config()
        self.setup_ui()
        self.setup_keyboard_shortcuts()
        self._load_saved_language()

        # Инициализируем тему иконок
        from gui.styling.icon_manager import icons

        icons.set_theme(self.config.get("theme", "light"))

        # ✅ Debug: логируем запуск приложения
        self.debug_manager.log_app_start()

    def _log_to_panel(self, message):
        """Внутренний метод для передачи сообщений в лог-панель"""
        self.log_panel.log(message)

    def log(self, message):
        """Добавление сообщения в лог"""
        # Пишем только в UI панель
        self.log_panel.log(message)
        # Debug менеджер сам решает, куда писать (debug.log + UI через log_callback)
        # НЕ вызываем log_action здесь, чтобы избежать дублирования в UI
        # debug_manager.log_action() вызывается только для конкретных действий,
        # а не для каждого сообщения лога

    def show_debug_log(self):
        """Показать окно debug-лога"""
        # Если debug выключен - включаем
        if not self.debug_manager.is_enabled:
            self.debug_manager.enable()
            self.log("Debug-режим включён через меню")

        from gui.dialogs import show_debug_log as _show_debug_log

        _show_debug_log(self.root, self.debug_manager.debug_logger)

    def _show_import_translations(self):
        """Показать диалог импорта переводов"""
        self.debug_manager.log_action("Открыт диалог импорта переводов", category="gui")
        ImportTranslationsDialog(self.root)

    def _show_glossary_editor(self):
        """Показать редактор глоссария"""
        logger.debug("Вызов _show_glossary_editor()")
        try:
            self.debug_manager.log_action("Открыт редактор глоссария", category="gui")
            logger.debug(f"self.root = {self.root}")
            logger.debug(f"root exists: {self.root.winfo_exists() if hasattr(self, 'root') else 'NO ROOT'}")

            # ✅ ИСПРАВЛЕНО: Сохраняем ссылку чтобы избежать garbage collection
            logger.debug("Создание GlossaryEditorDialog...")
            self._glossary_dialog = GlossaryEditorDialog(self.root, self.config.get("target_language"))
            logger.debug(f"Диалог создан: {self._glossary_dialog}")

            if hasattr(self._glossary_dialog, 'dialog'):
                logger.debug(f"dialog.dialog = {self._glossary_dialog.dialog}")
                logger.debug(f"dialog exists: {self._glossary_dialog.dialog.winfo_exists()}")
        except Exception as e:
            logger.error(f"Ошибка запуска редактора глоссария: {e}")
            import traceback
            logger.error(traceback.format_exc())
            from tkinter import messagebox
            from gui.gui_i18n import tr
            messagebox.showerror(
                tr("error", "Ошибка"),
                f"Не удалось запустить редактор глоссария:\n{e}"
            )

    def _show_mod_glossary_import(self):
        """Показать диалог импорта глоссаря мода"""
        self.debug_manager.log_action("Открыт диалог импорта глоссаря мода", category="gui")
        ModGlossaryImportDialog(
            self.root,
            self.config.get("target_language"),
            callback=self._glossary_imported
        )

    def _glossary_imported(self):
        """Обработчик после импорта глоссария"""
        self.debug_manager.log_action("Глоссарий мода импортирован", category="gui")
        if hasattr(self, '_glossary_dialog') and self._glossary_dialog:
            # Проверяем, что диалог всё ещё существует
            if hasattr(self._glossary_dialog, 'dialog') and self._glossary_dialog.dialog.winfo_exists():
                self._glossary_dialog._load_glossary()

    def toggle_debug_mode(self):
        """Переключить debug-режим через менеджер"""
        is_enabled = self.debug_manager.toggle()
        self.log(
            i18n.tr("gui_debug_enabled", "🔧 Debug-режим включён")
            if is_enabled
            else i18n.tr("gui_debug_disabled", "🔧 Debug-режим выключен")
        )

    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            config_mgr = get_config_manager()
            self.config.update(config_mgr.get_all())

            # ✅ ИСПРАВЛЕНО: Инициализируем настройки движков если их нет
            engine_keys = ["google", "mymemory", "deepl", "bing", "deeplx", "translators", "libre", "argos"]
            default_enabled = ["google", "mymemory", "deepl", "bing"]  # Движки по умолчанию
            for key in engine_keys:
                config_key = f"engine_{key}_enabled"
                if config_key not in self.config:
                    self.config[config_key] = (key in default_enabled)
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")

    def save_config(self):
        """Сохранение конфигурации в файл с повторными попытками"""
        import time

        config_mgr = get_config_manager()
        for attempt in range(MAX_SAVE_RETRIES):
            try:
                config_mgr.update(self.config)
                self.debug_manager.log_config_change("save_config", None, "Конфигурация сохранена")
                return
            except PermissionError:
                if attempt < MAX_SAVE_RETRIES - 1:
                    time.sleep(SAVE_RETRY_DELAY)
                else:
                    self.log("Ошибка сохранения конфигурации: файл заблокирован")
                    self.debug_manager.log_error("Файл конфигурации заблокирован")
            except Exception as e:
                self.log(f"Ошибка сохранения конфигурации: {e}")
                self.debug_manager.log_error(f"Ошибка сохранения: {e}", e)
                return

    def _on_save_settings(self, options: dict):
        """Обработчик сохранения настроек из вкладки Settings.
        Принимает options из SettingsTab и сохраняет конфигурацию.
        """
        if options:
            self.config.update(options)
            self.debug_manager.log_action("Конфигурация обновлена из настроек", category="gui")
        self.save_config()

    def add_to_history(self, operation: str, details: str = ""):
        """Добавить операцию в историю"""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "operation": operation,
            "details": details,
        }
        self.operation_history.append(entry)
        self.log(f"[{entry['timestamp']}] {operation}: {details}")
        # Debug: логируем каждое действие пользователя
        self.debug_manager.log_event(operation, "History", details)

    def show_history(self):
        """Показать историю операций"""
        show_history(self.root, self.operation_history)

    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        logger.debug("Начало setup_ui()")

        # Строим UI через UIBuilder
        # ✅ ИСПРАВЛЕНО: Используем self.callbacks (уже создан в __init__)
        ui_builder = UIBuilder(
            self.root,
            self.config,
            self.tab_manager,
            self.callbacks,  # ✅ Используем self.callbacks
            main_paned=self.main_paned,
            notebook=self.notebook,
        )
        widgets = ui_builder.build()

        # Сохраняем все виджеты
        for key, value in widgets.items():
            setattr(self, key, value)

        # Инициализация обработчиков
        self._init_handlers()

        # Инициализация системы переводов
        self._init_i18n_system()

        # Главное меню (после создания всех компонентов)
        self.setup_menu()

        # Система скрываемых вкладок
        self._setup_hideable_tabs()

        # Контекстное меню для вкладок
        self.notebook.bind("<Button-3>", self._on_tab_right_click)

        # ✅ Debug: логируем переключение вкладок
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Применяем шрифты и цвета из конфига
        self._apply_fonts()
        self._apply_colors()

    def _on_tab_changed(self, event=None):
        """Обработчик переключения вкладки"""
        try:
            tab_index = self.notebook.index("current")
            tab_name = self.notebook.tab(tab_index, "text")
            self.debug_manager.log_tab_switch(tab_name)
        except Exception:
            pass

    def setup_menu(self):
        """Настройка главного меню"""
        logger.debug("Начало setup_menu()")

        # ✅ ИСПРАВЛЕНО: Обновляем self.callbacks (уже создан в __init__)
        self.callbacks.update({
            "open_mods": self._menu_open_mods,
            "save_settings": self._menu_save_settings,
            "clear_log": self._menu_clear_log,
            "show_history": self.show_history,
            "show_all_tabs": self._show_all_tabs,
            "change_theme": self._change_theme,
            "start_verification": self.start_verification,
            "start_full_verification": self.start_full_verification,
            "run_integrity_check": self.run_integrity_check,
            "run_game_data_load": self.run_game_data_load,
            "show_documentation": self._show_documentation,
            "show_about": self._show_about,
            "show_shortcuts": self._show_shortcuts,
            "show_language_selector": self._show_language_selector,
            "show_debug_log": self.show_debug_log,
            "toggle_debug_mode": self.toggle_debug_mode,
            "get_theme_names": get_theme_names,
            "import_translations": self._show_import_translations,  # ✅ НОВОЕ
            "show_glossary_editor": self._show_glossary_editor,  # ✅ НОВОЕ
            "load_mod_glossary": self._show_mod_glossary_import,
        })

        logger.debug(f"self.callbacks['show_glossary_editor'] = {self.callbacks.get('show_glossary_editor')}")
        logger.debug(f"self._menu_clear_log = {getattr(self, '_menu_clear_log', 'NOT FOUND')}")

        # ✅ ИСПРАВЛЕНО: Передаём self.callbacks (уже обновлён)
        menu_builder = MenuBuilder(self.root, self.config, self.callbacks)
        logger.debug("MenuBuilder создан")

        menu_builder.build()
        logger.debug("MenuBuilder.build() завершён")

        # Сохраняем ссылки
        self._theme_var = menu_builder.get_theme_var()
        self._tabs_menu = menu_builder.get_tabs_menu()
        self.menubar = menu_builder.menubar
        logger.debug(f"menubar = {self.menubar}")
        logger.debug(f"root.menu = {self.root['menu'] if 'menu' in self.root.keys() else 'NOT SET'}")

    def setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш с поддержкой всех раскладок"""
        # ✅ Инициализируем HotkeyManager для мультираскладочной поддержки
        self.hotkey_manager = HotkeyManager(self.root)

        # Файл
        self.hotkey_manager.register(
            "Ctrl+O",
            lambda e: self._menu_open_mods(),
            tooltip_text="Открыть папку модов (Ctrl+O / Ctrl+Щ)",
        )
        self.hotkey_manager.register(
            "Ctrl+S",
            lambda e: self._menu_save_settings(),
            tooltip_text="Сохранить настройки (Ctrl+S / Ctrl+Ы)",
        )

        # Лог
        self.hotkey_manager.register(
            "Ctrl+L",
            lambda e: self.log_panel.clear(),
            tooltip_text="Очистить лог (Ctrl+L / Ctrl+Д)",
        )
        self.hotkey_manager.register(
            "Ctrl+H",
            lambda e: self.show_history(),
            tooltip_text="История операций (Ctrl+H / Ctrl+Р)",
        )

        # Справка и действия
        self.hotkey_manager.register(
            "F1", lambda e: self._show_shortcuts(), tooltip_text="Горячие клавиши (F1)"
        )
        self.hotkey_manager.register(
            "F5", lambda e: self.start_verification(), tooltip_text="Быстрая проверка (F5)"
        )
        self.hotkey_manager.register(
            "F6", lambda e: self.start_full_verification(), tooltip_text="Полная проверка (F6)"
        )

    def _apply_ttkbootstrap_theme(self, theme_name):
        """Применить тему ttkbootstrap"""
        apply_theme(self.style, theme_name)

    def _get_font_tuple(self, key, default_family, default_size):
        """Получить шрифт из конфига в формате (family, size)"""
        return get_font_tuple(self.config, key, default_family, default_size)

    def _apply_fonts(self):
        """Применить шрифты из конфига ко всем виджетам"""
        widgets = {}
        if hasattr(self, "log_panel"):
            widgets["log_text"] = self.log_panel.log_text
        if hasattr(self, "status_bar"):
            widgets["status_label"] = self.status_bar.status_label
        apply_fonts(self.config, self.style, widgets, self.log)

    def _apply_colors(self):
        """Применить пользовательские цвета из конфига ко всем виджетам"""
        widgets = {}
        if hasattr(self, "log_panel"):
            widgets["log_text"] = self.log_panel.log_text
        apply_colors(self.config, self.style, widgets, self.log)

    def _change_theme(self, theme_name):
        """Сменить тему оформления"""
        from gui.styling.icon_manager import icons

        old_theme = self.config.get("theme", "light")
        change_theme(self.config, self.style, theme_name, self.log)
        self._apply_fonts()
        self._apply_colors()
        self.save_config()

        # Обновляем иконки для новой темы
        icons.set_theme(theme_name)
        self._rebuild_menu()

        # ✅ Обновляем цветовые теги дерева зависимостей
        if hasattr(self, "tab_dependencies"):
            self.tab_dependencies.update_tree_colors()

        # Debug: логируем смену темы
        self.debug_manager.log_theme_change(old_theme, theme_name)

    def _menu_open_mods(self):
        """Открыть папку модов"""
        folder = filedialog.askdirectory(
            title=i18n.tr("gui_select_mods_folder", "Выберите папку с модами")
        )
        if folder:
            get_paths_config().set_mods_path(folder, save=True)
            self.add_to_history(i18n.tr("gui_history_opened_folder", "Открыта папка"), folder)
            # Debug: логируем выбор папки
            self.debug_manager.log_file_operation("select_folder", folder, "Папка модов выбрана")
            # Обновляем список модов
            self.tab_mods_manager.set_mods_folder(folder)
            # Обновляем папку во вкладке перевода
            self.tab_translation.mods_selector.set(folder)
            # Обновляем папку во вкладке редактора
            self.tab_editor.mods_folder = folder

    def _menu_save_settings(self):
        """Сохранить настройки"""
        self.debug_manager.log_action("Сохранение настроек", category="gui")
        self.save_config()

        self.add_to_history(i18n.tr("gui_history_settings_saved", "Настройки сохранены"))

        messagebox.showinfo(
            i18n.tr("gui_success", "Успех"),
            i18n.tr(
                "gui_settings_saved", "Настройки успешно сохранены")
        )

    def _menu_clear_log(self):
        """Очистить лог отладки"""
        self.debug_manager.log_action("Очистка лога", category="gui")
        try:
            # Пробуем через debug_logger
            if hasattr(self, 'debug_logger'):
                from utils.debug_logger import DebugLogger
                if isinstance(self.debug_logger, DebugLogger):
                    self.debug_logger.clear_log()
            # Или через log_panel
            if hasattr(self, 'log_panel') and hasattr(self.log_panel, 'clear'):
                self.log_panel.clear()
            messagebox.showinfo(
                i18n.tr("gui_success", "Успех"),
                i18n.tr("log_cleared", "Лог отладки успешно очищен")
            )
        except Exception as e:
            messagebox.showerror(
                i18n.tr("error", "Ошибка"),
                f"Не удалось очистить лог: {e}"
            )

    def _show_about(self):
        """Показать окно "О программе" """
        self.debug_manager.log_action("Открыто окно 'О программе'", category="gui")
        show_about(self.root)

    def _show_shortcuts(self):
        """Показать горячие клавиши"""
        self.debug_manager.log_action("Открыты горячие клавиши", category="gui")
        show_shortcuts(self.root)

    def _init_i18n_system(self):
        """Инициализировать менеджер интернационализации"""
        from gui.core.i18n_manager import I18nManager

        self.i18n_manager = I18nManager(
            root=self.root,
            notebook=self.notebook,
            status_bar=getattr(self, "status_bar", None),
            config=self.config,
            log_fn=self.log,
        )
        self.i18n_manager.set_rebuild_menu_callback(self._rebuild_menu)
        self.i18n_manager.initialize()

    def _load_saved_language(self):
        """Загрузить сохранённый язык"""
        self.i18n_manager.load_saved_language()

    def _save_current_language(self):
        """Сохранить текущий язык"""
        self.i18n_manager.save_current_language()

    def _apply_ui_language(self):
        """Применить язык к интерфейсу"""
        self.i18n_manager.apply_language()
        # Debug: логируем изменение языка
        lang_code = self.config.get("interface_language", "ru")
        lang_names = {"ru": "Русский", "en": "English", "uk": "Українська"}
        lang_name = lang_names.get(lang_code, lang_code)
        self.debug_manager.log_language_change("previous", lang_name)

    def _rebuild_tabs(self):
        """Обновить названия всех вкладок"""
        try:
            tab_count = self.notebook.index("end")
            tab_names = [
                i18n.tr("tab_translation", "🌐 Перевод"),
                i18n.tr("tab_verification", "✅ Верификация"),
                i18n.tr("tab_duplicates", "🔄 Дубликаты"),
                i18n.tr("tab_settings", "⚙️ Настройки"),
                i18n.tr("tab_mods", "📦 Моды"),
                i18n.tr("tab_filters", "📝 Фильтры"),
                i18n.tr("tab_dependencies", "🔗 Зависимости"),
                i18n.tr("tab_editor", "✏️ Редактор"),
                i18n.tr("tab_log", "📋 Лог"),
            ]

            for i, name in enumerate(tab_names):
                if i < tab_count:
                    try:
                        self.notebook.tab(i, text=name)
                    except Exception:
                        pass
        except Exception as e:
            print("Ошибка перестройки вкладок:", e)

    def _rebuild_menu(self):
        """Перестроить главное меню с текущим языком"""

        # Удаляем старое меню
        if hasattr(self, "menubar"):
            self.root.config(menu="")
            del self.menubar

        # ✅ ИСПРАВЛЕНО: Обновляем self.callbacks вместо создания нового dict
        self.callbacks.update({
            "open_mods": self._menu_open_mods,
            "save_settings": self._menu_save_settings,
            "clear_log": self.log_panel.clear,
            "show_history": self.show_history,
            "show_all_tabs": self._show_all_tabs,
            "change_theme": self._change_theme,
            "start_verification": self.start_verification,
            "start_full_verification": self.start_full_verification,
            "run_integrity_check": self.run_integrity_check,
            "run_game_data_load": self.run_game_data_load,
            "show_documentation": self._show_documentation,
            "show_about": self._show_about,
            "show_shortcuts": self._show_shortcuts,
            "show_language_selector": self._show_language_selector,
            "show_debug_log": self.show_debug_log,
            "toggle_debug_mode": self.toggle_debug_mode,
            "cancel_translation": self.cancel_translation,
            "get_theme_names": get_theme_names,
            "load_mod_glossary": self._show_mod_glossary_import,
        })
        # ✅ show_glossary_editor уже есть в self.callbacks (добавлено в setup_menu)

        menu_builder = MenuBuilder(self.root, self.config, self.callbacks)
        menu_builder.build()

        # Сохраняем ссылки
        self._theme_var = menu_builder.get_theme_var()
        self._tabs_menu = menu_builder.get_tabs_menu()
        self.menubar = menu_builder.menubar

    def _show_language_selector(self):
        """Выбор языка"""
        self.debug_manager.log_action("Открыт выбор языка", category="gui")

        dlg = tk.Toplevel(self.root)
        dlg.title(i18n.tr("menu_language", "Язык интерфейса"))
        dlg.geometry("320x300")
        dlg.transient(self.root)
        dlg.grab_set()

        # Заголовок с текущим языком
        ttk.Label(
            dlg,
            text=i18n.tr("language_select_title", "Выберите язык:"),
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(10, 5))

        # Показываем текущий язык
        current_label = ttk.Label(
            dlg,
            text=f"({i18n.get_current_language_with_name()})",
            font=("Segoe UI", 9),
            bootstyle="info",
        )
        current_label.pack(pady=(0, 10))

        var = tk.StringVar(value=i18n.current_language)
        for code in i18n.get_available_languages():
            # Помечаем текущий язык
            is_current = code == i18n.current_language
            text = (
                f"✓ {i18n.get_language_name(code)}"
                if is_current
                else f"  {i18n.get_language_name(code)}"
            )
            ttk.Radiobutton(dlg, text=text, variable=var, value=code).pack(
                anchor="w", padx=20, pady=2
            )

        def apply():
            lang = var.get()
            if i18n.set_language(lang):
                self.config["ui_language"] = lang
                try:
                    config_mgr = get_config_manager()
                    config_mgr.set("ui_language", lang)
                except OSError:
                    pass
                dlg.destroy()

                # Применяем язык без перезапуска
                self._apply_ui_language()

                self.log(f"✅ Язык изменён на: {i18n.get_language_name(lang)}")
                self.status_bar.show_toast(f"Язык: {i18n.get_language_name(lang)}", "success")
            else:
                from tkinter import messagebox

                messagebox.showerror(
                    "Ошибка",
                    f"Язык '{lang}' не найден. Доступные языки: {', '.join(i18n.get_available_languages())}",
                )

        ttk.Button(
            dlg, text=i18n.tr("language_apply_btn", "Применить"), command=apply, bootstyle="success"
        ).pack(pady=10)

    def _register_i18n_widget(self, widget, key):
        """Зарегистрировать виджет с i18n ключом для автоматического обновления"""
        widget._i18n_key = key

    def _restart_application(self):
        """Перезапустить приложение"""
        self.debug_manager.log_action("Перезапуск приложения", category="gui")
        import os
        import sys

        # Сохраняем состояние
        self.save_config()

        # Перезапускаем процесс
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def _show_documentation(self):
        """Показать документацию"""
        self.debug_manager.log_action("Открыта документация", category="gui")
        show_documentation(self.root)

    def set_status(self, message):
        """Установка статусного сообщения"""
        self.status_bar.set_status(message)
        # Debug: логируем изменение статуса
        self.debug_manager.log_status_change(message)

    def start_progress(self):
        """Запуск прогресс-бара"""
        self.status_bar.start_progress()
        self.debug_manager.log_progress("start")

    def stop_progress(self):
        """Остановка прогресс-бара"""
        self.status_bar.stop_progress()
        self.debug_manager.log_progress("stop")

    def set_progress(self, value):
        """Установка значения прогресс-бара (0-100)"""
        self.status_bar.set_progress(value)
        self.debug_manager.log_progress("update", value)

    def flush_log(self):
        """Принудительное обновление лога"""
        self.log_panel.flush()

    def _init_handlers(self):
        """Инициализация обработчиков событий"""
        self.verification_handler = VerificationHandler(
            log_callback=self.log,
            status_callback=self.set_status,
            progress_callback=self.set_progress,
            result_callback=self.tab_verification.log,  # Обратная совместимость
            batch_result_callback=self.tab_verification.log_batch,  # ✅ НОВОЕ: пакетная вставка
            stop_progress_callback=self.stop_progress,  # ✅ Сброс прогресс-бара
        )
        self.verification_handler.show_toast = self.status_bar.show_toast  # ✅ Toast
        self.verification_handler.update_stats = self.status_bar.update_stats  # ✅ Статистика

        self.translation_handler = TranslationHandler(
            log_callback=self.log,
            status_callback=self.set_status,
            progress_callback=self.set_progress,
            stop_progress_callback=self.stop_progress,  # ✅ Сброс прогресс-бара
            config=self.config,
        )
        self.translation_handler.show_toast = self.status_bar.show_toast  # ✅ Toast
        self.translation_handler.update_stats = self.status_bar.update_stats  # ✅ Статистика

        self.duplicate_handler = DuplicateMergeHandler(
            log_callback=self.log,
            status_callback=self.set_status,
            progress_callback=self.set_progress,
            stop_progress_callback=self.stop_progress,  # ✅ Сброс прогресс-бара
        )
        self.duplicate_handler.show_toast = self.status_bar.show_toast  # ✅ Toast
        self.duplicate_handler.update_stats = self.status_bar.update_stats  # ✅ Статистика

        self.integrity_handler = IntegrityCheckHandler(
            log_callback=self.log,
            status_callback=self.set_status,
            progress_callback=self.set_progress,
            parent_window=self.root,  # ✅ НОВОЕ: для показа окна результатов
            stop_progress_callback=self.stop_progress,  # ✅ Сброс прогресс-бара
        )
        self.integrity_handler.show_toast = self.status_bar.show_toast  # ✅ Toast
        self.integrity_handler.update_stats = self.status_bar.update_stats  # ✅ Статистика

        # ✅ Workers для дубликатов и целостности
        self.duplicate_worker = None
        self.integrity_worker = None

        # ✅ Менеджер горячих клавиш (работает на всех раскладках)
        self.hotkey_manager = HotkeyManager(self.root)
        setup_default_hotkeys(self.hotkey_manager, self)

        self.game_data_loader = GameDataLoader(
            config=self.config,
            log_callback=self.log,
            status_callback=self.set_status,
            progress_callbacks=None,
            save_callback=self.save_config,
            game_data_processor=game_data_processor,
        )

    def _on_save_settings(self, options):
        """Сохранение настроек"""
        self.debug_manager.log_action("Сохранение настроек через вкладку настроек", category="gui")
        # ✅ ИСПРАВЛЕНО: Используем update для сохранения всех настроек (кроме фильтров)
        self.config.update(options)
        self.save_config()

        self.add_to_history(i18n.tr("gui_history_settings_saved", "Настройки сохранены"))

        messagebox.showinfo(
            i18n.tr("gui_success", "Успех"),
            i18n.tr(
                "gui_settings_saved", i18n.tr("gui_history_settings_saved", "Настройки сохранены")
            ),
        )

    def _on_save_filters_config(self, filters_config):
        """
        Обработчик сохранения настроек фильтров.
        Сохраняет напрямую в filters_config.json.

        Args:
            filters_config: Конфигурация фильтров из gui_filters_tab
        """
        self.debug_manager.log_action("Сохранение настроек фильтров", category="gui")

        # ✅ Сохраняем напрямую в filters_config.json
        import json
        try:
            with open("filters_config.json", "w", encoding="utf-8") as f:
                json.dump(filters_config, f, ensure_ascii=False, indent=4)
            self.add_to_history(
                i18n.tr("gui_history_filters_saved", "Настройки фильтров сохранены"),
                f"Whitelist: {len(filters_config.get('whitelist_tags', []))} тегов",
            )
        except Exception as e:
            self.debug_manager.log_error(f"Ошибка сохранения filters_config.json: {e}", e)
            messagebox.showerror(i18n.tr("msg_error", "Ошибка"), f"Не удалось сохранить настройки фильтров: {e}")

    def _save_filters_config(self):
        """Wrapper for _on_save_filters_config - gets config from tab_filters and saves it"""
        if hasattr(self, "tab_filters") and self.tab_filters:
            filters_config = self.tab_filters.get_filters_config()
            self._on_save_filters_config(filters_config)

    def _on_load_settings(self):
        """Загрузка настроек"""
        self.debug_manager.log_action("Загрузка настроек", category="gui")
        self.load_config()
        self.tab_settings.apply_config(self.config)
        # ✅ ОБНОВЛЯЕМ все вкладки
        if hasattr(self, "tab_translation") and self.tab_translation:
            self.tab_translation.apply_config(self.config)
        # ✅ Фильтры загружаются автоматически из filters_config.json при создании FiltersTab
        self.add_to_history(i18n.tr("gui_history_settings_loaded", "Настройки загружены"))

    # Функции верификации
    def start_verification(self, options=None):
        """Запуск верификации модов"""
        options = options or {}

        mods_folder = get_paths_config().get_mods_path()
        if not mods_folder:
            self.status_bar.show_toast(
                i18n.tr("gui_toast_select_mods", "Выберите папку с модами!"), "warning"
            )
            return

        # Очищаем предыдущие результаты
        self.tab_verification.clear()

        checks = []
        if options.get("verify_translations", True):
            checks.append("translations")
        if options.get("verify_dependencies", True):
            checks.append("dependencies")
        if options.get("verify_conflicts", True):
            checks.append("conflicts")

        # ✅ ИСПРАВЛЕНО: Получаем язык из options и сохраняем в config
        verification_language = options.get(
            "verification_language", self.config.get("verification_language", "Russian")
        )
        self.config["verification_language"] = verification_language  # Сохраняем

        self.add_to_history(
            i18n.tr("gui_history_verification", "Верификация"),
            f"Папка: {mods_folder}, Язык: {verification_language}",
        )

        # Debug: логируем запуск верификации
        self.debug_manager.log_action(
            f"Верификация запущена: {mods_folder}, проверки: {', '.join(checks)}, язык: {verification_language}",
            category="verification",
        )

        self.status_bar.show_toast(
            i18n.tr("gui_toast_verification_started", "Верификация запущена..."), "info"
        )
        # ✅ ИСПРАВЛЕНО: Передаём язык верификации
        self.run_verification_async(
            mods_folder, checks, verification_language=verification_language
        )

    def start_full_verification(self, options=None):
        """Запуск полной проверки"""
        options = options or {}

        mods_folder = get_paths_config().get_mods_path()
        if not mods_folder:
            messagebox.showwarning(
                i18n.tr("gui_warning", "Предупреждение"),
                i18n.tr("gui_no_mods_folder_warning", "Выберите папку с модами"),
            )
            return

        # Очищаем предыдущие результаты
        self.tab_verification.clear()

        # ✅ ИСПРАВЛЕНО: Получаем язык из options
        verification_language = options.get(
            "verification_language", self.config.get("verification_language", "Russian")
        )
        self.config["verification_language"] = verification_language

        self.add_to_history(
            i18n.tr("gui_history_full_check", "Полная проверка"),
            f"Папка: {mods_folder}, Язык: {verification_language}",
        )
        # ✅ ИСПРАВЛЕНО: Передаём язык верификации
        self.run_verification_async(
            mods_folder, is_full=True, verification_language=verification_language
        )

    # Обработчики сигналов
    def _on_log_event(self, event):
        """Обработка событий логирования"""
        if hasattr(event, "message"):
            self.log(event.message)
        if hasattr(event, "level") and hasattr(event.level, "name"):
            if event.level.name == "ERROR":
                self.set_status(f"Ошибка: {event.message}")
            elif event.level.name == "WARNING":
                self.set_status(f"Предупреждение: {event.message}")

    # Асинхронные методы
    def run_verification_async(
        self, mods_folder, checks=None, is_full=False, verification_language=None
    ):
        """Запуск асинхронной верификации (потокобезопасно)"""
        # ✅ ИСПРАВЛЕНО: Используем переданный язык или fallback на config
        verification_language = verification_language or self.config.get(
            "verification_language", "Russian"
        )

        # Для полной проверки - все проверки (пустой список = все проверки)
        if is_full:
            checks = []  # Пустой список означает все 20 проверок

        worker = VerificationWorker(
            mods_folder=mods_folder,
            checks=checks or [],
            language=verification_language,
            logger=self.debug_manager.debug_logger if self.debug_manager.is_enabled else None,
            game_path=self.config.get("game_path", ""),  # Передаём путь к игре
        )

        # Потокобезопасные callbacks через root.after()
        handler = self.verification_handler
        if handler:

            def on_progress_cb(p, t, m):
                self.root.after(0, handler.on_progress, p, t, m)

            def on_complete_cb(r):
                self.root.after(0, handler.on_complete, r)

            def on_error_cb(e):
                self.root.after(0, handler.on_error, e)

            worker.on_progress(on_progress_cb)
            worker.on_complete(on_complete_cb)
            worker.on_error(on_error_cb)

        self.start_progress()  # ✅ Запуск прогресс-бара
        worker.start()
        return worker

    def _get_enabled_engines(self):
        """Собрать активные движки из конфига."""
        engine_keys = ["google", "mymemory", "deepl", "bing", "deeplx", "translators", "libre", "argos"]
        enabled = []
        for key in engine_keys:
            config_key = f"engine_{key}_enabled"
            if config_key in self.config:
                if self.config[config_key]:
                    enabled.append(key)
            else:
                # Используем умолчание: включён если в списке по умолчанию
                if key in ["google", "mymemory", "deepl", "bing"]:
                    enabled.append(key)
        # ✅ ИСПРАВЛЕНО: Возвращаем список (даже пустой), а не None
        # None заставляет AutoTranslator использовать DEFAULT_ENGINES
        self.debug_manager.log_action(f"Собраны движки: {enabled}", category="translation")
        return enabled  # Пустой список = ни одного движка, None = использовать дефолтные

    def start_translation(self, options=None):
        """Запуск перевода модов"""
        options = options or {}

        # ✅ НОВОЕ: Сохраняем настройки перевода в config
        for key in ["mods_folder", "output_folder", "source_language", "target_language", "force_update", "fuzzy", "use_morphy", "auto_detect_source_lang"]:
            if key in options:
                self.config[key] = options[key]

        # ✅ НОВОЕ: Сохраняем source_languages если передан
        if "source_languages" in options:
            self.config["source_languages"] = options["source_languages"]
        self.save_config()

        mods_folder = options.get("mods_folder", "")
        output_folder = options.get("output_folder", "")
        source_lang = options.get("source_language", "English")
        source_langs = options.get("source_languages", [source_lang])
        target_lang = options.get("target_language", "Russian")
        selected_mods = options.get("selected_mods", [])
        force_update = options.get("force_update", False)
        fuzzy = options.get("fuzzy", True)
        auto_detect_source_lang = options.get("auto_detect_source_lang", True)

        # ✅ ПРЯМО ЧИТАЕМ движки из UI (tab_settings) - ВСЕГДА актуально!
        engine_names = []
        if hasattr(self, "tab_settings") and self.tab_settings:
            try:
                for key in ["google", "mymemory", "deepl", "bing", "deeplx", "translators", "libre", "argos"]:
                    if key in self.tab_settings.engine_vars:
                        var = self.tab_settings.engine_vars[key]
                        is_checked = var.get()  # ✅ Читаем значение BooleanVar
                        if is_checked:
                            engine_names.append(key)
                        # ✅ ОТЛАДКА: Показываем состояние каждого движка
                        self.debug_manager.log_action(f"DEBUG start_translation: движок {key} = {is_checked}", category="translation")

                # ✅ ОТЛАДКА: Показываем что прочитано из UI
                self.debug_manager.log_action(f"DEBUG start_translation: engine_names из UI = {engine_names}", category="translation")
            except Exception as e:
                self.debug_manager.log_error(f"Ошибка чтения движков из UI: {e}", e)
                engine_names = []  # Пустой = ни одного движка

        # ✅ ОТЛАДКА: Показываем что передаём в run_translation_async
        self.debug_manager.log_action(f"DEBUG start_translation: ПЕРЕДАЁМ engine_names={engine_names}", category="translation")

        if not mods_folder:
            self.status_bar.show_toast(
                i18n.tr("gui_toast_select_mods", "Выберите папку с модами!"), "warning"
            )
            return

        if not output_folder:
            self.status_bar.show_toast(
                i18n.tr("gui_toast_select_output", "Выберите папку вывода!"), "warning"
            )
            return

        self.add_to_history(
            i18n.tr("gui_history_translation", "Перевод"),
            f"{source_lang} -> {target_lang}: {mods_folder}",
        )
        self.status_bar.show_toast(f"Перевод запущен: {source_lang} → {target_lang}", "info")

        # ✅ НОВОЕ: Передаём конфиг в handler для Morphy.py
        if self.translation_handler:
            self.translation_handler.set_config(options)

        self.run_translation_async(
            mods_folder, output_folder, source_lang, source_langs, target_lang, selected_mods, force_update, fuzzy, engine_names, auto_detect_source_lang,
        )

        # ✅ ОТЛАДКА: Показываем какие движки переданы
        self.debug_manager.log_action(f"Переданы движки в run_translation_async: {engine_names}", category="translation")

    def run_translation_async(
        self,
        mods_folder,
        output_folder,
        source_lang,
        source_langs,
        target_lang,
        selected_mods=None,
        force_update=False,
        fuzzy=True,
        engine_names=None,
        auto_detect_source_lang=True,
    ):
        """Запуск асинхронного перевода"""
        # ✅ ОТЛАДКА: Показываем полученные языки
        self.debug_manager.log_action(f"DEBUG run_translation_async: source_lang={source_lang}, source_langs={source_langs}", category="translation")

        # ✅ ОТЛАДКА: Показываем какие движки получены
        self.debug_manager.log_action(f"DEBUG run_translation_async: ПОЛУЧИЛИ engine_names={engine_names}", category="translation")

        # ✅ ОТЛАДКА: Показываем какие движки передаём в Worker
        if engine_names:
            self.debug_manager.log_action(f"DEBUG run_translation_async: ПЕРЕДАЁМ в Worker engine_names={engine_names}", category="translation")
        else:
            self.debug_manager.log_action("DEBUG run_translation_async: engine_names ПУСТОЙ или None", category="translation")

        # Получаем режим перевода из конфига (separate или inplace)
        translation_mode = self.config.get("translation_mode", "separate")
        print(f"DEBUG GUI: Read translation_mode = '{translation_mode}'")
        self.debug_manager.log_action(
            f"DEBUG: translation_mode from config = '{translation_mode}'", category="translation"
        )

        # Debug: логируем запуск перевода
        self.debug_manager.log_action(
            f"Запуск перевода: {source_lang} -> {target_lang}, режим: {translation_mode}, force_update: {force_update}, fuzzy: {fuzzy}"
        )
        self.debug_manager.log_file_operation(
            "translation_start",
            mods_folder,
            f"Output: {output_folder}, Mode: {translation_mode}, Selected mods: {selected_mods}, Force: {force_update}, Fuzzy: {fuzzy}",
        )

        # Создаём sink который пишет в UI лог через callback
        def ui_sink(message):
            """Sink который пишет сообщения в UI лог (потокобезопасный)"""
            try:
                msg = message.strip()
                if self.log and self.root:
                    # ✅ Безопасный вызов UI из любого потока через .after()
                    self.root.after(0, self.log, msg)
            except Exception:
                pass

        if self.debug_manager.is_enabled:
            # Debug режим - используем debug_logger
            worker_logger = self.debug_manager.debug_logger
        else:
            # Обычный режим - создаём logger который пишет в UI
            logger_name = f"translation.{os.path.basename(mods_folder)}"
            worker_logger = logger.bind(name=logger_name)

            # ✅ Удаляем предыдущий sink если он был
            if hasattr(self, '_ui_sink_id'):
                try:
                    logger.remove(self._ui_sink_id)
                except Exception:
                    pass

            # ✅ Добавляем custom sink для вывода в UI
            self._ui_sink_id = logger.add(
                ui_sink, level="INFO", format="{message}",
                filter=lambda record: record["extra"].get("name") == logger_name
            )

        # ✅ ИСПРАВЛЕНО: Используем фабрику для создания правильного Worker-а
        from workers.factory import create_translation_worker

        self.translation_worker = create_translation_worker(
            mode=translation_mode,
            mods_folder=mods_folder,
            source_lang=source_lang,
            source_langs=source_langs,
            target_lang=target_lang,
            output_folder=output_folder,
            logger=worker_logger,
            selected_mods=selected_mods,
            force_update=force_update,
            fuzzy=fuzzy,
            engine_names=engine_names,
            auto_detect_source_lang=auto_detect_source_lang,
        )

        # ✅ ОТЛАДКА: Показуємо які движки передані у worker
        self.debug_manager.log_action(f"DEBUG: worker створено з engine_names={engine_names}", category="translation")

        # ✅ Устанавливаем root для потокобезопасных callbacks
        self.translation_worker.set_tk_root(self.root)

        handler = self.translation_handler
        worker = self.translation_worker
        if handler:
            # ✅ Потокобезопасные callbacks через root.after()
            worker.on_progress(
                lambda p, t, m, h=handler: self.root.after(0, h.on_progress, p, t, m)
            )
            worker.on_complete(
                lambda r, h=handler: self.root.after(
                    0, lambda: (h.on_complete(r), self.tab_translation.finish_translation(True))
                )
            )
            worker.on_error(
                lambda e, h=handler: self.root.after(
                    0, lambda: (h.on_error(e), self.tab_translation.finish_translation(False))
                )
            )

        self.start_progress()  # ✅ Запуск прогресс-бара
        worker.start()
        return worker

    def cancel_translation(self):
        """Отмена текущего перевода."""
        if hasattr(self, "translation_worker") and self.translation_worker:
            self.translation_worker.stop(timeout=2.0)
            self.set_status(i18n.tr("gui_translation_cancelled", "Перевод отменён"))
            # Debug: логируем отмену перевода
            self.debug_manager.log_action("Перевод отменён пользователем")
            self.stop_progress()
            self.status_bar.show_toast(i18n.tr("gui_toast_cancelled", "Перевод отменён"), "warning")
            self.translation_worker = None

    # Функции слияния дубликатов
    def start_duplicate_merge(self, options=None):
        """Запуск слияния дубликатов через DuplicateWorker."""
        options = options or {}

        mods_folder = options.get("mods_folder", "")
        output_folder = options.get("output_folder", "")

        if not mods_folder or not output_folder:
            messagebox.showwarning(
                i18n.tr("gui_warning", "Предупреждение"),
                i18n.tr("duplicates_no_paths_warning", "Выберите папки модов и вывода"),
            )
            return

        self.add_to_history(
            i18n.tr("gui_history_duplicate_merge", "Слияние дубликатов"),
            f"Из: {mods_folder} -> В: {output_folder}",
        )

        # Debug: логируем запуск слияния дубликатов
        self.debug_manager.log_action(
            f"Слияние дубликатов запущено: {mods_folder} -> {output_folder}", category="duplicates"
        )

        # ✅ Используем DuplicateWorker вместо DuplicateRunner
        self.duplicate_worker = DuplicateWorker(
            mods_folder=mods_folder,
            output_folder=output_folder,
            auto_merge=options.get("auto_merge", True),
            create_backup=options.get("create_backup", True),
            logger=self.debug_manager.debug_logger if self.debug_manager.is_enabled else None,
        )

        handler = self.duplicate_handler
        worker = self.duplicate_worker

        if handler:
            # ✅ Потокобезопасные callbacks через root.after()
            worker.on_progress(
                lambda p, t, m, h=handler: self.root.after(0, h.on_progress, p, t, m)
            )
            worker.on_complete(lambda r, h=handler: self.root.after(0, h.on_complete, r))
            worker.on_error(lambda e, h=handler: self.root.after(0, h.on_error, e))

        self.start_progress()  # ✅ Запуск прогресс-бара
        worker.start()

    # Функции настроек
    def run_integrity_check(self, language_filter=None):
        """Запуск проверки целостности через IntegrityWorker.

        Args:
            language_filter: Язык для фильтрации (например, "Russian") или None для всех
        """
        self.add_to_history(i18n.tr("gui_history_integrity_check", "Проверка целостности"))

        mods_folder = get_paths_config().get_mods_path()
        if not mods_folder:
            self.status_bar.show_toast(
                i18n.tr("gui_toast_no_mods_folder", "Укажите папку модов в настройках!"),
                "warning",
            )
            return

        # ✅ НОВОЕ: Если язык не передан явно, берём из настроек
        if language_filter is None:
            language_filter = self.config.get("verification_language", "Все языки")

        # Debug: логируем запуск проверки целостности
        self.debug_manager.log_action(
            f"Проверка целостности запущена: {mods_folder}", category="integrity"
        )

        if language_filter and language_filter != "Все языки":
            self.debug_manager.log_action(f"Фильтр языка: {language_filter}", category="integrity")

        # ✅ Используем IntegrityWorker вместо IntegrityRunner
        self.integrity_worker = IntegrityWorker(
            mods_folder=mods_folder,
            language_filter=language_filter,
            logger=self.debug_manager.debug_logger if self.debug_manager.is_enabled else None,
        ).set_tk_root(self.root)  # ✅ Потокобезопасные callbacks через root.after()

        handler = self.integrity_handler
        worker = self.integrity_worker

        if handler:
            # ✅ Потокобезопасные callbacks через root.after()
            worker.on_progress(
                lambda p, t, m, h=handler: self.root.after(0, h.on_progress, p, t, m)
            )
            worker.on_complete(lambda r, h=handler: self.root.after(0, h.on_complete, r))
            worker.on_error(lambda e, h=handler: self.root.after(0, h.on_error, e))

        self.start_progress()  # ✅ Запуск прогресс-бара
        worker.start()

    def run_game_data_load(self):
        """Загрузка официальных данных игры для использования в качества справочника"""
        from gui.gui_i18n import tr
        from tkinter.simpledialog import askstring

        self.debug_manager.log_action("Загрузка данных игры начата", category="gui")
        game_path = filedialog.askdirectory(
            title=tr("gui_select_game_folder", "Выберите папку с RimWorld")
        )
        if not game_path:
            return

        self.debug_manager.log_file_operation("select_game_folder", game_path)

        # ✅ ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА: Ищем папку Data
        data_path = self._find_game_data_path(game_path)

        if not data_path:
            # Папка Data не найдена, показываем подсказки
            self._show_data_folder_error(game_path)
            return

        # Если нашли в родительской папке, предлагаем использовать её
        if data_path != os.path.join(game_path, "Data"):
            result = messagebox.askyesno(
                tr("gui_data_folder_found", "Папка Data найдена"),
                tr(
                    "gui_data_folder_prompt",
                    f"В указанной папке нет Data, но найдена в:\n{data_path}\n\nИспользовать эту папку?",
                ),
            )
            if result:
                game_path = os.path.dirname(data_path)
            else:
                return

        lang = askstring(
            tr("game_loader_select_language", "Выбор языка"),
            tr("game_loader_language_prompt", "Введите язык для загрузки справочника\n(по умолчанию Russian):"),
            initialvalue=self.config.get("target_language", "Russian"),
        )
        if not lang:
            lang = "Russian"

        self.add_to_history(tr("gui_history_game_data_load", "Загрузка данных игры"), game_path)
        self.log("=" * 50)
        self.debug_manager.log_action(f"Данные игры загружены: {game_path}", category="gui")
        self.log("Загрузка официальных данных игры...")
        self.log("=" * 50)

        thread = threading.Thread(target=self._perform_game_data_load, args=(game_path, lang))
        thread.daemon = True
        thread.start()

    def _find_game_data_path(self, user_path: str) -> str | None:
        """
        Ищет папку Data в указанной директории или выше.

        Проверяет:
        1. user_path/Data
        2. user_path/../Data
        3. user_path/../../Data
        4. user_path/../../../Data

        Args:
            user_path: Путь, указанный пользователем

        Returns:
            Путь к папке Data или None
        """
        variants = [
            os.path.join(user_path, "Data"),
            os.path.join(user_path, "..", "Data"),
            os.path.join(user_path, "..", "..", "Data"),
            os.path.join(user_path, "..", "..", "..", "Data"),
        ]

        for variant in variants:
            normalized = os.path.normpath(variant)
            if os.path.exists(normalized):
                # Дополнительная проверка: есть ли Core в Data
                core_path = os.path.join(normalized, "Core")
                if os.path.exists(core_path):
                    return normalized

        return None

    def _show_data_folder_error(self, game_path: str):
        """
        Показывает подробное сообщение об ошибке с подсказками.

        Args:
            game_path: Путь, который указал пользователь
        """
        self.log(f"❌ Не удалось найти папку Data в: {game_path}")
        self.log(f"   Ожидаемая структура: {game_path}/Data/Core/Languages/")

        # Проверяем распространённые ошибки
        suggestions = []

        # Если путь содержит RimWorldWin64
        if "RimWorldWin64" in game_path or "RimWorldWin64_Data" in game_path:
            suggestions.append(
                "⚠️ Вы указали папку с exe-файлом!\n"
                "   Нужно указать папку выше (где лежит RimWorldWin64.exe)"
            )

        # Проверяем наличие Data в соседней папке
        parent_path = os.path.dirname(game_path)
        if os.path.exists(os.path.join(parent_path, "Data")):
            suggestions.append(
                f"✅ Папка Data найдена в: {parent_path}\n   Укажите эту папку вместо {game_path}"
            )

        # Формируем сообщение
        message = (
            "Не удалось найти папку Data.\n\n"
            f"Проверьте путь:\n{game_path}\n\n"
            "Ожидаемая структура:\n"
            f"  {game_path}/Data/Core/Languages/Russian/\n\n"
        )

        if suggestions:
            message += "💡 Подсказки:\n" + "\n\n".join(suggestions)
        else:
            message += (
                "Возможно, вы указали:\n"
                "  • Папку с exe-файлом (RimWorldWin64)\n"
                "  • Папку с модом вместо папки игры\n"
                "  • Неправильный путь\n\n"
                "Нужно указать папку, где лежит RimWorldWin64.exe"
            )

        messagebox.showwarning(i18n.tr("gui_warning", "Предупреждение"), message)

    def _perform_game_data_load(self, game_path, lang="Russian"):
        """Выполнение загрузки данных игры"""
        try:
            # ✅ ПРОВЕРКА: Ещё раз проверяем наличие Data
            data_path = self._find_game_data_path(game_path)
            if not data_path:
                self.log(f"❌ Ошибка: папка Data не найдена в {game_path}")
                self.set_status(i18n.tr("gui_status_data_not_found", "Ошибка: данные не найдены"))
                self._show_data_folder_error(game_path)
                return

            manager = game_data_processor.GameReferenceManager(game_path=game_path, lang=lang)

            self.set_status(i18n.tr("gui_status_loading_data", "Загрузка данных..."))
            self.start_progress()

            success = manager.load_all_official_data()

            if success:
                db_size = len(manager.reference_db)
                symbols_count = len(manager.special_symbols)

                self.log(f"Загружено {db_size} строк из официальных DLC")
                self.log(f"Найдено {symbols_count} специальных символов/тегов")
                # ✅ ДОБАВЛЕНО: Сохраняем официальные переводы в базу данных
                try:
                    from translation_db import get_translation_db
                    db = get_translation_db(manager.lang)
                    if db:
                        added_glossary = 0
                        added_translations = 0
                        for key, val in manager.reference_db.items():
                            if key and val:
                                db.add_glossary_term(key, val, category="auto",
                                                       description=f"Официальный перевод из {manager.lang}")
                                added_glossary += 1
                                db.add_translation(
                                    key=key,
                                    original=key,
                                    translated=val,
                                    file_name="",
                                    mod_name="official",
                                    source_lang="English",
                                    target_lang=manager.lang,
                                )
                                added_translations += 1
                        self.log(f"✅ Добавлено в глоссарий: {added_glossary} терминов из игры")
                        self.log(f"✅ Добавлено в translations: {added_translations} записей из игры")
                except Exception as e:
                    self.log(f"⚠️ Ошибка сохранения в базу: {e}")

                # Сохраняем путь к игре в конфиг
                self.config["game_path"] = game_path
                self.save_config()

                self.set_status(f"Данные загружены: {db_size} строк, {symbols_count} символов")
                messagebox.showinfo(
                    i18n.tr("gui_success", "Успех"),
                    i18n.tr(
                        "gui_data_load_success",
                        f"Официальные данные загружены:\n- Строк: {db_size}\n- Спецсимволов: {symbols_count}",
                    ),
                )
            else:
                self.log(f"❌ Не удалось загрузить данные из: {data_path}")
                self.set_status(i18n.tr("gui_status_data_not_found", "Ошибка: данные не найдены"))
                messagebox.showwarning(
                    i18n.tr("gui_warning", "Предупреждение"),
                    i18n.tr(
                        "gui_data_load_warning",
                        f"Не удалось найти файлы данных.\nУбедитесь, что игра установлена корректно.\n\nПроверен путь:\n{data_path}",
                    ),
                )

        except Exception as e:
            self.log(f"Ошибка загрузки данных: {e}")
            self.set_status(f"Ошибка: {e}")
            messagebox.showerror(
                i18n.tr("gui_error", "Ошибка"),
                i18n.tr("gui_data_load_error", f"Не удалось загрузить данные игры:\n{e}"),
            )
        finally:
            self.stop_progress()

    def _setup_hideable_tabs(self):
        """Настройка системы скрываемых вкладок"""
        self.tab_manager.apply_hidden_state()

    def _on_tab_right_click(self, event):
        """Обработка правого клика на вкладке"""
        self.debug_manager.log_action("Правый клик на вкладке", category="gui")
        self.tab_manager.on_tab_right_click(event)

    def _hide_tab(self, tab_name):
        """Скрыть вкладку"""
        self.debug_manager.log_action(f"Вкладка скрыта: {tab_name}", category="gui")
        self.tab_manager.hide_tab(tab_name)

    def _show_tab(self, tab_name):
        """Показать скрытую вкладку"""
        self.debug_manager.log_action(f"Вкладка показана: {tab_name}", category="gui")
        self.tab_manager.show_tab(tab_name)

    def _show_all_tabs(self):
        """Показать все вкладки"""
        self.debug_manager.log_action("Показаны все вкладки", category="gui")
        self.tab_manager.show_all_tabs()

    def _update_tabs_menu(self):
        """Обновить меню управления вкладками"""
        self.tab_manager._update_tabs_menu()


def main():
    """Точка входа"""
    # ✅ Инициализация логирования для GUI режима
    from utils.loguru_setup import setup_logging, logger
    from config.debug_config import get_default_debug_config

    config = get_default_debug_config()
    debug_mode = config.log_level == "DEBUG"

    setup_logging(
        debug_mode=debug_mode,
        log_file="debug.log" if config.log_to_file else None,
        warning_log_file="warnings.log" if config.log_to_file else None,
    )

    if debug_mode:
        logger.info("Debug mode enabled from config")

    import atexit

    app = ImprovedGUI()

    # ✅ Debug: логируем завершение приложения
    def on_exit():
        app.debug_manager.log_app_exit()

    atexit.register(on_exit)
    app.root.mainloop()


if __name__ == "__main__":
    main()
