"""
Settings Color Manager - управление цветами в настройках GUI.

Отвечает за:
- Настройку цветов UI (текст, фон, акцент)
- Настройку цветов логов (фон, текст)
- Настройку цветов тегов логов
- Диалоги выбора цвета
- Сброс цветов к значениям по умолчанию
"""

import tkinter as tk
from tkinter import colorchooser
from typing import Any, Callable, Dict, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class SettingsColorManager:
    """Менеджер управления цветами для вкладки настроек."""

    # Цвета по умолчанию
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
        section = ttk.Labelframe(container, text="Цвета интерфейса")
        section.pack(fill="x", padx=5, pady=5)

        colors = [
            ("text_color", "Цвет текста"),
            ("bg_color", "Цвет фона"),
            ("accent_color", "Цвет акцента"),
        ]

        for key, label in colors:
            self._create_color_row(section, key, label)

        # Кнопки действий
        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="Загрузить",
            command=self._load_all_colors_info,
            bootstyle="info-outline"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset_colors,
            bootstyle="warning-outline"
        ).pack(side="left", padx=2)

    def create_log_colors_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию цветов логов.

        Args:
            container: Контейнер для секции
        """
        section = ttk.Labelframe(container, text="Цвета логов")
        section.pack(fill="x", padx=5, pady=5)

        colors = [
            ("log_bg_color", "Фон логов"),
            ("log_text_color", "Текст логов"),
        ]

        for key, label in colors:
            self._create_log_color_row(section, key, label)

        # Кнопки действий
        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="Загрузить",
            command=self._load_all_log_colors_info,
            bootstyle="info-outline"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset_log_colors,
            bootstyle="warning-outline"
        ).pack(side="left", padx=2)

    def create_tag_colors_section(self, container: ttk.Frame) -> None:
        """
        Создаёт секцию цветов тегов логов.

        Args:
            container: Контейнер для секции
        """
        section = ttk.Labelframe(container, text="Цвета тегов логов")
        section.pack(fill="x", padx=5, pady=5)

        tags = [
            ("log_tag_info", "INFO"),
            ("log_tag_success", "SUCCESS"),
            ("log_tag_warning", "WARNING"),
            ("log_tag_error", "ERROR"),
        ]

        for key, tag_name in tags:
            self._create_log_tag_color_row(section, key, tag_name)

        # Кнопка сброса
        ttk.Button(
            section,
            text="Сбросить цвета тегов",
            command=self._reset_log_tag_colors,
            bootstyle="warning-outline"
        ).pack(padx=5, pady=5)

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
        current = self.config.get("colors", {}).get(key, "#000000")
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config.setdefault("colors", {})[key] = color[1]
            self._draw_ui_color_preview(widget_key, color[1])

    def _change_log_color(self, key: str, widget_key: str) -> None:
        """Диалог выбора цвета логов."""
        current = self.config.get("log_colors", {}).get(key, "#000000")
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config.setdefault("log_colors", {})[key] = color[1]
            self._draw_log_color_preview(widget_key, color[1])

    def _change_log_tag_color(self, key: str, widget_key: str) -> None:
        """Диалог выбора цвета тега."""
        current = self.config.get("log_tag_colors", {}).get(key, "#000000")
        color = colorchooser.askcolor(color=current, title=f"Выберите {key}")
        if color[1]:
            self.config.setdefault("log_tag_colors", {})[key] = color[1]
            self._draw_log_tag_preview(widget_key, key, color[1])

    def _load_all_colors_info(self) -> None:
        """Загружает информацию о цветах UI."""
        colors = self.config.get("colors", {})
        for key in self.DEFAULT_UI_COLORS:
            widget_key = f"ui_{key}"
            if widget_key in self._preview_widgets:
                color = colors.get(key, self.DEFAULT_UI_COLORS[key])
                self._draw_ui_color_preview(widget_key, color)

    def _reset_colors(self) -> None:
        """Сбрасывает цвета UI к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno("Сброс цветов", "Сбросить все цвета UI к значениям по умолчанию?"):
            for key, default in self.DEFAULT_UI_COLORS.items():
                self.config.setdefault("colors", {})[key] = default
                self._draw_ui_color_preview(f"ui_{key}", default)

    def _load_all_log_colors_info(self) -> None:
        """Загружает информацию о цветах логов."""
        colors = self.config.get("log_colors", {})
        for key in self.DEFAULT_LOG_COLORS:
            widget_key = f"log_{key}"
            if widget_key in self._preview_widgets:
                color = colors.get(key, self.DEFAULT_LOG_COLORS[key])
                self._draw_log_color_preview(widget_key, color)

    def _reset_log_colors(self) -> None:
        """Сбрасывает цвета логов к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno("Сброс цветов логов", "Сбросить все цвета логов?"):
            for key, default in self.DEFAULT_LOG_COLORS.items():
                self.config.setdefault("log_colors", {})[key] = default
                self._draw_log_color_preview(f"log_{key}", default)

    def _load_log_tag_colors_info(self) -> None:
        """Загружает информацию о цветах тегов."""
        colors = self.config.get("log_tag_colors", {})
        for key in self.DEFAULT_TAG_COLORS:
            widget_key = f"tag_{key}"
            if widget_key in self._preview_widgets:
                color = colors.get(key, self.DEFAULT_TAG_COLORS[key])
                self._draw_log_tag_preview(widget_key, key, color)

    def _reset_log_tag_colors(self) -> None:
        """Сбрасывает цвета тегов к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno("Сброс цветов тегов", "Сбросить все цвета тегов?"):
            for key, default in self.DEFAULT_TAG_COLORS.items():
                self.config.setdefault("log_tag_colors", {})[key] = default
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
