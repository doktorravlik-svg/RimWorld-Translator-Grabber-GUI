# Вкладка настроек приложения
from __future__ import annotations

import json
import logging
import os
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Any

import ttkbootstrap as ttk
from config.config_manager import get_config_manager
from config.language_constants import SUPPORTED_LANGUAGES
from config.paths_config import get_paths_config
from gui.components.advanced_widgets import (
    AutocompleteCombobox,
    CollapsibleFrame,
    ValidatedEntry,
)
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
from gui.tabs.settings import SettingsColorManager, SettingsFontManager, SettingsPathValidator
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import FontDialog

logger = logging.getLogger(__name__)


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
        self.verification_language_var: tk.StringVar = tk.StringVar(
            value=config.get("verification_language", "Russian")
        )
        self.translation_mode_var: tk.StringVar = tk.StringVar(
            value=config.get("translation_mode", "separate")
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

        return main_frame

    def _create_fonts_section(self, parent: ttk.Widget) -> None:
        """Создает секцию настроек шрифтов."""
        from gui.components.advanced_widgets import CollapsibleFrame

        fonts_collapsible = CollapsibleFrame(
            parent, text=tr("section_fonts", "🔤 Шрифты"), collapsed=False, bootstyle="info"
        )
        fonts_collapsible.pack(fill="x", pady=5, padx=5)
        frame = fonts_collapsible.content_frame

        self._create_font_row(
            frame,
            tr("label_main_font", "Основной:"),
            "main_font_label",
            "main_font_preview",
            "#f8f9fa",
            "#212529",
            "Аа Бб Вв 123",
            self._change_main_font,
        )
        self._create_font_row(
            frame,
            tr("label_log_font", "Логи:"),
            "log_font_label",
            "log_font_preview",
            "#1e1e1e",
            "#d4d4d4",
            "[INFO] 12:00:00",
            self._change_log_font,
        )

        tf = ttk.Frame(frame)
        tf.pack(fill="x", pady=5, padx=5)
        ttk.Label(
            tf,
            text=tr("label_tree_font", "Дерево:"),
            width=15,
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=2)
        self.tree_font_label = ttk.Label(
            tf, text=tr("font_loading", "Загрузка..."), font=("Segoe UI", 9), anchor="w"
        )
        self.tree_font_label.pack(side="left", padx=2, fill="x", expand=True)
        self.tree_font_preview = ttk.Label(
            tf,
            text="📦 Моды  ✅ Верификация  🔄 Дубликаты",
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1,
            anchor="w",
            padding=5,
            width=30,
        )
        self.tree_font_preview.pack(side="left", padx=5)
        ttk.Button(
            tf, text="🔤", command=self._change_tree_font, bootstyle="info-outline", width=4
        ).pack(side="left", padx=2)

        font_btn_frame = ttk.Frame(frame)
        font_btn_frame.pack(fill="x", pady=5, padx=5)
        ttk.Button(
            font_btn_frame,
            text=tr("btn_apply_font_to_all", "📝 Применить ко всему"),
            command=self._apply_main_font_to_all,
            bootstyle="info-outline",
        ).pack(side="left", padx=2, expand=True, fill="x")
        ttk.Button(
            font_btn_frame,
            text=tr("btn_reset_all_fonts", "🔄 Сбросить"),
            command=self._reset_all_fonts,
            bootstyle="warning-outline",
        ).pack(side="left", padx=2, expand=True, fill="x")

        self._load_all_fonts_info()

    def _create_ui_colors_section(self, parent: ttk.Widget) -> None:
        """Создает секцию цветов интерфейса."""
        from gui.components.advanced_widgets import CollapsibleFrame

        collapsible = CollapsibleFrame(
            parent,
            text=tr("section_ui_colors", "🎨 Цвета интерфейса"),
            collapsed=False,
            bootstyle="primary",
        )
        collapsible.pack(fill="x", pady=5, padx=5)
        frame = collapsible.content_frame

        # ✅ Определяем цвет фона Canvas в зависимости от темы
        canvas_bg = "#2b2b2b" if self._is_dark_theme() else "#ffffff"

        self.ui_color_preview = tk.Canvas(
            frame, height=60, bg=canvas_bg, relief="solid", borderwidth=1, highlightthickness=0
        )
        self.ui_color_preview.pack(fill="x", pady=5, padx=5)
        self._draw_ui_color_preview()

        self._create_color_row(
            frame,
            tr("label_text_color", "Цвет текста:"),
            "text_color_label",
            "#000000",
            "text_color_preview",
            self._change_text_color,
            "primary-outline",
        )
        self._create_color_row(
            frame,
            tr("label_bg_color", "Цвет фона:"),
            "bg_color_label",
            "#ffffff",
            "bg_color_preview",
            self._change_bg_color,
            "primary-outline",
        )
        self._create_color_row(
            frame,
            tr("label_accent_color", "Цвет акцента:"),
            "accent_color_label",
            "#0d6efd",
            "accent_color_preview",
            self._change_accent_color,
            "primary-outline",
        )

        ttk.Button(
            frame,
            text=tr("btn_reset_colors", "🔄 Сбросить цвета"),
            command=self._reset_colors,
            bootstyle="warning-outline",
        ).pack(pady=5, padx=5)
        self._load_all_colors_info()

    def _create_log_colors_section(self, parent: ttk.Widget) -> None:
        """Создает секцию цветов логов."""
        from gui.components.advanced_widgets import CollapsibleFrame

        collapsible = CollapsibleFrame(
            parent,
            text=tr("section_log_colors", "📝 Цвета логов"),
            collapsed=False,
            bootstyle="success",
        )
        collapsible.pack(fill="x", pady=5, padx=5)
        frame = collapsible.content_frame

        self.log_color_preview = tk.Text(
            frame,
            height=6,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
            bg="#1e1e1e",
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=5,
        )
        self.log_color_preview.pack(fill="x", pady=5, padx=5)
        self._draw_log_color_preview()

        self._create_color_row(
            frame,
            tr("label_log_bg", "Фон логов:"),
            "log_bg_color_label",
            "#1e1e1e",
            "log_bg_color_preview",
            self._change_log_bg_color,
            "success-outline",
        )
        self._create_color_row(
            frame,
            tr("label_log_text", "Текст логов:"),
            "log_text_color_label",
            "#d4d4d4",
            "log_text_color_preview",
            self._change_log_text_color,
            "success-outline",
        )

        ttk.Button(
            frame,
            text=tr("btn_reset_log_colors", "🔄 Сбросить цвета логов"),
            command=self._reset_log_colors,
            bootstyle="warning-outline",
        ).pack(pady=5, padx=5)
        self._load_all_log_colors_info()

    def _create_tag_colors_section(self, parent: ttk.Widget) -> None:
        """Создает секцию цветов тегов логов."""
        from gui.components.advanced_widgets import CollapsibleFrame

        collapsible = CollapsibleFrame(
            parent,
            text=tr("section_log_tag_colors", "🏷️ Цвета тегов логов"),
            collapsed=True,
            bootstyle="info",
        )
        collapsible.pack(fill="x", pady=5, padx=5)
        frame = collapsible.content_frame

        tag_colors = [
            ("log_info_color", tr("tag_info", "ℹ️ Инфо:"), "#4fc3f7"),
            ("log_warning_color", tr("tag_warning", "⚠️ Предупреждение:"), "#ffb74d"),
            ("log_error_color", tr("tag_error", "❌ Ошибка:"), "#ef5350"),
            ("log_success_color", tr("tag_success", "✅ Успех:"), "#66bb6a"),
        ]

        for key, label, default in tag_colors:
            tc_frame = ttk.Frame(frame)
            tc_frame.pack(fill="x", pady=3, padx=5)
            ttk.Label(tc_frame, text=label, width=18, anchor="w").pack(side="left", padx=2)
            lbl = ttk.Label(tc_frame, text=tr("font_loading", "Загрузка..."), anchor="w")
            lbl.pack(side="left", padx=2, fill="x", expand=True)
            self.log_tag_color_labels[key] = lbl
            tag_preview = tk.Canvas(
                tc_frame, width=30, height=20, bg=default, relief="solid", borderwidth=1
            )
            tag_preview.pack(side="left", padx=2)
            self.log_tag_color_previews[key] = tag_preview
            ttk.Button(
                tc_frame,
                text="🎨",
                command=lambda k=key: self._change_log_tag_color(k),
                bootstyle="info-outline",
                width=4,
            ).pack(side="left", padx=2)

        ttk.Button(
            frame,
            text=tr("btn_reset_log_tag_colors", "🔄 Сбросить цвета тегов"),
            command=self._reset_log_tag_colors,
            bootstyle="warning-outline",
        ).pack(pady=5, padx=5)
        self._load_log_tag_colors_info()

    def _create_font_row(
        self, parent, label_text, label_attr, preview_attr, bg, fg, text, change_fn
    ):
        """Создает строку настройки шрифта с превью"""
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5, padx=5)

        # Метка
        ttk.Label(row, text=label_text, width=15, anchor="w", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=2
        )

        # Метка текущего шрифта (обновляется при загрузке)
        lbl = ttk.Label(
            row, text=tr("font_loading", "Загрузка..."), font=("Segoe UI", 9), anchor="w"
        )
        lbl.pack(side="left", padx=2, fill="x", expand=True)
        setattr(self, label_attr, lbl)

        # Превью шрифта
        preview = tk.Text(
            row,
            height=2,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 10),
            bg=bg,
            fg=fg,
            relief="solid",
            borderwidth=1,
            padx=5,
            pady=3,
            width=20,
        )
        preview.pack(side="left", padx=5)
        setattr(self, preview_attr, preview)

        # Обновляем текст превью
        if preview_attr == "main_font_preview":
            self._update_font_preview(text)
        elif preview_attr == "log_font_preview":
            self._update_log_font_preview(text)

        # Кнопка выбора
        ttk.Button(row, text="🔤", command=change_fn, bootstyle="info-outline", width=4).pack(
            side="left", padx=2
        )

    def _create_color_row(
        self,
        parent: ttk.Widget,
        label_text: str,
        label_attr: str,
        default_color: str,
        preview_attr: str,
        change_fn: callable,
        bootstyle: str = "primary-outline",
    ) -> None:
        """Создает строку настройки цвета с превью"""
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=PAD_Y, padx=PAD_FRAME_X)

        # Метка
        ttk.Label(row, text=label_text, width=LABEL_WIDTH, anchor="w").pack(side="left", padx=PAD_X)

        # Метка текущего цвета
        lbl = ttk.Label(row, text=tr("font_loading", "Загрузка..."), anchor="w")
        lbl.pack(side="left", padx=PAD_X, fill="x", expand=True)
        setattr(self, label_attr, lbl)

        # Превью цвета
        preview = tk.Canvas(
            row,
            width=COLOR_PREVIEW_WIDTH,
            height=COLOR_PREVIEW_HEIGHT,
            bg=default_color,
            relief="solid",
            borderwidth=1,
        )
        preview.pack(side="left", padx=PAD_X)
        setattr(self, preview_attr, preview)

        # Кнопка выбора
        ttk.Button(row, text="🎨", command=change_fn, bootstyle=bootstyle, width=BUTTON_WIDTH).pack(
            side="left", padx=PAD_X
        )

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
        # Можно заменить на более красивую подсветку поля

    def _create_verification_tab(self, parent: ttk.Widget) -> ttk.Frame:
        """Создает вкладку настроек верификации."""
        frame = ttk.Frame(parent, padding=10)
        lang_frame = ttk.LabelFrame(frame, text=tr("section_verification_lang", "Язык верификации"))
        lang_frame.pack(fill="x", pady=5)
        ttk.Label(lang_frame, text=tr("label_verify_lang", "Язык для проверки:")).pack(
            side="left", padx=5
        )
        self.language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.verification_language_var,
            values=SUPPORTED_LANGUAGES,
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

    def _change_main_font(self) -> None:
        """Изменить основной шрифт."""
        self._change_font("main_font", tr("font_main_name", "Osnovnoy"), "Segoe UI", 9)

    def _change_log_font(self) -> None:
        """Изменить шрифт логов."""
        self._change_font("log_font", tr("font_log_name", "Logi"), "Consolas", 10)

    def _change_tree_font(self) -> None:
        """Изменить шрифт дерева."""
        self._change_font("tree_font", tr("font_tree_name", "Derevo"), "Segoe UI", 9)

    def _apply_main_font_to_all(self) -> None:
        """Применяет основной шрифт ко всем элементам."""
        try:
            main_cfg = self.config.get("main_font", {"family": "Segoe UI", "size": 9})
            family = main_cfg.get("family", "Segoe UI")
            size = main_cfg.get("size", 9)

            config_mgr = get_config_manager()
            for key in ["main_font", "log_font", "tree_font"]:
                self.config[key] = {"family": family, "size": size}
                config_mgr.set(key, {"family": family, "size": size}, save=False)
            config_mgr.save()

            self._load_all_fonts_info()
            if self.on_font_change_callback:
                self.on_font_change_callback()

            logger.info(f"Шрифт {family}, {size}pt применён ко всем элементам")
            messagebox.showinfo(
                tr("msg_ok", "OK"),
                tr(
                    "msg_font_applied_all", "Шрифт {family}, {size}pt применён ко всем элементам"
                ).format(family=family, size=size),
            )
        except Exception as e:
            logger.error(f"Ошибка при применении шрифта: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _change_font(self, key: str, name: str, fam: str, sz: int) -> None:
        """Изменить шрифт с помощью диалога."""
        try:
            cur = self.config.get(key, {"family": fam, "size": sz})
            cur_family = cur.get("family", fam)
            cur_size = cur.get("size", sz)
            std_font = "TkDefaultFont"
            default = tkfont.nametofont(std_font)
            default.config(family=cur_family, size=cur_size)
            dlg = FontDialog(parent=self, default_font=std_font)
            selected_font = dlg.show()
            if selected_font is not None:
                actual_family = selected_font.cget("family")
                actual_size = selected_font.cget("size")
                self.config[key] = {
                    "family": actual_family,
                    "size": actual_size,
                }
                config_mgr = get_config_manager()
                config_mgr.set(key, self.config[key])
                self._load_all_fonts_info()
                if self.on_font_change_callback:
                    self.on_font_change_callback()
                logger.info(f"Шрифт {name} изменен на {actual_family}, {actual_size}pt")
                messagebox.showinfo(
                    tr("msg_ok", "OK"),
                    f"{name}: {actual_family}, {actual_size}pt",
                )
        except Exception as e:
            logger.error(f"Ошибка при изменении шрифта {key}: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _load_all_fonts_info(self) -> None:
        """Загрузить информацию о всех шрифтах."""
        for lbl, key, df in [
            ("main_font_label", "main_font", "Segoe UI, 9pt"),
            ("log_font_label", "log_font", "Consolas, 10pt"),
            ("tree_font_label", "tree_font", "Segoe UI, 9pt"),
        ]:
            if hasattr(self, lbl):
                cfg = self.config.get(key, {})
                txt = (
                    cfg.get("family", df.split(",")[0])
                    + ", "
                    + str(cfg.get("size", df.split(",")[1].strip().replace("pt", "")))
                    + "pt"
                )
                getattr(self, lbl).config(text=txt)

    def _reset_all_fonts(self) -> None:
        """Сбросить все шрифты к значениям по умолчанию."""
        try:
            from tkinter import messagebox

            if messagebox.askyesno(
                tr("msg_reset", "Сброс"), tr("msg_reset_fonts", "Сбросить все шрифты?")
            ):
                config_mgr = get_config_manager()
                for key, val in {
                    "main_font": {"family": "Segoe UI", "size": 9},
                    "log_font": {"family": "Consolas", "size": 10},
                    "tree_font": {"family": "Segoe UI", "size": 9},
                }.items():
                    self.config[key] = val
                    config_mgr.set(key, val, save=False)
                config_mgr.save()
                self._load_all_fonts_info()
                if self.on_font_change_callback:
                    self.on_font_change_callback()
                logger.info("Все шрифты сброшены")
                messagebox.showinfo(tr("msg_ok", "OK"), tr("msg_fonts_reset", "Шрифты сброшены."))
        except Exception as e:
            logger.error(f"Ошибка при сбросе шрифтов: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _change_text_color(self) -> None:
        """Изменить цвет текста."""
        self._change_color("text_color", tr("color_text", "Цвет текста"), "#2c3e50")

    def _change_bg_color(self) -> None:
        """Изменить цвет фона."""
        self._change_color("bg_color", tr("color_bg", "Цвет фона"), "#ffffff")

    def _change_accent_color(self) -> None:
        """Изменить цвет акцента."""
        self._change_color("accent_color", tr("color_accent", "Цвет акцента"), "#3498db")

    def _change_color(self, key: str, name: str, default_color: str) -> None:
        """Изменить цвет с помощью диалога."""
        try:
            from tkinter import colorchooser, messagebox

            current = self.config.get(key, default_color)
            color = colorchooser.askcolor(color=current, title=name)
            if color and color[1]:
                self.config[key] = color[1]
                config_mgr = get_config_manager()
                config_mgr.set(key, color[1])
                self._load_all_colors_info()
                if self.on_color_change_callback:
                    self.on_color_change_callback()
                logger.info(f"Цвет {name} изменен на {color[1]}")
                messagebox.showinfo(tr("msg_ok", "OK"), f"{name}: {color[1]}")
        except Exception as e:
            logger.error(f"Ошибка при изменении цвета {key}: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _load_all_colors_info(self) -> None:
        """Загрузить информацию о всех цветах."""
        color_map = [
            ("text_color_label", "text_color", "#2c3e50"),
            ("bg_color_label", "bg_color", "#ffffff"),
            ("accent_color_label", "accent_color", "#3498db"),
        ]
        for lbl, key, default in color_map:
            if hasattr(self, lbl):
                color_val = self.config.get(key, default)
                getattr(self, lbl).config(
                    text=color_val,
                    foreground=color_val,
                    background="#333333"
                    if color_val.lower() in ("#ffffff", "#fff", "white")
                    else "#ffffff",
                )

    def _reset_colors(self) -> None:
        """Сбросить все цвета к значениям по умолчанию."""
        try:
            from tkinter import messagebox

            if messagebox.askyesno(
                tr("msg_reset", "Сброс"), tr("msg_reset_colors", "Сбросить все цвета?")
            ):
                config_mgr = get_config_manager()
                for key, val in {
                    "text_color": "#2c3e50",
                    "bg_color": "#ffffff",
                    "accent_color": "#3498db",
                }.items():
                    self.config[key] = val
                    config_mgr.set(key, val, save=False)
                config_mgr.save()
                self._load_all_colors_info()
                if self.on_color_change_callback:
                    self.on_color_change_callback()
                logger.info("Все цвета сброшены")
                messagebox.showinfo(tr("msg_ok", "OK"), tr("msg_colors_reset", "Цвета сброшены."))
        except Exception as e:
            logger.error(f"Ошибка при сбросе цветов: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _change_log_bg_color(self) -> None:
        """Изменить цвет фона логов."""
        self._change_log_color("log_bg_color", tr("color_log_bg", "Фон логов"), "#1e1e1e")

    def _change_log_text_color(self) -> None:
        """Изменить цвет текста логов."""
        self._change_log_color("log_text_color", tr("color_log_text", "Текст логов"), "#d4d4d4")

    def _change_log_color(self, key: str, name: str, default_color: str) -> None:
        """Изменить цвет логов с помощью диалога."""
        try:
            from tkinter import colorchooser, messagebox

            current = self.config.get(key, default_color)
            color = colorchooser.askcolor(color=current, title=name)
            if color and color[1]:
                self.config[key] = color[1]
                config_mgr = get_config_manager()
                config_mgr.set(key, color[1])
                self._load_all_log_colors_info()
                if self.on_color_change_callback:
                    self.on_color_change_callback()
                logger.info(f"Цвет логов {name} изменен на {color[1]}")
                messagebox.showinfo(tr("msg_ok", "OK"), f"{name}: {color[1]}")
        except Exception as e:
            logger.error(f"Ошибка при изменении цвета логов {key}: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _load_all_log_colors_info(self) -> None:
        """Загрузить информацию о цветах логов."""
        for lbl, key, default in [
            ("log_bg_color_label", "log_bg_color", "#1e1e1e"),
            ("log_text_color_label", "log_text_color", "#d4d4d4"),
        ]:
            if hasattr(self, lbl):
                color_val = self.config.get(key, default)
                bg_preview = (
                    "#333333"
                    if color_val.lower() in ("#ffffff", "#fff", "white", "#d4d4d4")
                    else "#ffffff"
                )
                getattr(self, lbl).config(
                    text=color_val, foreground=color_val, background=bg_preview
                )

    def _reset_log_colors(self) -> None:
        """Сбросить цвета логов к значениям по умолчанию."""
        try:
            from tkinter import messagebox

            if messagebox.askyesno(
                tr("msg_reset", "Сброс"), tr("msg_reset_log_colors", "Сбросить цвета логов?")
            ):
                config_mgr = get_config_manager()
                for key, val in {
                    "log_bg_color": "#1e1e1e",
                    "log_text_color": "#d4d4d4",
                }.items():
                    self.config[key] = val
                    config_mgr.set(key, val, save=False)
                config_mgr.save()
                self._load_all_log_colors_info()
                if self.on_color_change_callback:
                    self.on_color_change_callback()
                logger.info("Цвета логов сброшены")
                messagebox.showinfo(
                    tr("msg_ok", "OK"), tr("msg_log_colors_reset", "Цвета логов сброшены.")
                )
        except Exception as e:
            logger.error(f"Ошибка при сбросе цветов логов: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

    def _change_log_tag_color(self, key: str) -> None:
        label_text = f"{tr('tag_color_prefix', 'Цвет тега')} ({key})"
        self._change_log_color(key, label_text, "log_tag_color_" + key)

    def _update_font_preview(self, text: str) -> None:
        """Обновить превью шрифта"""
        if hasattr(self, "main_font_preview"):
            self.main_font_preview.config(state="normal")
            self.main_font_preview.delete("1.0", "end")
            self.main_font_preview.insert("1.0", text)
            self.main_font_preview.config(state="disabled")

    def _update_log_font_preview(self, text: str) -> None:
        """Обновить превью шрифта логов"""
        if hasattr(self, "log_font_preview"):
            self.log_font_preview.config(state="normal")
            self.log_font_preview.delete("1.0", "end")
            self.log_font_preview.insert("1.0", text)
            self.log_font_preview.config(state="disabled")

    def _load_log_tag_colors_info(self) -> None:
        """Загрузить информацию о цветах тегов логов."""
        tag_colors = {
            "log_info_color": "#4fc3f7",
            "log_warning_color": "#ffb74d",
            "log_error_color": "#ef5350",
            "log_success_color": "#66bb6a",
        }
        for key, default in tag_colors.items():
            if key in self.log_tag_color_labels:
                color_val = self.config.get(key, default)
                bg_preview = (
                    "#333333" if color_val.lower() in ("#ffffff", "#fff", "white") else "#ffffff"
                )
                self.log_tag_color_labels[key].config(
                    text=color_val, foreground=color_val, background=bg_preview
                )
                # Обновить превью
                if key in self.log_tag_color_previews:
                    self.log_tag_color_previews[key].config(bg=color_val)

    def _is_dark_theme(self) -> bool:
        """Проверяет, используется ли тёмная тема"""
        theme = self.config.get("theme", "light")
        return theme in ("dark", "ocean", "superhero", "cyborg", "darkly", "solar")

    def _draw_ui_color_preview(self) -> None:
        """Нарисовать превью цветов интерфейса с учётом темы"""
        if not hasattr(self, "ui_color_preview"):
            return
        self.ui_color_preview.delete("all")
        width = self.ui_color_preview.winfo_reqwidth() or 300

        is_dark = self._is_dark_theme()

        # Выбираем цвета в зависимости от темы
        bg_color = PREVIEW_BG_DARK if is_dark else PREVIEW_BG_LIGHT
        text_color = PREVIEW_TEXT_DARK if is_dark else PREVIEW_TEXT_LIGHT
        outline_color = PREVIEW_OUTLINE_DARK if is_dark else PREVIEW_OUTLINE_LIGHT

        # Обновляем фон самого Canvas
        self.ui_color_preview.config(bg=bg_color)

        # Рисуем образец текста и фона
        self.ui_color_preview.create_rectangle(
            10, 10, width // 2 - 5, 50, fill=bg_color, outline=outline_color
        )
        self.ui_color_preview.create_text(
            width // 4, 30, text="Текст", fill=text_color, font=("Segoe UI", 12)
        )

        self.ui_color_preview.create_rectangle(
            width // 2 + 5, 10, width - 10, 50, fill=PREVIEW_ACCENT, outline=PREVIEW_ACCENT_OUTLINE
        )
        self.ui_color_preview.create_text(
            width * 3 // 4, 30, text="Акцент", fill=PREVIEW_TEXT_DARK, font=("Segoe UI", 12, "bold")
        )

    def _draw_log_color_preview(self) -> None:
        """Нарисовать превью цветов логов с учётом темы."""
        if not hasattr(self, "log_color_preview"):
            return
        self.log_color_preview.config(state="normal")
        self.log_color_preview.delete("1.0", "end")

        is_dark = self._is_dark_theme()

        # Для логов обычно используется тёмный фон, но проверим конфиг
        log_bg = self.config.get("log_bg_color", DEFAULT_LOG_BG)
        is_log_dark = self._is_color_dark(log_bg)

        text_color = "white" if is_log_dark else "black"
        secondary_text_color = DEFAULT_LOG_TEXT if is_log_dark else DARK_PREVIEW_BG

        self.log_color_preview.config(bg=log_bg)

        self.log_color_preview.insert("end", "[INFO] ", "cyan")
        self.log_color_preview.insert("end", "Загрузка завершена\n", text_color)

        self.log_color_preview.insert("end", "[WARN] ", "orange")
        self.log_color_preview.insert("end", "Проверьте настройки\n", text_color)

        self.log_color_preview.insert("end", "[ERROR] ", "red")
        self.log_color_preview.insert("end", "Ошибка подключения\n", text_color)

        self.log_color_preview.insert("end", "[OK] ", "green")
        self.log_color_preview.insert("end", "Операция выполнена", text_color)

        # Теги для цветов
        self.log_color_preview.tag_config("cyan", foreground=TAG_COLOR_INFO)
        self.log_color_preview.tag_config("orange", foreground=TAG_COLOR_WARNING)
        self.log_color_preview.tag_config("red", foreground=TAG_COLOR_ERROR)
        self.log_color_preview.tag_config("green", foreground=TAG_COLOR_SUCCESS)
        self.log_color_preview.tag_config("white", foreground=secondary_text_color)

        self.log_color_preview.config(state="disabled")

    def _is_color_dark(self, hex_color: str) -> bool:
        """Определяет, тёмный ли цвет (для контраста текста)"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return True
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Формула люминанса
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except ValueError:
            return True

    def _draw_log_tags_preview(self) -> None:
        """Нарисовать превью цветов тегов"""
        if not hasattr(self, "log_tags_preview_container"):
            return

        # Очистить старые виджеты
        for widget in self.log_tags_preview_container.winfo_children():
            widget.destroy()

        # Выбираем цвета текста в зависимости от темы
        badges = [
            ("ℹ️ Инфо", TAG_COLOR_INFO, TAG_TEXT_ON_DARK),
            ("⚠️ Предупреждение", TAG_COLOR_WARNING, TAG_TEXT_ON_DARK),
            ("❌ Ошибка", TAG_COLOR_ERROR, TAG_TEXT_ON_LIGHT),
            ("✅ Успех", TAG_COLOR_SUCCESS, TAG_TEXT_ON_DARK),
        ]

        for text, bg_color, fg_color in badges:
            badge = tk.Label(
                self.log_tags_preview_container,
                text=text,
                bg=bg_color,
                fg=fg_color,
                font=("Segoe UI", 9, "bold"),
                padx=BADGE_PADX,
                pady=BADGE_PADY,
                relief="raised",
                borderwidth=1,
            )
            badge.pack(side="left", padx=PAD_X, pady=PADY_SMALL)

    def _reset_log_tag_colors(self) -> None:
        """Сбросить цвета тегов логов к значениям по умолчанию."""
        try:
            from tkinter import messagebox

            if messagebox.askyesno(
                tr("msg_reset", "Сброс"),
                tr("msg_reset_log_tag_colors", "Сбросить цвета тегов логов?"),
            ):
                defaults = {
                    "log_info_color": "#4fc3f7",
                    "log_warning_color": "#ffb74d",
                    "log_error_color": "#ef5350",
                    "log_success_color": "#66bb6a",
                }
                for key, val in defaults.items():
                    self.config[key] = val
                    config_mgr.set(key, val, save=False)
                config_mgr.save()
                self._load_log_tag_colors_info()
                if self.on_color_change_callback:
                    self.on_color_change_callback()
                logger.info("Цвета тегов логов сброшены")
                messagebox.showinfo(
                    tr("msg_ok", "OK"),
                    tr("msg_log_tag_colors_reset", "Цвета тегов логов сброшены."),
                )
        except Exception as e:
            logger.error(f"Ошибка при сбросе цветов тегов логов: {e}")
            messagebox.showerror(tr("msg_error", "Ошибка"), str(e))

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
                self.config = {
                    "source_language": "English",
                    "target_language": "Russian",
                    "verification_language": "Russian",
                    "translation_mode": "separate",
                    "verbose": False,
                    "auto_backup": True,
                }
                self.apply_config(self.config)
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

    def get_options(self) -> dict[str, Any]:
        """Получить текущие настройки."""
        # Собираем настройки движков
        engine_config = {}
        for key, var in self.engine_vars.items():
            engine_config[f"engine_{key}_enabled"] = var.get()

        return {
            "preset_file": self.preset_entry.get(),
            "verbose": self.verbose_var.get(),
            "auto_backup": self.auto_backup_var.get(),
            "verification_language": self.verification_language_var.get(),
            "translation_mode": self.translation_mode_var.get(),
            "source_language": getattr(
                self, "source_lang_var", tk.StringVar(value="English")
            ).get(),
            "target_language": getattr(
                self, "target_lang_var", tk.StringVar(value="Russian")
            ).get(),
            # ✅ НОВОЕ: Настройки переводчиков
            **engine_config,
            "smart_routing": self.smart_routing_var.get(),
            "split_long_text": self.split_long_text_var.get(),
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
        if hasattr(self, "source_lang_var"):
            self.source_lang_var.set(config.get("source_language", "English"))
        if hasattr(self, "target_lang_var"):
            self.target_lang_var.set(config.get("target_language", "Russian"))

        # ✅ НОВОЕ: Применяем настройки переводчиков
        if hasattr(self, "engine_vars"):
            for key in self.engine_vars:
                self.engine_vars[key].set(
                    config.get(
                        f"engine_{key}_enabled", key in ["google", "mymemory", "deepl", "bing"]
                    )
                )

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
            settings_data = {
                "version": "2.0",
                "timestamp": datetime.now().isoformat(),
                "config": self.get_options(),
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
