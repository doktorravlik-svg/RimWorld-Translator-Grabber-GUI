# Вкладка настроек приложения
from __future__ import annotations

import json
from loguru import logger
import os
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any, Callable

import ttkbootstrap as ttk
from config.config_manager import get_config_manager
from config.language_constants import SUPPORTED_LANGUAGES
from config.paths_config import get_paths_config
from gui.components.advanced_widgets import (
    AutocompleteCombobox,
    CollapsibleFrame,
    CollapsingFrame,
    ValidatedEntry,
)
from gui.components.gui_components import MultiLanguageSelector
from gui.components.path_entry import PathEntryWithBrowse
from gui.constants import (
    BADGE_PADX,
    BADGE_PADY,
    BUTTON_WIDTH,
    COLOR_PREVIEW_HEIGHT,
    COLOR_PREVIEW_WIDTH,
    DEFAULT_LOG_BG,
    DEFAULT_LOG_TEXT,
    ENTRY_WIDTH_SMALL,
    LABEL_WIDTH,
    PAD_FRAME_X,
    PAD_X,
    PAD_Y,
    PADX_LARGE,
    PADY_LARGE,
    PADY_SMALL,
    PREVIEW_ACCENT,
    PREVIEW_ACCENT_OUTLINE,
    PREVIEW_BG_DARK,
    PREVIEW_BG_LIGHT,
    PREVIEW_OUTLINE_DARK,
    PREVIEW_OUTLINE_LIGHT,
    PREVIEW_TEXT_DARK,
    PREVIEW_TEXT_LIGHT,
    TAG_COLOR_ERROR,
    TAG_COLOR_INFO,
    TAG_COLOR_SUCCESS,
    TAG_COLOR_WARNING,
    TAG_TEXT_ON_DARK,
    TAG_TEXT_ON_LIGHT,
)
from gui.gui_i18n import tr
from gui.tabs.settings import SettingsColorManager, SettingsFontManager, SettingsPathValidator, SettingsGlossaryManager
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import FontDialog


