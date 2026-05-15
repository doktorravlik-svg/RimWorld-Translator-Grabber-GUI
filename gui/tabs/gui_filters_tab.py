"""
Вкладка фильтров - обновлённая версия.

Учитывает все новые возможности:
- slateRef теги для QuestScriptDef
- Частичное совпадение тегов (PARTIAL_TAG_MATCHES)
- elem_tag_check (добавление недостающих полей)
- ModSettingsFramework Keyed из патчей
"""

import json
import os
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from gui.constants import PAD_BTN_X, PAD_FRAME_X, PAD_FRAME_Y
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip

# Путь к конфигу
FILTERS_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "filters_config.json",
)

# ========================================
# ОБНОВЛЁННЫЕ списки тегов
# ========================================

DEFAULT_WHITELIST = [
    # Базовые
    "label",
    "labelShort",
    "labelPlural",
    "labelNoun",
    "labelNounPretty",
    "description",
    "desc",
    "text",
    "title",
    "tooltip",
    "helpText",
    # Специфичные
    "reportString",
    "jobString",
    "ingestCommandString",
    "ingestReportString",
    "skillLabel",
    "pawnLabel",
    "pawnLabelNoun",
    "pawnSingular",
    "pawnsPlural",
    "deathMessage",
    "useLabel",
    "verb",
    "gerund",
    "beginLetterLabel",
    "beginLetter",
    "recoveryMessage",
    "letterLabel",
    "letterText",
    "notification",
    "baseInspectLine",
    # Ideology
    "ideoName",
    "member",
    "theme",
    "leaderTitle",
    "structureLabel",
    # Materials
    "stuffAdjective",
    "adjective",
    # Quest
    "summary",
    # Backstory
    "titleShort",
    "titleFemale",
    "titleMale",
    "baseDesc",
    # Weapon/Verb
    "commandDesc",
    "commandLabel",
    "chargeNoun",
    "cooldownGerund",
    # Дополнительные
    "customLabel",
    "customLetterLabel",
    "customLetterText",
    "outOfFuelMessage",
    "name",
    # slateRef для QuestScriptDef (НОВОЕ)
    "slateRef",
    "slate",
    # ModSettingsFramework (НОВОЕ)
    "tKey",
    "tKeyTip",
]

DEFAULT_BLACKLIST = [
    "defName",
    "modContentPack",
    "modMetaData",
    "Abstract",
    "workerClass",
    "driverClass",
    "graphicData",
    "texture",
    "sound",
    "costList",
    "thingClass",
    "statBases",
    "comps",
    "verbs",
    # Технические
    "ParentName",
    "Name",
    "MayRequire",
    "MayRequireAny",
    "MayRequireActive",
    "Class",
]

DEFAULT_PATTERNS = [
    "internal_",
    "debug_",
    "tmp_",
    "icon",
    "texture",
    "sprite",
    "gfx",
    "sound_",
    "audio_",
    "shader",
    "mesh",
    "costList",
    r".*\.points\.\d+",
    r".*\.li\d*",
]

DEFAULT_PRIORITY_SUFFIXES = [
    "label",
    "description",
    "reportString",
    "jobString",
    "title",
    "text",
    "tooltip",
    "letterLabel",
    "letterText",
]

# Частичные совпадения тегов (Part_of_tag_to_extraction из Text-grabber)
DEFAULT_PARTIAL_MATCHES = [
    "Message",
    "Label",
    "Title",
    "Text",
    "gerund",
    "Explanation",
    "description",
    "Hint",
    "Name",
]


