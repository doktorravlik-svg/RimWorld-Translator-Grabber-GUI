import os
import sys
import threading
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Импорт модулей проекта
try:
    from config.config_manager import get_config_manager
    from config.paths_config import get_paths_config
    from duplicates import duplicate_merger
    from integrity import game_data_processor, integrity_checker, mod_verifier
    from translation import translator
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
        """Добавление сообщения в лог (оптимизировано)"""
        self.log_panel.log(message)
        # Debug: логируем каждое действие через менеджер
        self.debug_manager.log_action(message)

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
        self.debug_manager.log_action("Открыт редактор глоссария", category="gui")
        GlossaryEditorDialog(self.root)

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
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")

    def save_config(self):
        """Сохранение конфигурации в файл с повторными попытками"""
        import time

        config_mgr = get_config_manager()
        for attempt in range(MAX_SAVE_RETRIES):
            try:
                config_mgr.update(self.config)
                # Debug: логируем сохранение конфига
                self.debug_manager.log_config_change("save_config", None, "Конфигурация сохранена")
                return  # Успешно сохранено
            except PermissionError:
                if attempt < MAX_SAVE_RETRIES - 1:
                    time.sleep(SAVE_RETRY_DELAY)
                else:
                    self.log(
                        "Ошибка сохранения конфигурации: файл заблокирован, попробуйте закрыть другие программы"
                    )
                    self.debug_manager.log_error("Файл конфигурации заблокирован")
            except Exception as e:
                self.log(f"Ошибка сохранения конфигурации: {e}")
                self.debug_manager.log_error(f"Ошибка сохранения: {e}", e)
                return

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
        # Строим UI через UIBuilder
        callbacks = {
            "save_config": self.save_config,
            "start_translation": self.start_translation,
            "cancel_translation": self.cancel_translation,
            "start_verification": self.start_verification,
            "start_full_verification": self.start_full_verification,
            "start_duplicate_merge": self.start_duplicate_merge,
            "run_integrity_check": self.run_integrity_check,
            "apply_fonts": self._apply_fonts,
            "apply_colors": self._apply_colors,
            "on_save_settings": self._on_save_settings,
            "on_load_settings": self._on_load_settings,
            "on_save_filters_config": self._on_save_filters_config,
            "log": self.log,
            "set_status": self.set_status,
            "start_progress": self.start_progress,
            "stop_progress": self.stop_progress,
            "set_progress": self.set_progress,
        }

        # Сначала создаём TabManager и notebook (ttk уже импортирован в начале файла)
        self.main_paned = ttk.Panedwindow(self.root, orient="vertical")
        # НЕ pack'уем здесь - будет упаковано в ui_builder.build() в правильном порядке
        self.notebook = ttk.Notebook(self.main_paned)
        self.main_paned.add(self.notebook, weight=3)

        self.tab_manager = TabManager(self.notebook, self.config, self.save_config, self.log)
        self.tab_manager.set_tabs_menu(None)  # будет установлено в setup_menu

        ui_builder = UIBuilder(
            self.root,
            self.config,
            self.tab_manager,
            callbacks,
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
        callbacks = {
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
            "get_theme_names": get_theme_names,
            "import_translations": self._show_import_translations,  # ✅ НОВОЕ
            "show_glossary_editor": self._show_glossary_editor,  # ✅ НОВОЕ
        }
        menu_builder = MenuBuilder(self.root, self.config, callbacks)
        menu_builder.build()

        # Сохраняем ссылки
        self._theme_var = menu_builder.get_theme_var()
        self._tabs_menu = menu_builder.get_tabs_menu()
        self.menubar = menu_builder.menubar

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
                "gui_settings_saved", i18n.tr("gui_history_settings_saved", "Настройки сохранены")
            ),
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

        callbacks = {
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
        }
        menu_builder = MenuBuilder(self.root, self.config, callbacks)
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
        self.config["preset_file"] = options.get("preset_file", "")
        self.config["verbose"] = options.get("verbose", False)
        self.config["auto_backup"] = options.get("auto_backup", True)
        self.config["verification_language"] = options.get("verification_language", "Russian")
        self.config["translation_mode"] = options.get("translation_mode", "separate")
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

        Args:
            filters_config: Конфигурация фильтров из gui_filters_tab
        """
        self.debug_manager.log_action("Сохранение настроек фильтров", category="gui")
        self.add_to_history(
            i18n.tr("gui_history_filters_saved", "Настройки фильтров сохранены"),
            f"Whitelist: {len(filters_config.get('whitelist_tags', []))} тегов",
        )

    def _on_load_settings(self):
        """Загрузка настроек"""
        self.debug_manager.log_action("Загрузка настроек", category="gui")
        self.load_config()
        self.tab_settings.apply_config(self.config)
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

    def start_translation(self, options=None):
        """Запуск перевода модов"""
        options = options or {}

        mods_folder = options.get("mods_folder", "")
        output_folder = options.get("output_folder", "")
        source_lang = options.get("source_language", "English")
        target_lang = options.get("target_language", "Russian")
        selected_mods = options.get("selected_mods", [])
        force_update = options.get("force_update", False)
        fuzzy = options.get("fuzzy", True)  # ✅ НОВОЕ: Fuzzy поиск

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
        self.run_translation_async(
            mods_folder, output_folder, source_lang, target_lang, selected_mods, force_update, fuzzy
        )

    def run_translation_async(
        self,
        mods_folder,
        output_folder,
        source_lang,
        target_lang,
        selected_mods=None,
        force_update=False,
        fuzzy=True,  # ✅ НОВОЕ: Fuzzy поиск
    ):
        """Запуск асинхронного перевода"""
        # Получаем режим перевода из конфига (separate или inplace)
        translation_mode = self.config.get("translation_mode", "separate")

        # Debug: логируем запуск перевода
        self.debug_manager.log_action(
            f"Запуск перевода: {source_lang} -> {target_lang}, режим: {translation_mode}, force_update: {force_update}, fuzzy: {fuzzy}"
        )
        self.debug_manager.log_file_operation(
            "translation_start",
            mods_folder,
            f"Output: {output_folder}, Mode: {translation_mode}, Selected mods: {selected_mods}, Force: {force_update}, Fuzzy: {fuzzy}",
        )

        # Создаём logger который пишет в UI лог через callback
        import logging

        class UILogHandler(logging.Handler):
            """Handler который пишет сообщения в UI лог (потокобезопасный)"""

            def __init__(self, log_callback, gui_root):
                super().__init__()
                self.log_callback = log_callback
                self.gui_root = gui_root

            def emit(self, record):
                try:
                    msg = self.format(record)
                    if self.log_callback and self.gui_root:
                        # ✅ Безопасный вызов UI из любого потока через .after()
                        self.gui_root.after(0, self.log_callback, msg)
                except Exception:
                    # В случае ошибки при форматировании - игнорируем
                    self.handleError(record)

        if self.debug_manager.is_enabled:
            # Debug режим - используем debug_logger
            worker_logger = self.debug_manager.debug_logger
        else:
            # Обычный режим - создаём logger который пишет в UI
            logger_name = f"translation.{os.path.basename(mods_folder)}"
            worker_logger = logging.getLogger(logger_name)

            # ✅ Очистка: удаляем старые handler'ы чтобы избежать дублирования
            for handler in worker_logger.handlers[:]:
                worker_logger.removeHandler(handler)

            # Создаём новый handler который пишет в UI через callback
            ui_handler = UILogHandler(self.log, self.root)
            ui_handler.setFormatter(logging.Formatter("%(message)s"))
            worker_logger.addHandler(ui_handler)
            # ✅ Явно устанавливаем уровень логирования
            worker_logger.setLevel(logging.INFO)
            worker_logger.propagate = False  # Не передавать в родительские логгеры

        self.translation_worker = TranslationWorker(
            mods_folder=mods_folder,
            output_folder=output_folder,
            source_lang=source_lang,
            target_lang=target_lang,
            mode=translation_mode,
            logger=worker_logger,
            selected_mods=selected_mods,
            force_update=force_update,
            fuzzy=fuzzy,  # ✅ НОВОЕ: Fuzzy поиск
        )

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
        """Загрузка официальных данных игры для использования в качестве справочника"""
        from gui.gui_i18n import tr

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

        self.add_to_history(tr("gui_history_game_data_load", "Загрузка данных игры"), game_path)
        self.log("=" * 50)
        self.debug_manager.log_action(f"Данные игры загружены: {game_path}", category="gui")
        self.log("Загрузка официальных данных игры...")
        self.log("=" * 50)

        thread = threading.Thread(target=self._perform_game_data_load, args=(game_path,))
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

    def _perform_game_data_load(self, game_path):
        """Выполнение загрузки данных игры"""
        try:
            # ✅ ПРОВЕРКА: Ещё раз проверяем наличие Data
            data_path = self._find_game_data_path(game_path)
            if not data_path:
                self.log(f"❌ Ошибка: папка Data не найдена в {game_path}")
                self.set_status(i18n.tr("gui_status_data_not_found", "Ошибка: данные не найдены"))
                self._show_data_folder_error(game_path)
                return

            manager = game_data_processor.GameReferenceManager(game_path=game_path, lang="Russian")

            self.set_status(i18n.tr("gui_status_loading_data", "Загрузка данных..."))
            self.start_progress()

            success = manager.load_all_official_data()

            if success:
                db_size = len(manager.reference_db)
                symbols_count = len(manager.special_symbols)

                self.log(f"Загружено {db_size} строк из официальных DLC")
                self.log(f"Найдено {symbols_count} специальных символов/тегов")

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
    import atexit

    app = ImprovedGUI()

    # ✅ Debug: логируем завершение приложения
    def on_exit():
        app.debug_manager.log_app_exit()

    atexit.register(on_exit)
    app.root.mainloop()


if __name__ == "__main__":
    main()