class SettingsTab(ttk.Frame):
    """Вкладка настроек приложения."""

    def __init__(
        self,
        parent: ttk.Widget,
        config: dict[str, Any],
        on_save_callback: Callable[[dict[str, Any]], None] | None = None,
        on_load_callback: Callable[[], None] | None = None,
        on_integrity_check_callback: Callable[[], None] | None = None,
        on_font_change_callback: Callable[[], None] | None = None,
        on_color_change_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.config: dict[str, Any] = config
        self.on_save_callback: Callable[[dict[str, Any]], None] | None = on_save_callback
        self.on_load_callback: Callable[[], None] | None = on_load_callback
        self.on_integrity_check_callback: Callable[[], None] | None = on_integrity_check_callback
        self.on_font_change_callback: Callable[[], None] | None = on_font_change_callback
        self.on_color_change_callback: Callable[[], None] | None = on_color_change_callback
        self.verbose_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.auto_backup_var: tk.BooleanVar = tk.BooleanVar(value=True)
        self.auto_split_glossary_var: tk.BooleanVar = tk.BooleanVar(
            value=config.get("auto_split_glossary", True)
        )
        self.verification_language_var: tk.StringVar = tk.StringVar(
            value=config.get("verification_language", "Russian")
        )
        self.translation_mode_var: tk.StringVar = tk.StringVar(
            value=config.get("translation_mode", "separate")
        )
        # ✅ ОТЛАДКА: следим за изменением режима
        def _on_mode_change(*args):
            new_val = self.translation_mode_var.get()
            print(f"DEBUG: translation_mode_var changed to '{new_val}'")
        self.translation_mode_var.trace_add("write", _on_mode_change)
        self.use_morphy_var: tk.BooleanVar = tk.BooleanVar(
            value=config.get("use_morphy", True)
        )
        self.path_history: dict[str, list[str]] = self._load_path_history()

        # UI components - будут инициализированы в _setup_ui
        self.notebook: ttk.Notebook | None = None
        self.general_tab: ttk.Frame | None = None
        self.paths_tab: ttk.Frame | None = None
        self.appearance_tab: ttk.Frame | None = None
        self.translation_tab: ttk.Frame | None = None
        self.engines_tab: ttk.Frame | None = None
        self.verification_tab: ttk.Frame | None = None

        # Font previews
        self._font_previews: dict[str, Any] = {}
        self.log_tag_color_previews: dict[str, tk.Canvas] = {}
        self.log_tag_color_labels: dict[str, ttk.Label] = {}

        # UI color previews
        self.ui_color_preview: tk.Canvas | None = None
        self.log_color_preview: tk.Text | None = None

        # Path entries
        self.mods_folder_entry: PathEntryWithBrowse | None = None
        self.mods_folder_entry_var: tk.StringVar | None = None
        self.output_folder_entry: PathEntryWithBrowse | None = None
        self.game_path_entry: PathEntryWithBrowse | None = None

        # History
        self.mods_history_text: tk.Text | None = None

        # Translation
        self.source_lang_var: tk.StringVar | None = None
        self.source_lang_combo: ttk.Combobox | None = None
        self.target_lang_var: tk.StringVar | None = None
        self.target_lang_combo: ttk.Combobox | None = None
        self.language_combo: ttk.Combobox | None = None

        # Engines
        self.engine_vars: dict[str, tk.BooleanVar] = {}
        self.advanced_collapsible: CollapsibleFrame | None = None
        self.smart_routing_var: tk.BooleanVar | None = None
        self.split_long_text_var: tk.BooleanVar | None = None
        self.rate_limit_var: tk.StringVar | None = None
        self.rate_limit_entry: ValidatedEntry | None = None
        self.max_chunk_var: tk.StringVar | None = None
        self.max_chunk_entry: ValidatedEntry | None = None
        self.deeplx_url_var: tk.StringVar | None = None
        self.deeplx_url_entry: AutocompleteCombobox | None = None

        # Preset
        self.preset_entry: ttk.Entry | None = None

        # ✅ Инициализация новых менеджеров
        self.color_manager = SettingsColorManager(
            self, self.config, is_dark_theme=self._is_dark_theme
        )
        self.font_manager = SettingsFontManager(
            self, self.config, apply_callback=self._on_font_change
        )
        self.path_validator = SettingsPathValidator(self.config)
        self.glossary_manager = SettingsGlossaryManager(
            self, self.config, is_dark_theme=self._is_dark_theme
        )

        self._font_change_callbacks = []

        self._setup_ui()

    def _on_font_change(self, key: str, family: str, size: int) -> None:
        """Callback при изменении шрифта."""
        if key == "reset":
            # Сброс всех шрифтов
            for callback in self._font_change_callbacks:
                try:
                    callback()
                except Exception:
                    pass
        elif self.on_font_change_callback:
            self.on_font_change_callback()

    def _load_path_history(self) -> dict[str, list[str]]:
        return self.config.get(
            "path_history",
            {
                "mods": [],
                "output": [],
                "game": [],
            },
        )

    def _save_path_history(self) -> None:
        self.config["path_history"] = self.path_history

    def _add_to_history(self, path_type: str, path: str) -> None:
        if path and path not in self.path_history.get(path_type, []):
            if path_type not in self.path_history:
                self.path_history[path_type] = []
            self.path_history[path_type].insert(0, path)
            self.path_history[path_type] = self.path_history[path_type][:10]
            self._save_path_history()

    def _setup_ui(self) -> None:
        """Настроить пользовательский интерфейс."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        self.general_tab = self._create_general_tab(self.notebook)
        self.notebook.add(self.general_tab, text=tr("tab_main", "⚙️ Основные"))
        self.paths_tab = self._create_paths_tab(self.notebook)
        self.notebook.add(self.paths_tab, text=tr("tab_paths", "📁 Пути"))
        self.appearance_tab = self._create_appearance_tab(self.notebook)
        self.notebook.add(self.appearance_tab, text=tr("tab_appearance", "🎨 Оформление"))
        self.translation_tab = self._create_translation_tab(self.notebook)
        self.notebook.add(self.translation_tab, text=tr("tab_translation", "🌐 Перевод"))

        # ✅ НОВОЕ: Вкладка настроек переводчиков
        self.engines_tab = self._create_engines_tab(self.notebook)
        self.notebook.add(self.engines_tab, text=tr("tab_engines", "🤖 Переводчики"))

        self.verification_tab = self._create_verification_tab(self.notebook)
        self.notebook.add(self.verification_tab, text=tr("tab_verification", "✅ Верификация"))
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(
            btn_frame,
            text=tr("btn_save_settings", "💾 Сохранить настройки"),
            command=self._on_save,
            bootstyle="success",
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame,
            text=tr("btn_load_settings", "📂 Загрузить настройки"),
            command=self._on_load,
            bootstyle="info",
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame,
            text=tr("btn_reset", "🔄 Сбросить"),
            command=self._on_reset,
            bootstyle="warning",
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame,
            text=tr("btn_export_settings", "📤 Экспорт настроек"),
            command=self._export_settings,
            bootstyle="info",
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame,
            text=tr("btn_import_settings", "📥 Импорт настроек"),
            command=self._import_settings,
            bootstyle="info",
        ).pack(side="left", padx=2)
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=10)
        ttk.Button(
            self,
            text=tr("btn_integrity_check", "🔍 Проверка целостности файлов"),
            command=self._on_integrity_check,
            bootstyle="info",
        ).pack(pady=5)

        # Подписка на событие смены языка
        self.bind("<<LanguageChanged>>", self._on_language_changed)

    def _on_language_changed(self, event: tk.Event | None = None) -> None:
        """Обновить названия под-вкладок при смене языка."""
        self._update_subtab_names()

    def _update_subtab_names(self) -> None:
        """Обновить названия под-вкладок при смене языка."""
        try:
            if hasattr(self, "notebook") and self.notebook is not None:
                self.notebook.tab(0, text=tr("tab_main", "⚙️ Основные"))
                self.notebook.tab(1, text=tr("tab_paths", "📁 Пути"))
                self.notebook.tab(2, text=tr("tab_appearance", "🎨 Оформление"))
                self.notebook.tab(3, text=tr("tab_translation", "🌐 Перевод"))
                self.notebook.tab(4, text=tr("tab_engines", "🤖 Переводчики"))
                self.notebook.tab(5, text=tr("tab_verification", "✅ Верификация"))
        except Exception as e:
            logger.debug(f"Не удалось обновить названия под-вкладок: {e}")

    def _create_general_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Создает вкладку основных настроек."""
        frame = ttk.Frame(parent, padding=10)
        preset_frame = ttk.LabelFrame(frame, text=tr("section_preset_file", "Файл пресета"))
        preset_frame.pack(fill="x", pady=5)
        ttk.Label(preset_frame, text=tr("label_preset_path", "Путь к пресету:")).grid(
            row=0, column=0, padx=5, pady=5
        )
        self.preset_entry = ttk.Entry(preset_frame, width=50)
        self.preset_entry.grid(row=0, column=1, padx=5, pady=5)
        self.preset_entry.insert(0, self.config.get("preset_file", ""))
        ttk.Button(
            preset_frame, text=tr("btn_browse", "📂 Обзор..."), command=self._browse_preset
        ).grid(row=0, column=2, padx=5, pady=5)
        opts_frame = ttk.LabelFrame(
            frame, text=tr("section_additional_settings", "Дополнительные настройки")
        )
        opts_frame.pack(fill="x", pady=5)
        ttk.Checkbutton(
            opts_frame,
            text=tr("chk_verbose_log", "Подробный вывод в логе"),
            variable=self.verbose_var,
        ).pack(anchor="w", padx=5, pady=2)
        ttk.Checkbutton(
            opts_frame,
            text=tr("chk_auto_backup", "Автосохранение резервных копий"),
            variable=self.auto_backup_var,
        ).pack(anchor="w", padx=5, pady=2)
        ttk.Checkbutton(
            opts_frame,
            text=tr("chk_auto_split_glossary", "Автоматическая разбивка глоссария на файлы"),
            variable=self.auto_split_glossary_var,
        ).pack(anchor="w", padx=5, pady=2)
        return frame

    def _create_paths_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Создает вкладку настроек путей."""
        frame = ttk.Frame(parent, padding=10)
        # Папка модов
        self.mods_folder_entry = PathEntryWithBrowse(
            frame,
            label_text=tr("label_mods_folder", "Папка модов:"),
            button_text=tr("btn_browse", "📂 Обзор..."),
            width=50,
            initial_value=get_paths_config().get_mods_path(),
            dialog_title=tr("label_mods_folder", "Выберите папку модов"),
        )
        self.mods_folder_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        # Для обратной совместимости
        self.mods_folder_entry_var = self.mods_folder_entry.entry_var

        ttk.Button(
            frame, text=tr("btn_validate", "✅ Проверить"), command=self._validate_mods_path
        ).grid(row=0, column=3, padx=5, pady=2)
        ttk.Label(frame, text=tr("label_output_folder", "Папка вывода:")).grid(
            row=1, column=0, sticky="w", padx=5, pady=2
        )
        self.output_folder_entry = PathEntryWithBrowse(
            frame,
            label_text="",
            button_text=tr("btn_browse", "📂 Обзор..."),
            width=50,
            initial_value=get_paths_config().get_output_path(),
            dialog_title=tr("label_output_folder", "Выберите папку вывода"),
        )
        self.output_folder_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Button(
            frame, text=tr("btn_validate", "✅ Проверить"), command=self._validate_output_path
        ).grid(row=1, column=3, padx=5, pady=2)
        ttk.Label(frame, text=tr("label_game_path", "Путь к игре:")).grid(
            row=2, column=0, sticky="w", padx=5, pady=2
        )
        self.game_path_entry = PathEntryWithBrowse(
            frame,
            label_text="",
            button_text=tr("btn_browse", "📂 Обзор..."),
            width=50,
            initial_value=get_paths_config().get_game_path(),
            dialog_title=tr("label_game_path", "Выберите путь к игре"),
        )
        self.game_path_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        ttk.Button(
            frame, text=tr("btn_validate", "✅ Проверить"), command=self._validate_game_path
        ).grid(row=2, column=3, padx=5, pady=2)
        frame.columnconfigure(1, weight=1)
        history_frame = ttk.LabelFrame(frame, text=tr("section_path_history", "История путей"))
        history_frame.grid(row=3, column=0, columnspan=4, sticky="ew", padx=5, pady=10)
        ttk.Label(history_frame, text=tr("label_recent_mods", "Последние папки модов:")).pack(
            anchor="w", padx=5, pady=2
        )
        self.mods_history_text = tk.Text(history_frame, height=3, wrap="none", state="disabled")
        self.mods_history_text.pack(fill="x", padx=5, pady=2)
        self._update_history_display("mods")
        return frame

    def _create_appearance_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Создает вкладку оформления со сворачиваемыми секциями."""
        from ttkbootstrap.widgets.scrolled import ScrolledFrame

        # Создаём родительский Frame для вкладки
        main_frame = ttk.Frame(parent)

        # ScrolledFrame с автоматическим скрытием скроллбара
        scrollable_frame = ScrolledFrame(main_frame, autohide=True)
        scrollable_frame.pack(fill="both", expand=True)

        self._font_previews = {}
        self.log_tag_color_previews = {}

        # ✅ ДЕЛЕГИРОВАНИЕ: Шрифты
        self.font_manager.create_fonts_section(scrollable_frame)

        # ✅ ДЕЛЕГИРОВАНИЕ: Цвета UI
        self.color_manager.create_ui_colors_section(scrollable_frame)

        # ✅ ДЕЛЕГИРОВАНИЕ: Цвета логов
        self.color_manager.create_log_colors_section(scrollable_frame)

        # ✅ ДЕЛЕГИРОВАНИЕ: Цвета тегов
        self.color_manager.create_tag_colors_section(scrollable_frame)

        # ✅ ДЕЛЕГИРОВАНИЕ: Настройки глоссария
        self.glossary_manager.create_glossary_section(scrollable_frame)

        return main_frame

    def _create_translation_tab(self, parent: ttk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)
        mode_frame = ttk.LabelFrame(frame, text=tr("section_translation_mode", "Режим перевода"))
        mode_frame.pack(fill="x", pady=PADY_LARGE)
        ttk.Radiobutton(
            mode_frame,
            text=tr("radio_translation_separate", "Создать мод-перевод (рекомендуется)"),
            variable=self.translation_mode_var,
            value="separate",
        ).pack(anchor="w", padx=PADX_LARGE, pady=PADY_SMALL)
        ttk.Radiobutton(
            mode_frame,
            text=tr("radio_translation_inplace", "Переводить в исходную папку"),
            variable=self.translation_mode_var,
            value="inplace",
        ).pack(anchor="w", padx=PADX_LARGE, pady=PADY_SMALL)

        # ✅ НОВОЕ: Чекбокс Morphy (автосклонение)
        morphy_frame = ttk.LabelFrame(frame, text=tr("section_morphy", "Morphy склонение"))
        morphy_frame.pack(fill="x", pady=PADY_LARGE)
        ttk.Checkbutton(
            morphy_frame,
            text=tr("chk_use_morphy", "🔤 Автосклонение слов (русский/украинский)"),
            variable=self.use_morphy_var,
            bootstyle="info",
        ).pack(anchor="w", padx=PADX_LARGE, pady=PADY_SMALL)

        lang_frame = ttk.LabelFrame(frame, text=tr("section_languages", "Языки"))
        lang_frame.pack(fill="x", pady=PADY_LARGE)
        ttk.Label(lang_frame, text=tr("label_source_lang", "Исходный язык:")).grid(
            row=0, column=0, padx=PADX_LARGE, pady=PADY_SMALL
        )
        self.source_lang_var = tk.StringVar(value=self.config.get("source_language", "English"))
        self.source_lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.source_lang_var,
            values=SUPPORTED_LANGUAGES,
            width=ENTRY_WIDTH_SMALL,
            state="readonly",
        )
        self.source_lang_combo.grid(row=0, column=1, padx=PADX_LARGE, pady=PADY_SMALL)
        ttk.Label(lang_frame, text=tr("label_target_lang", "Целевой язык:")).grid(
            row=1, column=0, padx=PADX_LARGE, pady=PADY_SMALL
        )
        self.target_lang_var = tk.StringVar(value=self.config.get("target_language", "Russian"))
        self.target_lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.target_lang_var,
            values=SUPPORTED_LANGUAGES,
            width=ENTRY_WIDTH_SMALL,
            state="readonly",
        )
        self.target_lang_combo.grid(row=1, column=1, padx=PADX_LARGE, pady=PADY_SMALL)

        # ✅ НОВОЕ: Чекбокс автоопределения исходного языка
        self.auto_detect_source_lang_var: tk.BooleanVar = tk.BooleanVar(
            value=self.config.get("auto_detect_source_lang", True)
        )
        ttk.Checkbutton(
            lang_frame,
            text=tr("chk_auto_detect_source", "Автоопределение исходного языка для мода"),
            variable=self.auto_detect_source_lang_var,
            bootstyle="info",
        ).grid(row=2, column=0, columnspan=2, padx=PADX_LARGE, pady=PADY_SMALL, sticky="w")
        return frame

    def _create_engines_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Вкладка настроек переводчиков."""
        frame = ttk.Frame(parent, padding=10)

        # ✅ НОВОЕ: Секция основных движков
        engines_frame = ttk.LabelFrame(
            frame, text=tr("section_translation_engines", "Движки перевода")
        )
        engines_frame.pack(fill="x", pady=5)

        # Чекбоксы для включения/отключения движков
        self.engine_vars = {}
        engine_options = [
            ("google", tr("engine_google", "Google Translate")),
            ("mymemory", tr("engine_mymemory", "MyMemory")),
            ("deepl", tr("engine_deepl", "DeepL (веб)")),
            ("bing", tr("engine_bing", "Bing Translator")),
            ("deeplx", tr("engine_deeplx", "DeepLX (локальный сервер)")),
            ("translators", tr("engine_translators", "Translators (20+ движков)")),
            ("libre", tr("engine_libre", "LibreTranslate (свой сервер)")),
            ("argos", tr("engine_argos", "Argos Translate (оффлайн)")),
        ]

        for key, label in engine_options:
            var = tk.BooleanVar(
                value=self.config.get(
                    f"engine_{key}_enabled", key in ["google", "mymemory", "deepl", "bing"]
                )
            )
            self.engine_vars[key] = var
            ttk.Checkbutton(
                engines_frame,
                text=label,
                variable=var,
            ).pack(anchor="w", padx=10, pady=2)

        # ✅ НОВОЕ: Сворачиваемый фрейм для дополнительных настроек
        self.advanced_collapsible = CollapsibleFrame(
            frame,
            text=tr("section_engine_advanced", "Дополнительные настройки"),
            collapsed=True,
            bootstyle="info",
        )
        self.advanced_collapsible.pack(fill="x", pady=10)

        advanced_frame = self.advanced_collapsible.content_frame

        # Умная маршрутизация
        self.smart_routing_var = tk.BooleanVar(value=self.config.get("smart_routing", True))
        ttk.Checkbutton(
            advanced_frame,
            text=tr("chk_smart_routing", "Умная маршрутизация (автоприоритизация по успешности)"),
            variable=self.smart_routing_var,
        ).pack(anchor="w", padx=10, pady=2)

        # Разбиение длинного текста
        self.split_long_text_var = tk.BooleanVar(value=self.config.get("split_long_text", True))
        ttk.Checkbutton(
            advanced_frame,
            text=tr("chk_split_long_text", "Умное разбиение длинного текста"),
            variable=self.split_long_text_var,
        ).pack(anchor="w", padx=10, pady=2)

        # Rate limiting с валидацией
        rl_frame = ttk.Frame(advanced_frame)
        rl_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(rl_frame, text=tr("label_rate_limit", "Задержка между запросами (сек):")).pack(
            side="left", padx=5
        )
        self.rate_limit_var = tk.StringVar(value=str(self.config.get("rate_limit_delay", "0.5")))
        self.rate_limit_entry = ValidatedEntry(
            rl_frame,
            textvariable=self.rate_limit_var,
            validate_type="float",
            width=10,
            error_callback=lambda msg: self._show_validation_error(msg),
        )
        self.rate_limit_entry.pack(side="left", padx=5)

        # Максимальный размер чанка с валидацией
        chunk_frame = ttk.Frame(advanced_frame)
        chunk_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(chunk_frame, text=tr("label_max_chunk", "Макс. размер чанка (символов):")).pack(
            side="left", padx=5
        )
        self.max_chunk_var = tk.StringVar(value=str(self.config.get("max_chunk_size", "450")))
        self.max_chunk_entry = ValidatedEntry(
            chunk_frame,
            textvariable=self.max_chunk_var,
            validate_type="number",
            width=10,
            error_callback=lambda msg: self._show_validation_error(msg),
        )
        self.max_chunk_entry.pack(side="left", padx=5)

        # DeepLX URL с автодополнением
        deeplx_frame = ttk.Frame(advanced_frame)
        deeplx_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(deeplx_frame, text=tr("label_deeplx_url", "DeepLX URL:")).pack(
            side="left", padx=5
        )

        deeplx_history = self.config.get("deeplx_url_history", ["http://localhost:1188"])
        self.deeplx_url_var = tk.StringVar(
            value=self.config.get("deeplx_url", "http://localhost:1188")
        )
        self.deeplx_url_entry = AutocompleteCombobox(
            deeplx_frame,
            textvariable=self.deeplx_url_var,
            values=deeplx_history,
            width=40,
        )
        self.deeplx_url_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Кнопка сброса статистики
        ttk.Button(
            advanced_frame,
            text=tr("btn_reset_routing_stats", "🔄 Сбросить статистику маршрутизации"),
            command=self._reset_routing_stats,
            bootstyle="warning-outline",
        ).pack(anchor="w", padx=10, pady=10)

        # Подсказка
        hint_label = ttk.Label(
            frame,
            text=tr(
                "hint_engines",
                "💡 Совет: DeepLX требует запущенный локальный сервер. Подробнее: github.com/OwO-Network/DeepLX",
            ),
            foreground="gray",
            wraplength=500,
        )
        hint_label.pack(anchor="w", padx=10, pady=10)

        return frame

    def _create_verification_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Создает вкладку настроек верификации."""
        frame = ttk.Frame(parent, padding=10)
        lang_frame = ttk.LabelFrame(frame, text=tr("section_verification_lang", "Язык верификации"))
        lang_frame.pack(fill="x", pady=5)
        ttk.Label(lang_frame, text=tr("label_verify_lang", "Язык для проверки:")).pack(
            side="left", padx=5
        )
        # ✅ ИСПРАВЛЕНО: Добавляем "Все языки" в список
        verify_languages = ["Все языки"] + list(SUPPORTED_LANGUAGES)
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.verification_language_var,
            values=verify_languages,
            width=20,
            state="readonly",
        )
        self.language_combo.pack(side="left", padx=5)
        ttk.Label(
            lang_frame,
            text=tr("label_verify_hint", "(только этот язык будет проверяться)"),
            foreground="gray",
        ).pack(side="left", padx=5)
        return frame

    def _reset_routing_stats(self) -> None:
        """Сбросить статистику маршрутизации."""
        try:
            config_mgr = get_config_manager()
            for key in ["engine_success_counts", "engine_total_attempts"]:
                config_mgr.set(key, {}, save=False)
            config_mgr.save()
            messagebox.showinfo(
                tr("msg_ok", "OK"),
                tr("msg_routing_stats_reset", "Статистика маршрутизации сброшена"),
            )
            logger.info("Статистика маршрутизации сброшена")
        except Exception as e:
            logger.error(f"Ошибка при сбросе статистики маршрутизации: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _show_validation_error(self, message: str) -> None:
        """Показать ошибку валидации."""
        logger.warning(f"Ошибка валидации: {message}")

    def _is_dark_theme(self) -> bool:
        """Проверяет, используется ли тёмная тема"""
        theme = self.config.get("theme", "light")
        return theme in ("dark", "ocean", "superhero", "cyborg", "darkly", "solar")

    def _browse_preset(self) -> None:
        """Выбрать файл пресета."""
        file = filedialog.askopenfilename(
            title=tr("dialog_select_preset", "Выберите файл пресета"),
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
        )
        if file:
            self.preset_entry.delete(0, tk.END)
            self.preset_entry.insert(0, file)
            logger.debug(f"Выбран файл пресета: {file}")

    def _validate_mods_path(self) -> None:
        """Проверить существование папки модов."""
        path = self.mods_folder_entry.get()
        if os.path.exists(path):
            count = len([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])
            logger.info(f"Папка модов существует: {path}, найдено модов: {count}")
            messagebox.showinfo(
                tr("msg_success", "Успех"),
                f"{tr('msg_folder_exists', 'Папка существует')}\n{tr('msg_mods_found', 'Найдено модов')}: {count}",
            )
        else:
            logger.warning(f"Папка модов не существует: {path}")
            messagebox.showerror(
                tr("msg_error", "Ошибка"),
                f"{tr('msg_folder_not_exists', 'Папка не существует')}:\n{path}",
            )

    def _validate_output_path(self) -> None:
        """Проверить существование папки вывода."""
        path = self.output_folder_entry.get()
        if os.path.exists(path):
            logger.info(f"Папка вывода существует: {path}")
            messagebox.showinfo(
                tr("msg_success", "Успех"),
                f"{tr('msg_folder_exists_path', 'Папка существует')}:\\n{path}",
            )
        else:
            result = messagebox.askyesno(
                tr("msg_warning", "Предупреждение"),
                f"{tr('msg_folder_not_exists_create', 'Папка не существует')}:\\n{path}\\n\\n{tr('msg_create_folder', 'Создать её?')}",
            )
            if result:
                os.makedirs(path, exist_ok=True)
                logger.info(f"Папка вывода создана: {path}")
                messagebox.showinfo(
                    tr("msg_success", "Успех"),
                    f"{tr('msg_folder_created', 'Папка создана')}:\\n{path}",
                )

    def _validate_game_path(self) -> None:
        """Проверить существование пути к игре."""
        path = self.game_path_entry.get()
        if os.path.exists(path):
            # Проверяем наличие RimWorld.exe или аналога
            exe_exists = os.path.exists(os.path.join(path, "RimWorldWin64.exe")) or os.path.exists(
                os.path.join(path, "RimWorldWin32.exe")
            )
            if exe_exists:
                logger.info(f"Путь к игре верифицирован: {path}")
                messagebox.showinfo(
                    tr("msg_success", "Успех"),
                    f"{tr('msg_game_path_verified', 'Путь к игре верифицирован')}:\\n{path}",
                )
            else:
                logger.warning(f"Папка игры существует, но exe не найден: {path}")
                messagebox.showwarning(
                    tr("msg_warning", "Предупреждение"),
                    f"{tr('msg_folder_exists_no_exe', 'Папка существует, но исполнительный файл не найден')}:\\n{path}",
                )
        else:
            logger.error(f"Путь к игре не существует: {path}")
            messagebox.showerror(
                tr("msg_error", "Ошибка"),
                f"{tr('msg_game_path_not_exists', 'Путь к игре не существует')}:\\n{path}",
            )

    def _update_history_display(self, path_type: str) -> None:
        """Обновить отображение истории путей."""
        if path_type == "mods" and hasattr(self, "mods_history_text"):
            self.mods_history_text.config(state="normal")
            self.mods_history_text.delete("1.0", tk.END)
            for path in self.path_history.get("mods", []):
                self.mods_history_text.insert(tk.END, f"• {path}\n")
            self.mods_history_text.config(state="disabled")

    def _on_save(self) -> None:
        """Обработчик сохранения настроек."""
        if hasattr(self, "glossary_manager"):
            self.glossary_manager.save_settings()
        if self.on_save_callback:
            self.on_save_callback(self.get_options())

    def _on_load(self) -> None:
        """Обработчик загрузки настроек."""
        if self.on_load_callback:
            self.on_load_callback()

    def _on_reset(self) -> None:
        """Сбросить настройки к значениям по умолчанию."""
        try:
            result = messagebox.askyesno(
                tr("msg_confirmation", "Подтверждение"),
                tr("msg_reset_to_defaults", "Сбросить все настройки к значениям по умолчанию?"),
            )
            if result:
                # ✅ ИСПРАВЛЕНО: Полный список настроек по умолчанию
                self.config = {
                    "source_language": "English",
                    "source_languages": ["English"],
                    "target_language": "Russian",
                    "verification_language": "Russian",
                    "translation_mode": "separate",
                    "use_morphy": True,
                    "auto_detect_source_lang": True,
                    "verbose": False,
                    "auto_backup": True,
                    "preset_file": "",
                    # Настройки движков
                    "engine_google_enabled": True,
                    "engine_mymemory_enabled": True,
                    "engine_deepl_enabled": True,
                    "engine_bing_enabled": True,
                    "engine_deeplx_enabled": False,
                    "engine_translators_enabled": False,
                    "engine_libre_enabled": False,
                    "engine_argos_enabled": False,
                    "smart_routing": True,
                    "split_long_text": True,
                    "rate_limit_delay": "0.5",
                    "max_chunk_size": "450",
                    "deeplx_url": "http://localhost:1188",
                    "glossary_auto_split": True,
                    "glossary_show_description": True,
                    "glossary_show_usage_count": True,
                    "glossary_default_confidence": 0.0,
                    "glossary_page_size": 100,
                    "glossary_confirm_on_delete": True,
                    "glossary_category_colors": {
                        "game": "#2E7D32",
                        "user": "#1565C0",
                        "auto": "#E65100",
                        "seed": "#6A1B9A",
                        "general": "#583A3A",
                    },
                    "glossary_category_names": {
                        "game": "Игра",
                        "user": "Пользователь",
                        "auto": "Авто",
                        "seed": "Семя",
                        "general": "Общий",
                    },
                }
                self.apply_config(self.config)
                if hasattr(self, "glossary_manager"):
                    self.glossary_manager.load_settings()

                # ✅ НОВОЕ: Сбрасываем настройки фильтров если доступно
                try:
                    toplevel = self.winfo_toplevel()
                    if hasattr(toplevel, "tab_filters") and toplevel.tab_filters:
                        toplevel.tab_filters.apply_filters_config({})
                except Exception:
                    pass

                logger.info("Настройки сброшены к значениям по умолчанию")
                messagebox.showinfo(
                    tr("msg_success", "Успех"), tr("msg_settings_reset", "Настройки сброшены")
                )
        except Exception as e:
            logger.error(f"Ошибка при сбросе настроек: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _on_integrity_check(self) -> None:
        """Запустить проверку целостности файлов с учётом выбранного языка."""
        if self.on_integrity_check_callback:
            # ✅ НОВОЕ: Передаём выбранный язык верификации
            language = getattr(self, "verification_language_var", None)
            lang_value = language.get() if language else None
            self.on_integrity_check_callback(lang_value)

    def _on_source_langs_change(self, values=None) -> None:
        """Обработчик изменения списка исходных языков"""
        if hasattr(self, "source_lang_var") and hasattr(self, "source_langs_selector") and self.source_langs_selector:
            current = self.source_langs_selector.get()
            if current:
                self.source_lang_var.set(current[0])

    def get_options(self) -> dict[str, Any]:
        """Получить текущие настройки."""
        # Собираем настройки движков
        engine_config = {}
        for key, var in self.engine_vars.items():
            engine_config[f"engine_{key}_enabled"] = var.get()

        # ✅ ОТЛАДКА: Показываем какой режим сохраняем
        mode_to_save = self.translation_mode_var.get()
        print(f"DEBUG SETTINGS: Saving translation_mode = '{mode_to_save}'")
        return {
            "mods_folder": self.mods_folder_entry.get(),
            "output_folder": self.output_folder_entry.get(),
            "game_path": self.game_path_entry.get(),
            "source_language": self.source_lang_var.get(),
            "source_languages": self.source_langs_selector.get() if hasattr(self, "source_langs_selector") else [self.source_lang_var.get()],
            "target_language": self.target_lang_var.get(),
            "translation_mode": mode_to_save,
            "use_morphy": self.use_morphy_var.get(),
            "auto_detect_source_lang": self.auto_detect_source_lang_var.get(),
            # ✅ НОВОЕ: Настройки переводчиков
            **engine_config,
            "smart_routing": self.smart_routing_var.get(),
            "split_long_text": self.split_long_text_var.get(),
            "auto_split_glossary": self.auto_split_glossary_var.get(),
            "rate_limit_delay": float(self.rate_limit_var.get()),
            "max_chunk_size": int(self.max_chunk_var.get()),
            "deeplx_url": self.deeplx_url_var.get(),
        }

    def apply_config(self, config: dict[str, Any]) -> None:
        """Применить конфигурацию к UI."""
        self.preset_entry.delete(0, tk.END)
        self.preset_entry.insert(0, config.get("preset_file", ""))
        self.verification_language_var.set(config.get("verification_language", "Russian"))
        self.translation_mode_var.set(config.get("translation_mode", "separate"))
        if hasattr(self, "use_morphy_var"):
            self.use_morphy_var.set(config.get("use_morphy", True))
        if hasattr(self, "source_lang_var"):
            self.source_lang_var.set(config.get("source_language", "English"))
        if hasattr(self, "source_langs_selector"):
            self.source_langs_selector.set(config.get("source_languages", ["English"]))
        if hasattr(self, "target_lang_var"):
            self.target_lang_var.set(config.get("target_language", "Russian"))
        if hasattr(self, "auto_detect_source_lang_var"):
            self.auto_detect_source_lang_var.set(config.get("auto_detect_source_lang", True))

        # ✅ НОВОЕ: Устанавливаем пути из конфигурации
        if hasattr(self, "mods_folder_entry"):
            self.mods_folder_entry.set(config.get("mods_folder", ""))
        if hasattr(self, "output_folder_entry"):
            self.output_folder_entry.set(config.get("output_folder", ""))
        if hasattr(self, "game_path_entry"):
            self.game_path_entry.set(config.get("game_path", ""))

        # ✅ НОВОЕ: Применяем настройки переводчиков
        if hasattr(self, "engine_vars"):
            for key in self.engine_vars:
                # ✅ ИСПРАВЛЕНО: Читаем значение из config, а не используем старый список по умолчанию
                config_key = f"engine_{key}_enabled"
                if config_key in config:
                    self.engine_vars[key].set(config[config_key])
                else:
                    # Только если ключа нет в config, используем умолчание
                    default = key in ["google", "mymemory", "deepl", "bing"]
                    self.engine_vars[key].set(default)

        if hasattr(self, "smart_routing_var"):
            self.smart_routing_var.set(config.get("smart_routing", True))
        if hasattr(self, "split_long_text_var"):
            self.split_long_text_var.set(config.get("split_long_text", True))
        if hasattr(self, "rate_limit_var"):
            self.rate_limit_var.set(str(config.get("rate_limit_delay", "0.5")))
        if hasattr(self, "max_chunk_var"):
            self.max_chunk_var.set(str(config.get("max_chunk_size", "450")))
        if hasattr(self, "deeplx_url_var"):
            self.deeplx_url_var.set(config.get("deeplx_url", "http://localhost:1188"))
        if hasattr(self, "auto_split_glossary_var"):
            self.auto_split_glossary_var.set(config.get("auto_split_glossary", True))

        # ✅ НОВОЕ: Применяем настройки глоссария
        if hasattr(self, "glossary_manager"):
            self.glossary_manager.load_settings()

    def _export_settings(self) -> None:
        """Экспорт настроек в файл."""
        file_path = filedialog.asksaveasfilename(
            title=tr("dialog_save_settings", "Сохранить настройки"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not file_path:
            return
        try:
            # ✅ ИСПРАВЛЕНО: Экспортируем также настройки фильтров если доступны
            config_to_export = self.get_options()

            # Получаем настройки фильтров если есть доступ
            try:
                toplevel = self.winfo_toplevel()
                if hasattr(toplevel, "tab_filters") and toplevel.tab_filters:
                    filters_config = toplevel.tab_filters.get_filters_config()
                    config_to_export.update(filters_config)
            except Exception:
                pass  # Игнорируем если не удалось получить настройки фильтров

            settings_data = {
                "version": "2.0",
                "timestamp": datetime.now().isoformat(),
                "config": config_to_export,
                "path_history": self.path_history,
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Настройки экспортированы в {file_path}")
            messagebox.showinfo(
                tr("msg_success", "Успех"),
                f"{tr('msg_settings_exported', 'Настройки экспортированы')}:\\n{file_path}",
            )
        except Exception as e:
            logger.error(f"Ошибка экспорта настроек: {e}")
            messagebox.showerror(
                tr("msg_error", "Ошибка"),
                f"{tr('msg_export_settings_error', 'Ошибка экспорта настроек')}:\\n{e}",
            )

    def _import_settings(self) -> None:
        """Импорт настроек из файла."""
        file_path = filedialog.askopenfilename(
            title=tr("dialog_load_settings", "Загрузить настройки"),
            filetypes=[("JSON files", "*.json")],
        )
        if not file_path:
            return
        try:
            with open(file_path, encoding="utf-8") as f:
                settings_data = json.load(f)
            if "config" in settings_data:
                self.apply_config(settings_data["config"])

                # ✅ ИСПРАВЛЕНО: Применяем настройки фильтров если доступны
                toplevel = self.winfo_toplevel()
                if hasattr(toplevel, "tab_filters") and toplevel.tab_filters:
                    try:
                        toplevel.tab_filters.apply_filters_config(settings_data["config"])
                    except Exception as e:
                        logger.error(f"Ошибка применения настроек фильтров: {e}")

                if "path_history" in settings_data:
                    self.path_history = settings_data["path_history"]
                    self._update_history_display("mods")
                logger.info(f"Настройки импортированы из {file_path}")
                messagebox.showinfo(
                    tr("msg_success", "Успех"),
                    f"{tr('msg_settings_imported', 'Настройки импортированы')}:\\n{file_path}\\n\\n{tr('msg_dont_forget_save', 'Не забудьте сохранить их!')}",
                )
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON при импорте настроек: {e}")
            messagebox.showerror(
                tr("msg_error", "Ошибка"),
                f"Ошибка формата файла настроек:\\n{e}",
            )
        except Exception as e:
            logger.error(f"Ошибка импорта настроек: {e}")
            messagebox.showerror(
                tr("msg_error", "Ошибка"),
                f"{tr('msg_import_settings_error', 'Ошибка импорта настроек')}:\\n{e}",
            )
