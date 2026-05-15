"""
Settings Glossary Manager - управление настройками редактора глоссария.

Отвечает за:
- Настройку отображения колонок
- Настройку фильтров
- Настройку поведения редактора
- Настройку цветов категорий
"""

import tkinter as tk
from tkinter import colorchooser, messagebox
from gui.gui_i18n import tr
from typing import Any, Callable, Dict, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class SettingsGlossaryManager:
    DEFAULT_SETTINGS = {
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

    def __init__(
        self,
        parent: ttk.Frame,
        config: dict,
        is_dark_theme: Callable[[], bool]
    ):
        self.parent = parent
        self.config = config
        self.is_dark_theme = is_dark_theme
        self._check_vars: Dict[str, tk.BooleanVar] = {}
        self._int_vars: Dict[str, tk.IntVar] = {}
        self._float_vars: Dict[str, tk.DoubleVar] = {}
        self._str_vars: Dict[str, tk.StringVar] = {}
        self._color_preview_widgets: Dict[str, tk.Canvas] = {}
        self._name_entry_widgets: Dict[str, ttk.Entry] = {}
        self._new_category_var: tk.StringVar = tk.StringVar()
        self._new_category_color_var: tk.StringVar = tk.StringVar(value="#888888")

    def create_glossary_section(self, container: ttk.Frame) -> None:
        section = ttk.Frame(container)
        section.pack(fill="x", padx=5, pady=5)

        self._create_setting_row(section, "glossary_auto_split", "Автоматически разделять глоссарий на файлы", "check")
        self._create_setting_row(section, "glossary_show_description", "Показывать колонку описания", "check")
        self._create_setting_row(section, "glossary_show_usage_count", "Показывать колонку использований", "check")
        self._create_setting_row(section, "glossary_confirm_on_delete", "Подтверждать удаление терминов", "check")

        ttk.Label(section, text="Размер страницы:", width=30, anchor="w").pack(anchor="w", padx=5, pady=(5, 0))
        size_frame = ttk.Frame(section)
        size_frame.pack(fill="x", padx=5, pady=2)
        self._int_vars["glossary_page_size"] = tk.IntVar(value=self.config.get("glossary_page_size", 100))
        ttk.Entry(size_frame, textvariable=self._int_vars["glossary_page_size"], width=10).pack(side="left", padx=2)
        self._int_vars["glossary_page_size"].trace_add("write", lambda *a: self._save_int("glossary_page_size"))

        ttk.Label(section, text="Уверенность по умолчанию:", width=30, anchor="w").pack(anchor="w", padx=5, pady=(5, 0))
        conf_frame = ttk.Frame(section)
        conf_frame.pack(fill="x", padx=5, pady=2)
        self._float_vars["glossary_default_confidence"] = tk.DoubleVar(value=self.config.get("glossary_default_confidence", 0.0))
        ttk.Entry(conf_frame, textvariable=self._float_vars["glossary_default_confidence"], width=10).pack(side="left", padx=2)
        self._float_vars["glossary_default_confidence"].trace_add("write", lambda *a: self._save_float("glossary_default_confidence"))

        self._create_category_colors_section(section)

    def _create_category_colors_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Цвета категорий")
        section.pack(fill="x", padx=5, pady=5)

        category_colors = self.config.get("glossary_category_colors", self.DEFAULT_SETTINGS["glossary_category_colors"])
        category_names = self.config.get("glossary_category_names", self.DEFAULT_SETTINGS["glossary_category_names"])
        
        for category, default_color in self.DEFAULT_SETTINGS["glossary_category_colors"].items():
            color = category_colors.get(category, default_color)
            name = category_names.get(category, self.DEFAULT_SETTINGS["glossary_category_names"].get(category, category))
            row = ttk.Frame(section)
            row.pack(fill="x", padx=5, pady=2)
            
            name_var = tk.StringVar(value=name)
            self._str_vars[f"cat_name_{category}"] = name_var
            name_entry = ttk.Entry(row, textvariable=name_var, width=15)
            name_entry.pack(side="left", padx=2)
            self._name_entry_widgets[category] = name_entry
            name_var.trace_add("write", lambda *a, c=category: self._save_category_name(c))
            
            preview = tk.Canvas(row, width=30, height=20, bg=color, relief="solid", borderwidth=1)
            preview.pack(side="left", padx=2)
            self._color_preview_widgets[category] = preview
            
            ttk.Button(
                row,
                text="🎨",
                command=lambda c=category: self._change_category_color(c),
                bootstyle="info-outline",
                width=4
            ).pack(side="left", padx=2)

        self._create_add_category_section(section)

    def _create_add_category_section(self, parent: ttk.Frame) -> None:
        add_frame = ttk.Frame(parent)
        add_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(add_frame, text="Добавить:", width=15, anchor="w").pack(side="left", padx=2)
        ttk.Entry(add_frame, textvariable=self._new_category_var, width=15).pack(side="left", padx=2)
        
        preview = tk.Canvas(add_frame, width=30, height=20, bg="#888888", relief="solid", borderwidth=1)
        preview.pack(side="left", padx=2)
        
        ttk.Button(
            add_frame,
            text="🎨",
            command=self._choose_new_category_color,
            bootstyle="info-outline",
            width=4
        ).pack(side="left", padx=2)
        
        ttk.Button(
            add_frame,
            text="+",
            command=self._add_new_category,
            bootstyle="success",
            width=4
        ).pack(side="left", padx=2)

    def _choose_new_category_color(self) -> None:
        color = colorchooser.askcolor(color="#888888", title=tr("glossary_new_category_color", "Цвет новой категории"))
        if color and color[1]:
            self._new_category_color_var.set(color[1])
            for widget in self.winfo_children():
                if isinstance(widget, tk.Canvas):
                    widget.config(bg=color[1])

    def _add_new_category(self) -> None:
        new_key = self._new_category_var.get().strip().lower()
        new_name = self._new_category_var.get().strip()
        new_color = self._new_category_color_var.get()
        
        if not new_key or not new_name:
            messagebox.showwarning(tr("glossary_confirm_category", "Предупреждение"), tr("glossary_enter_category_name", "Введите название категории"))
            return
        
        if new_key in self.config.get("glossary_category_colors", {}):
            if not messagebox.askyesno(tr("glossary_confirm_category", "Подтверждение"), tr("glossary_category_exists", f"Категория '{new_name}' уже существует. Перезаписать?")):
                return
        
        if "glossary_category_colors" not in self.config:
            self.config["glossary_category_colors"] = {}
        if "glossary_category_names" not in self.config:
            self.config["glossary_category_names"] = {}
        
        self.config["glossary_category_colors"][new_key] = new_color
        self.config["glossary_category_names"][new_key] = new_name
        
        self._color_preview_widgets[new_key] = tk.Canvas(self.parent, width=30, height=20, bg=new_color, relief="solid", borderwidth=1)
        self._str_vars[f"cat_name_{new_key}"] = tk.StringVar(value=new_name)
        
        self._new_category_var.set("")
        self._new_category_color_var.set("#888888")

    def _save_category_name(self, category: str) -> None:
        if f"cat_name_{category}" in self._str_vars:
            names = self.config.get("glossary_category_names", {})
            if "glossary_category_names" not in self.config:
                self.config["glossary_category_names"] = {}
            self.config["glossary_category_names"][category] = self._str_vars[f"cat_name_{category}"].get()

    def _change_category_color(self, category: str) -> None:
        current_colors = self.config.get("glossary_category_colors", self.DEFAULT_SETTINGS["glossary_category_colors"])
        current = current_colors.get(category, self.DEFAULT_SETTINGS["glossary_category_colors"][category])
        color = colorchooser.askcolor(color=current, title=f"Цвет категории {category}")
        if color and color[1]:
            if "glossary_category_colors" not in self.config:
                self.config["glossary_category_colors"] = {}
            self.config["glossary_category_colors"][category] = color[1]
            if category in self._color_preview_widgets:
                self._color_preview_widgets[category].config(bg=color[1])

    def _create_setting_row(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        setting_type: str
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        if label:
            ttk.Label(row, text=label, width=30, anchor="w").pack(side="left", padx=2)

        if setting_type == "check":
            var = tk.BooleanVar(value=self.config.get(key, self.DEFAULT_SETTINGS[key]))
            self._check_vars[key] = var
            chk = ttk.Checkbutton(row, variable=var)
            chk.pack(side="left", padx=2)
            var.trace_add("write", lambda *a, k=key: self._save_check(k))
        elif setting_type == "int":
            var = tk.IntVar(value=self.config.get(key, self.DEFAULT_SETTINGS[key]))
            self._int_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=10)
            entry.pack(side="left", padx=2)
            var.trace_add("write", lambda *a, k=key: self._save_int(k))
        elif setting_type == "float":
            var = tk.DoubleVar(value=self.config.get(key, self.DEFAULT_SETTINGS[key]))
            self._float_vars[key] = var
            entry = ttk.Entry(row, textvariable=var, width=10)
            entry.pack(side="left", padx=2)
            var.trace_add("write", lambda *a, k=key: self._save_float(k))

    def _save_check(self, key: str) -> None:
        self.config[key] = self._check_vars[key].get()

    def _save_int(self, key: str) -> None:
        try:
            self.config[key] = self._int_vars[key].get()
        except tk.TclError:
            pass

    def _save_float(self, key: str) -> None:
        try:
            self.config[key] = self._float_vars[key].get()
        except tk.TclError:
            pass

    def save_settings(self) -> None:
        for key, var in self._check_vars.items():
            self.config[key] = var.get()
        for key, var in self._int_vars.items():
            try:
                self.config[key] = var.get()
            except tk.TclError:
                self.config[key] = self.DEFAULT_SETTINGS[key]
        for key, var in self._float_vars.items():
            try:
                self.config[key] = var.get()
            except tk.TclError:
                self.config[key] = self.DEFAULT_SETTINGS[key]
        for key, var in self._str_vars.items():
            if key.startswith("cat_name_"):
                category = key.replace("cat_name_", "")
                if "glossary_category_names" not in self.config:
                    self.config["glossary_category_names"] = {}
                self.config["glossary_category_names"][category] = var.get()

    def load_settings(self) -> None:
        for key, var in self._check_vars.items():
            var.set(self.config.get(key, self.DEFAULT_SETTINGS.get(key)))
        for key, var in self._int_vars.items():
            var.set(self.config.get(key, self.DEFAULT_SETTINGS.get(key)))
        for key, var in self._float_vars.items():
            var.set(self.config.get(key, self.DEFAULT_SETTINGS.get(key)))
        category_colors = self.config.get("glossary_category_colors", self.DEFAULT_SETTINGS["glossary_category_colors"])
        category_names = self.config.get("glossary_category_names", self.DEFAULT_SETTINGS["glossary_category_names"])
        for key, var in self._str_vars.items():
            if key.startswith("cat_name_"):
                category = key.replace("cat_name_", "")
                var.set(category_names.get(category, self.DEFAULT_SETTINGS["glossary_category_names"].get(category, category)))
                if category in self._color_preview_widgets:
                    self._color_preview_widgets[category].config(bg=category_colors.get(category, "#FFFFFF"))