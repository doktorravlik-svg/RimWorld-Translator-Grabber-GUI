"""
Settings Color Manager - управление цветами в настройках GUI.

Отвечает за:
- Настройку цветов UI (текст, фон, акцент)
- Настройку цветов логов (фон, текст)
- Настройку цветов тегов логов
- Настройку темы
- Диалоги выбора цвета
- Сброс цветов к значениям по умолчанию
"""

import tkinter as tk
from tkinter import colorchooser
from typing import Any, Callable, Dict, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from gui.components.advanced_widgets import CollapsingFrame
from gui.gui_i18n import tr


class SettingsColorManager:
    DEFAULT_UI_COLORS = {
        "text_color": "#000000",
        "bg_color": "#FFFFFF",
        "accent_color": "#0078D4",
    }

    DEFAULT_LOG_COLORS = {
        "log_bg_color": "#1E1E1E",
        "log_text_color": "#D4D4D4",
    }

    DEFAULT_TAG_COLORS = {
        "log_tag_info": "#2196F3",
        "log_tag_success": "#4CAF50",
        "log_tag_warning": "#FF9800",
        "log_tag_error": "#F44336",
    }

    THEMES = [
        "lumen", "minty", "solar", "superhero", "dark", "cyborg",
        "cerulean", "cosmo", "flatly", "journal", "litera",
        "pulse", "morph", "united", "yeti",
    ]

    DEFAULT_LOG_COLORS = {
        "log_bg_color": "#1E1E1E",
        "log_text_color": "#D4D4D4",
    }

    DEFAULT_TAG_COLORS = {
        "log_tag_info": "#2196F3",
        "log_tag_success": "#4CAF50",
        "log_tag_warning": "#FF9800",
        "log_tag_error": "#F44336",
    }

    def __init__(
        self,
        parent: ttk.Frame,
        config: dict,
        is_dark_theme: Callable[[], bool]
    ):
        """
        Args:
            parent: Родительский виджет
            config: Словарь конфигурации
            is_dark_theme: Функция проверки тёмной темы
        """
        self.parent = parent
        self.config = config
        self.is_dark_theme = is_dark_theme

        # Ссылки на виджеты
        self._color_widgets: Dict[str, Any] = {}
        self._preview_widgets: Dict[str, Any] = {}

    def create_ui_colors_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию цветов интерфейса.

        Args:
            container: Контейнер для секции
        """
        section = CollapsingFrame(container, text="🎨 Цвета интерфейса", collapsed=False)
        section.pack(fill="x", padx=5, pady=5)
        frame = section.content_frame

        colors = [
            ("text_color", "Цвет текста"),
            ("bg_color", "Цвет фона"),
            ("accent_color", "Цвет акцента"),
        ]

        for key, label in colors:
            self._create_color_row(frame, key, label)

        self._load_all_colors_info()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="Загрузить",
            command=self._load_all_colors_info,
            bootstyle="info-outline"
        ).pack(side="left", padx=2, expand=True, fill="x")

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset_colors,
            bootstyle="warning-outline"
        ).pack(side="left", padx=2, expand=True, fill="x")

    def create_log_colors_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию цветов логов.

        Args:
            container: Контейнер для секции
        """
        section = CollapsingFrame(container, text="📝 Цвета логов", collapsed=False)
        section.pack(fill="x", padx=5, pady=5)
        frame = section.content_frame

        colors = [
            ("log_bg_color", "Фон логов"),
            ("log_text_color", "Текст логов"),
        ]

        for key, label in colors:
            self._create_log_color_row(frame, key, label)

        self._load_all_log_colors_info()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="Загрузить",
            command=self._load_all_log_colors_info,
            bootstyle="info-outline"
        ).pack(side="left", padx=2, expand=True, fill="x")

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset_log_colors,
            bootstyle="warning-outline"
        ).pack(side="left", padx=2, expand=True, fill="x")

    def create_tag_colors_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию цветов тегов логов.

        Args:
            container: Контейнер для секции
        """
        section = CollapsingFrame(container, text="🏷️ Цвета тегов логов", collapsed=True)
        section.pack(fill="x", padx=5, pady=5)
        frame = section.content_frame

        tags = [
            ("log_tag_info", "INFO"),
            ("log_tag_success", "SUCCESS"),
            ("log_tag_warning", "WARNING"),
            ("log_tag_error", "ERROR"),
        ]

        for key, tag_name in tags:
            self._create_log_tag_color_row(frame, key, tag_name)

        self._load_log_tag_colors_info()

        ttk.Button(
            frame,
            text="Сбросить цвета тегов",
            command=self._reset_log_tag_colors,
            bootstyle="warning-outline"
        ).pack(padx=5, pady=5)

    def create_theme_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию настройки темы.

        Args:
            container: Контейнер для секции
        """
        section = ttk.LabelFrame(container, text="Тема")
        section.pack(fill="x", padx=5, pady=5)

        ttk.Label(section, text="Тема:", width=15).pack(side="left", padx=5, pady=5)

        self._theme_var = tk.StringVar(value=self.config.get("theme", "lumen"))
        theme_combo = ttk.Combobox(
            section,
            textvariable=self._theme_var,
            values=self.THEMES,
            width=20,
            state="readonly"
        )
        theme_combo.pack(side="left", padx=5, pady=5)
        
        ttk.Button(
            section,
            text="Применить",
            command=self._apply_theme,
            bootstyle="success-outline"
        ).pack(side="right", padx=5, pady=5)

        self._theme_var.trace_add("write", self._on_theme_change)

    def _apply_theme(self) -> None:
        """Применяет выбранную тему."""
        try:
            import ttkbootstrap as ttk
            from config.config_manager import get_config_manager
            
            theme = self._theme_var.get()
            style = ttk.Style(theme)
            
            self.config["theme"] = theme
            get_config_manager().set("theme", theme, save=False)
            get_config_manager().save()
            
            self._is_dark = theme in ("dark", "cyborg", "superhero", "darkly", "solar")
            
            if self.is_dark_theme:
                self.is_dark_theme.__self__.config["theme"] = theme
            
            if hasattr(self.parent, "parent") and hasattr(self.parent.parent, "event_generate"):
                self.parent.parent.event_generate("<<ThemeChanged>>")
                
        except Exception as e:
            print(f"Ошибка применения темы: {e}")

    def _on_theme_change(self, *args) -> None:
        """Обработчик изменения темы."""
        pass

    def _create_color_row(
        self,
        parent: ttk.Frame,
        key: str,
        label: str
    ) -> None:
        """Создаёт строку настройки цвета UI."""
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        ttk.Label(row, text=label, width=15).pack(side="left", padx=2)

        # Превью цвета (Canvas)
        preview = tk.Canvas(row, width=30, height=20, bd=1, relief="solid")
        preview.pack(side="left", padx=2)
        self._preview_widgets[f"ui_{key}"] = preview

        # Кнопка выбора цвета
        btn = ttk.Button(
            row,
            text="Выбрать",
            command=lambda k=key: self._change_color(k, f"ui_{k}"),
            bootstyle="primary-outline"
        )
        btn.pack(side="left", padx=2)
        self._color_widgets[f"ui_{key}"] = btn

    def _create_log_color_row(
        self,
        parent: ttk.Frame,
        key: str,
        label: str
    ) -> None:
        """Создаёт строку настройки цвета логов."""
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        ttk.Label(row, text=label, width=15).pack(side="left", padx=2)

        # Превью
        preview = tk.Text(row, width=30, height=1, state="disabled")
        preview.pack(side="left", padx=2)
        self._preview_widgets[f"log_{key}"] = preview

        # Кнопка
        btn = ttk.Button(
            row,
            text="Выбрать",
            command=lambda k=key: self._change_log_color(k, f"log_{k}"),
            bootstyle="primary-outline"
        )
        btn.pack(side="left", padx=2)
        self._color_widgets[f"log_{key}"] = btn

    def _create_log_tag_color_row(
        self,
        parent: ttk.Frame,
        key: str,
        tag_name: str
    ) -> None:
        """Создаёт строку настройки цвета тега."""
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        ttk.Label(row, text=tag_name, width=15).pack(side="left", padx=2)

        # Превью (badge)
        preview = tk.Canvas(row, width=80, height=20)
        preview.pack(side="left", padx=2)
        self._preview_widgets[f"tag_{key}"] = preview

        # Кнопка
        btn = ttk.Button(
            row,
            text="Выбрать",
            command=lambda k=key: self._change_log_tag_color(k, f"tag_{k}"),
            bootstyle="primary-outline"
        )
        btn.pack(side="left", padx=2)
        self._color_widgets[f"tag_{key}"] = btn

    def _change_color(self, key: str, widget_key: str) -> None:
        """Диалог выбора цвета UI."""
        current = self.config.get(key, self.DEFAULT_UI_COLORS.get(key, "#000000"))
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config[key] = color[1]
            self._draw_ui_color_preview(widget_key, color[1])

    def _change_log_color(self, key: str, widget_key: str) -> None:
        """Диалог выбора цвета логов."""
        current = self.config.get(key, self.DEFAULT_LOG_COLORS.get(key, "#000000"))
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config[key] = color[1]
            self._draw_log_color_preview(widget_key, color[1])

    def _change_log_tag_color(self, key: str, widget_key: str) -> None:
        """Диалог выбора цвета тега."""
        current = self.config.get(key, self.DEFAULT_TAG_COLORS.get(key, "#000000"))
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config[key] = color[1]
            self._draw_log_tag_preview(widget_key, key, color[1])

    def _load_all_colors_info(self) -> None:
        """Загружает информацию о цветах UI."""
        for key in self.DEFAULT_UI_COLORS:
            widget_key = f"ui_{key}"
            if widget_key in self._preview_widgets:
                color = self.config.get(key, self.DEFAULT_UI_COLORS[key])
                self._draw_ui_color_preview(widget_key, color)

    def _reset_colors(self) -> None:
        """Сбрасывает цвета UI к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno(tr("glossary_reset_colors_confirm", "Сброс цветов"), tr("glossary_reset_colors_confirm", "Сбросить все цвета UI к значениям по умолчанию?")):
            for key, default in self.DEFAULT_UI_COLORS.items():
                self.config[key] = default
                self._draw_ui_color_preview(f"ui_{key}", default)

    def _load_all_log_colors_info(self) -> None:
        """Загружает информацию о цветах логов."""
        for key in self.DEFAULT_LOG_COLORS:
            widget_key = f"log_{key}"
            if widget_key in self._preview_widgets:
                color = self.config.get(key, self.DEFAULT_LOG_COLORS[key])
                self._draw_log_color_preview(widget_key, color)

    def _reset_log_colors(self) -> None:
        """Сбрасывает цвета логов к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno(tr("glossary_reset_log_colors_confirm", "Сброс цветов логов"), tr("glossary_reset_log_colors_confirm", "Сбросить все цвета логов?")):
            for key, default in self.DEFAULT_LOG_COLORS.items():
                self.config[key] = default
                self._draw_log_color_preview(f"log_{key}", default)

    def _load_log_tag_colors_info(self) -> None:
        """Загружает информацию о цветах тегов."""
        for key in self.DEFAULT_TAG_COLORS:
            widget_key = f"tag_{key}"
            if widget_key in self._preview_widgets:
                color = self.config.get(key, self.DEFAULT_TAG_COLORS[key])
                self._draw_log_tag_preview(widget_key, key, color)

    def _reset_log_tag_colors(self) -> None:
        """Сбрасывает цвета тегов к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno(tr("glossary_reset_tag_colors_confirm", "Сброс цветов тегов"), tr("glossary_reset_tag_colors_confirm", "Сбросить все цвета тегов?")):
            for key, default in self.DEFAULT_TAG_COLORS.items():
                self.config[key] = default
                widget_key = f"tag_{key}"
                if widget_key in self._preview_widgets:
                    self._draw_log_tag_preview(widget_key, key, default)

    def _draw_ui_color_preview(self, widget_key: str, color: str) -> None:
        """Рисует превью цвета UI на Canvas."""
        if widget_key not in self._preview_widgets:
            return
        canvas = self._preview_widgets[widget_key]
        canvas.delete("all")
        canvas.create_rectangle(2, 2, 28, 18, fill=color, outline="gray")

    def _draw_log_color_preview(self, widget_key: str, color: str) -> None:
        """Рисует превью цвета логов в Text."""
        if widget_key not in self._preview_widgets:
            return
        text_widget = self._preview_widgets[widget_key]
        text_widget.config(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", "  Пример текста  ")

        # Создаём/обновляем тег
        text_widget.tag_configure("preview_bg", background=color)
        is_dark = self._is_color_dark(color)
        text_widget.tag_configure("preview_fg", foreground="#FFFFFF" if is_dark else "#000000")

        text_widget.tag_add("preview_bg", "1.0", "end")
        text_widget.tag_add("preview_fg", "1.0", "end")
        text_widget.config(state="disabled")

    def _draw_log_tag_preview(self, widget_key: str, key: str, color: str) -> None:
        """Рисует превью цвета тега (badge)."""
        if widget_key not in self._preview_widgets:
            return
        canvas = self._preview_widgets[widget_key]
        canvas.delete("all")

        # Рисуем badge
        canvas.create_rectangle(2, 2, 78, 18, fill=color, outline="", tags="bg")
        is_dark = self._is_color_dark(color)
        text_color = "#FFFFFF" if is_dark else "#000000"

        # Текст тега
        tag_name = key.replace("log_tag_", "").upper()
        canvas.create_text(40, 10, text=tag_name, fill=text_color, font=("Arial", 8, "bold"))

    @staticmethod
    def _is_color_dark(color: str) -> bool:
        """
        Определяет тёмность цвета по формуле люминанса.

        Args:
            color: HEX цвет (#RRGGBB)

        Returns:
            True если цвет тёмный
        """
        color = color.lstrip("#")
        if len(color) != 6:
            return False

        try:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            # Формула люминанса
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except ValueError:
            return False