class FiltersTab(ttk.Frame):
    """Обновлённая вкладка фильтров."""

    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.config = self._load_filters_config()
        self._setup_ui()

    def _load_filters_config(self) -> dict:
        try:
            with open(FILTERS_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        return {
            "whitelist_tags": DEFAULT_WHITELIST,
            "blacklist_tags": DEFAULT_BLACKLIST,
            "blacklist_patterns": DEFAULT_PATTERNS,
            "partial_tag_matches": DEFAULT_PARTIAL_MATCHES,
            "keyed_as_direct": [],
            "aggressive_fallback": False,
            "min_text_length": 2,
            "max_text_length": 200,
            "priority_suffixes": DEFAULT_PRIORITY_SUFFIXES,
            "enable_space_fallback": True,
            "enable_elem_tag_check": True,
            "enable_mod_settings_framework": True,
            "enable_dollar_variable_replace": True,
        }

    def _save_filters_config(self):
        try:
            with open(FILTERS_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo(
                tr("success", "Успех"),
                tr("filters_saved", "Настройки фильтров сохранены!")
                + "\n\n"
                + tr(
                    "filters_restart_may_be_needed",
                    "Для применения изменений может потребоваться перезапуск программы.",
                ),
            )
            if self.on_save_callback:
                self.on_save_callback(self.config)
        except Exception as e:
            messagebox.showerror(
                tr("error", "Ошибка"),
                tr("filters_save_error", "Не удалось сохранить конфигурацию:") + f"\n{e}",
            )

    def _setup_ui(self):
        """Настройка интерфейса вкладки"""
        # Заголовок
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            title_frame,
            text=tr("filters_title", "Настройка фильтров извлечения текста"),
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            title_frame,
            text=tr(
                "filters_subtitle",
                "Настройте правила для извлечения переводимого текста из модов",
            ),
            foreground="gray",
        ).pack(anchor="w")

        # Notebook с вкладками
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.whitelist_tab = self._create_whitelist_tab(notebook)
        notebook.add(self.whitelist_tab, text=tr("filters_tab_whitelist", "Whitelist тегов"))

        self.blacklist_tab = self._create_blacklist_tab(notebook)
        notebook.add(self.blacklist_tab, text=tr("filters_tab_blacklist", "Blacklist тегов"))

        self.patterns_tab = self._create_patterns_tab(notebook)
        notebook.add(self.patterns_tab, text=tr("filters_tab_patterns", "Паттерны"))

        # ✅ НОВАЯ: Вкладка Partial Tag Matches
        self.partial_tab = self._create_partial_matches_tab(notebook)
        notebook.add(self.partial_tab, text=tr("filters_tab_partial", "Частичные совпадения"))

        # ✅ НОВАЯ: Вкладка расширенных настроек
        self.advanced_tab = self._create_advanced_tab(notebook)
        notebook.add(self.advanced_tab, text=tr("filters_tab_advanced", "Расширенные"))

        # Кнопки действий
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        btn_save = ttk.Button(
            btn_frame,
            text=tr("filters_save_button", "💾 Сохранить"),
            command=self._on_save,
            bootstyle="success",
        )
        btn_save.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_save, "Сохранить настройки фильтров")

        btn_reset = ttk.Button(
            btn_frame,
            text=tr("filters_reset_button", "🔄 Сбросить"),
            command=self._on_reset,
            bootstyle="warning",
        )
        btn_reset.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_reset, "Сбросить все настройки к умолчаниям")

        btn_open = ttk.Button(
            btn_frame,
            text=tr("filters_open_config_button", "📂 Открыть конфиг"),
            command=self._open_config_file,
            bootstyle="info",
        )
        btn_open.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_open, "Открыть filters_config.json")

        btn_help = ttk.Button(
            btn_frame,
            text=tr("filters_help_button", "❓ Справка"),
            command=self._show_help,
            bootstyle="secondary-outline",
        )
        btn_help.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_help, "Показать справку по фильтрам")

    # ========================================
    # WHITELIST
    # ========================================

    def _create_whitelist_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)
        ttk.Label(
            frame,
            text=tr("filters_whitelist_description", "Теги, которые ИЗВЛЕКАЮТСЯ для перевода:"),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        text_frame = ttk.LabelFrame(
            frame, text=tr("filters_whitelist_text_area", "Whitelist тегов (по одному в строке)")
        )
        text_frame.pack(fill="both", expand=True, pady=5)

        self.whitelist_text = tk.Text(text_frame, height=20, width=60, wrap="none")
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.whitelist_text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.whitelist_text.xview)
        self.whitelist_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.whitelist_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        hsb.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        for tag in self.config.get("whitelist_tags", DEFAULT_WHITELIST):
            self.whitelist_text.insert("end", f"{tag}\n")

        self.whitelist_text.bind("<KeyRelease>", self._on_text_change)

        # Быстрое добавление
        quick_frame = ttk.Frame(frame)
        quick_frame.pack(fill="x", pady=5)
        ttk.Label(quick_frame, text=tr("filters_quick_add", "Быстро добавить:")).pack(
            side="left", padx=5
        )
        common_tags = [
            "label",
            "description",
            "text",
            "title",
            "tooltip",
            "letterText",
            "slateRef",
            "tKey",
        ]
        for tag in common_tags:
            ttk.Button(
                quick_frame,
                text=f"+ {tag}",
                width=12,
                command=lambda t=tag: self._add_tag_to_whitelist(t),
            ).pack(side="left", padx=2)

        return frame

    def _add_tag_to_whitelist(self, tag: str):
        current = self.whitelist_text.get("1.0", "end").strip()
        if tag not in current:
            self.whitelist_text.insert("end", f"\n{tag}")

    # ========================================
    # BLACKLIST
    # ========================================

    def _create_blacklist_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)
        ttk.Label(
            frame,
            text=tr("filters_blacklist_description", "Теги, которые ИГНОРИРУЮТСЯ (технические):"),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        text_frame = ttk.LabelFrame(
            frame, text=tr("filters_blacklist_text_area", "Blacklist тегов (по одному в строке)")
        )
        text_frame.pack(fill="both", expand=True, pady=5)

        self.blacklist_text = tk.Text(text_frame, height=15, width=60, wrap="none")
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.blacklist_text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.blacklist_text.xview)
        self.blacklist_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.blacklist_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        hsb.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        for tag in self.config.get("blacklist_tags", DEFAULT_BLACKLIST):
            self.blacklist_text.insert("end", f"{tag}\n")

        self.blacklist_text.bind("<KeyRelease>", self._on_text_change)
        return frame

    # ========================================
    # PATTERNS
    # ========================================

    def _create_patterns_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)

        # Паттерны
        ttk.Label(
            frame,
            text=tr("filters_patterns_description", "Ключи содержащие эти слова будут пропущены:"),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        text_frame = ttk.LabelFrame(
            frame, text=tr("filters_patterns_text_area", "Blacklist паттерны (по одному в строке)")
        )
        text_frame.pack(fill="both", expand=True, pady=5)

        self.patterns_text = tk.Text(text_frame, height=15, width=60, wrap="none")
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.patterns_text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.patterns_text.xview)
        self.patterns_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.patterns_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        hsb.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        for pattern in self.config.get("blacklist_patterns", DEFAULT_PATTERNS):
            self.patterns_text.insert("end", f"{pattern}\n")

        self.patterns_text.bind("<KeyRelease>", self._on_text_change)

        # Минимальная длина
        min_len_frame = ttk.Frame(frame)
        min_len_frame.pack(fill="x", pady=5)
        ttk.Label(min_len_frame, text=tr("filters_min_length", "Минимальная длина текста:")).pack(
            side="left", padx=5
        )
        self.min_length_var = tk.StringVar(value=str(self.config.get("min_text_length", 2)))
        min_len_entry = ttk.Entry(min_len_frame, textvariable=self.min_length_var, width=5)
        min_len_entry.pack(side="left", padx=5)
        min_len_entry.bind("<KeyRelease>", self._on_text_change)

        # Максимальная длина
        max_len_frame = ttk.Frame(frame)
        max_len_frame.pack(fill="x", pady=5)
        ttk.Label(max_len_frame, text=tr("filters_max_length", "Максимальная длина текста:")).pack(
            side="left", padx=5
        )
        self.max_length_var = tk.StringVar(value=str(self.config.get("max_text_length", 200)))
        max_len_entry = ttk.Entry(max_len_frame, textvariable=self.max_length_var, width=5)
        max_len_entry.pack(side="left", padx=5)
        max_len_entry.bind("<KeyRelease>", self._on_text_change)

        # Приоритетные суффиксы
        ttk.Label(
            frame,
            text=tr(
                "filters_priority_description", "Приоритетные суффиксы (обрабатываются первыми):"
            ),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(10, 10))

        priority_frame = ttk.LabelFrame(frame, text=tr("filters_priority_suffixes", "Приоритетные суффиксы"))
        priority_frame.pack(fill="both", expand=True, pady=5)

        self.priority_text = tk.Text(priority_frame, height=8, width=60, wrap="none")
        vsb2 = ttk.Scrollbar(priority_frame, orient="vertical", command=self.priority_text.yview)
        self.priority_text.configure(yscrollcommand=vsb2.set)
        self.priority_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        vsb2.pack(side="right", fill="y", padx=(0, 5), pady=5)

        for suffix in self.config.get("priority_suffixes", DEFAULT_PRIORITY_SUFFIXES):
            self.priority_text.insert("end", f"{suffix}\n")

        self.priority_text.bind("<KeyRelease>", self._on_text_change)

        return frame

    # ========================================
    # PARTIAL TAG MATCHES (НОВАЯ)
    # ========================================

    def _create_partial_matches_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)

        ttk.Label(
            frame,
            text=tr(
                "filters_partial_description",
                "Части тегов для частичного совпадения (как Part_of_tag_to_extraction из Text-grabber).\n"
                "Если тег содержит одно из этих слов, он будет извлечён.",
            ),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        text_frame = ttk.LabelFrame(
            frame, text=tr("filters_partial_text_area", "Частичные совпадения (по одному в строке)")
        )
        text_frame.pack(fill="both", expand=True, pady=5)

        self.partial_text = tk.Text(text_frame, height=12, width=60, wrap="none")
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.partial_text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self.partial_text.xview)
        self.partial_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.partial_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        vsb.grid(row=0, column=1, sticky="ns", padx=(0, 5), pady=5)
        hsb.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        for match in self.config.get("partial_tag_matches", DEFAULT_PARTIAL_MATCHES):
            self.partial_text.insert("end", f"{match}\n")

        self.partial_text.bind("<KeyRelease>", self._on_text_change)

        return frame

    # ========================================
    # ADVANCED SETTINGS (НОВАЯ)
    # ========================================

    def _create_advanced_tab(self, parent) -> ttk.Frame:
        frame = ttk.Frame(parent, padding=10)

        # Включить/выключить функции
        ttk.Label(
            frame,
            text=tr("filters_advanced_description", "Расширенные настройки извлечения текста:"),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # elem_tag_check
        self.enable_elem_tag_check_var = tk.BooleanVar(
            value=self.config.get("enable_elem_tag_check", True)
        )
        ttk.Checkbutton(
            frame,
            text=tr(
                "filters_elem_tag_check",
                "✅ elem_tag_check - добавлять недостающие поля для Def типов",
            ),
            variable=self.enable_elem_tag_check_var,
            command=self._on_text_change,
        ).pack(anchor="w", pady=2)

        # Space fallback
        self.enable_space_fallback_var = tk.BooleanVar(
            value=self.config.get("enable_space_fallback", True)
        )
        ttk.Checkbutton(
            frame,
            text=tr(
                "filters_space_fallback",
                "✅ Fallback по пробелу - извлекать текст с пробелами даже если тег не в whitelist",
            ),
            variable=self.enable_space_fallback_var,
            command=self._on_text_change,
        ).pack(anchor="w", pady=2)

        # ModSettingsFramework
        self.enable_msf_var = tk.BooleanVar(
            value=self.config.get("enable_mod_settings_framework", True)
        )
        ttk.Checkbutton(
            frame,
            text=tr(
                "filters_msf", "✅ ModSettingsFramework - извлекать Keyed строки из патчей настроек"
            ),
            variable=self.enable_msf_var,
            command=self._on_text_change,
        ).pack(anchor="w", pady=2)

        # Dollar variable replace
        self.enable_dollar_var = tk.BooleanVar(
            value=self.config.get("enable_dollar_variable_replace", True)
        )
        ttk.Checkbutton(
            frame,
            text=tr(
                "filters_dollar_replace",
                "✅ dollar_variable_replace - заменять $variable в QuestScriptDef",
            ),
            variable=self.enable_dollar_var,
            command=self._on_text_change,
        ).pack(anchor="w", pady=2)

        # Aggressive fallback
        self.aggressive_var = tk.BooleanVar(value=self.config.get("aggressive_fallback", False))
        ttk.Checkbutton(
            frame,
            text=tr(
                "filters_aggressive",
                "⚠️ Агрессивный fallback - извлекать ВСЕ теги (может добавить шум)",
            ),
            variable=self.aggressive_var,
            command=self._on_text_change,
        ).pack(anchor="w", pady=2)

        return frame

    # ========================================
    # GET OPTIONS / APPLY CONFIG
    # ========================================

    def get_filters_config(self):
        """Получить текущие настройки фильтров"""
        self._save_config_from_ui()  # Обновляем self.config из UI
        return self.config.copy()

    def apply_filters_config(self, config):
        """Применить настройки фильтров из словаря"""
        # Обновляем только ключи, относящиеся к фильтрам
        filter_keys = [
            "whitelist_tags", "blacklist_tags", "blacklist_patterns",
            "priority_suffixes", "partial_tag_matches", "min_text_length",
            "max_text_length", "enable_elem_tag_check", "enable_space_fallback",
            "enable_mod_settings_framework", "enable_dollar_variable_replace",
            "aggressive_fallback"
        ]
        for key in filter_keys:
            if key in config:
                self.config[key] = config[key]
        
        # ✅ ИСПРАВЛЕНО: Обновляем UI без уничтожения виджета
        # Пересоздаём содержимое вкладки вместо уничтожения
        for widget in self.winfo_children():
            widget.destroy()
        self._setup_ui()
        
        return self  # Возвращаем тот же экземпляр

    # ========================================
    # CALLBACKS
    # ========================================

    def _on_text_change(self, event=None):
        self.after(300, self._save_config_from_ui)

    def _save_config_from_ui(self):
        self.config["whitelist_tags"] = [
            line.strip()
            for line in self.whitelist_text.get("1.0", "end").split("\n")
            if line.strip()
        ]
        self.config["blacklist_tags"] = [
            line.strip()
            for line in self.blacklist_text.get("1.0", "end").split("\n")
            if line.strip()
        ]
        self.config["blacklist_patterns"] = [
            line.strip()
            for line in self.patterns_text.get("1.0", "end").split("\n")
            if line.strip()
        ]
        self.config["priority_suffixes"] = [
            line.strip()
            for line in self.priority_text.get("1.0", "end").split("\n")
            if line.strip()
        ]
        self.config["partial_tag_matches"] = [
            line.strip() for line in self.partial_text.get("1.0", "end").split("\n") if line.strip()
        ]
        if hasattr(self, "min_length_var"):
            try:
                self.config["min_text_length"] = int(self.min_length_var.get())
            except ValueError:
                pass
        if hasattr(self, "max_length_var"):
            try:
                self.config["max_text_length"] = int(self.max_length_var.get())
            except ValueError:
                pass
        if hasattr(self, "enable_elem_tag_check_var"):
            self.config["enable_elem_tag_check"] = self.enable_elem_tag_check_var.get()
        if hasattr(self, "enable_space_fallback_var"):
            self.config["enable_space_fallback"] = self.enable_space_fallback_var.get()
        if hasattr(self, "enable_msf_var"):
            self.config["enable_mod_settings_framework"] = self.enable_msf_var.get()
        if hasattr(self, "enable_dollar_var"):
            self.config["enable_dollar_variable_replace"] = self.enable_dollar_var.get()
        if hasattr(self, "aggressive_var"):
            self.config["aggressive_fallback"] = self.aggressive_var.get()

        # Автосохранение
        try:
            with open(FILTERS_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def _on_save(self):
        self._save_config_from_ui()
        self._save_filters_config()

    def _on_reset(self):
        if messagebox.askyesno(
            tr("confirm_reset", "Подтверждение"),
            tr(
                "filters_reset_confirm", "Сбросить все настройки фильтров к значениям по умолчанию?"
            ),
        ):
            self.config = self._get_default_config()
            self._setup_ui()
            self._save_filters_config()

    def _open_config_file(self):
        try:
            import subprocess

            subprocess.Popen(["notepad", FILTERS_CONFIG_FILE])
        except Exception as e:
            messagebox.showerror(tr("error", "Ошибка"), f"Не удалось открыть файл:\n{e}")

    def _show_help(self):
        help_text = (
            tr("filters_help_title", "Справка по фильтрам")
            + "\n\n"
            + tr("filters_help_whitelist", "• Whitelist теги — XML-теги для извлечения")
            + "\n"
            + tr("filters_help_blacklist", "• Blacklist теги — технические теги для пропуска")
            + "\n"
            + tr("filters_help_patterns", "• Паттерны — ключи содержащие эти слова будут пропущены")
            + "\n"
            + tr(
                "filters_help_partial",
                "• Частичные совпадения — если тег содержит одно из этих слов, он извлекается",
            )
            + "\n"
            + tr(
                "filters_help_elem_tag_check",
                "• elem_tag_check — добавляет недостающие поля для Def типов",
            )
            + "\n"
            + tr(
                "filters_help_space_fallback",
                "• Fallback по пробелу — извлекает текст с пробелами даже если тег не в whitelist",
            )
            + "\n"
            + tr(
                "filters_help_msf",
                "• ModSettingsFramework — извлекает Keyed строки из патчей настроек",
            )
            + "\n"
            + tr(
                "filters_help_dollar",
                "• dollar_variable_replace — заменяет $variable в QuestScriptDef",
            )
            + "\n\n"
            + tr(
                "filters_help_note",
                "⚠️ Настройки сохраняются в filters_config.json.\nДля применения может потребоваться перезапуск.",
            )
        )
        messagebox.showinfo(tr("filters_help_title", "❓ Справка по фильтрам"), help_text)
