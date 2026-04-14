"""
Settings Font Manager - управление шрифтами в настройках GUI.

Отвечает за:
- Настройку шрифтов (основной, логов, дерева)
- Применение шрифта ко всем элементам
- Сброс шрифтов к значениям по умолчанию
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Any, Callable, Dict, Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import FontDialog


class SettingsFontManager:
    """Менеджер управления шрифтами для вкладки настроек."""

    # Шрифты по умолчанию
    DEFAULT_FONTS = {
        "main_font": ("Segoe UI", 10),
        "log_font": ("Consolas", 9),
        "tree_font": ("Segoe UI", 9),
    }

    def __init__(
        self,
        parent: ttk.Frame,
        config: dict,
        apply_callback: Optional[Callable] = None
    ):
        """
        Args:
            parent: Родительский виджет
            config: Словарь конфигурации
            apply_callback: Callback для применения шрифта
        """
        self.parent = parent
        self.config = config
        self.apply_callback = apply_callback

        # Ссылки на виджеты
        self._font_entries: Dict[str, Any] = {}
        self._font_previews: Dict[str, Any] = {}

    def create_fonts_section(self, container: ttk.Frame) -> ttk.Frame:
        """
        Создаёт секцию настройки шрифтов.

        Args:
            container: Контейнер для секции

        Returns:
            Созданный фрейм секции
        """
        section = ttk.Labelframe(container, text="Шрифты")
        section.pack(fill="x", padx=5, pady=5)

        fonts = [
            ("main_font", "Основной шрифт", "Пример текста"),
            ("log_font", "Шрифт логов", "0123456789 Log"),
            ("tree_font", "Шрифт дерева", "Дерево элементов"),
        ]

        for key, label, preview_text in fonts:
            self._create_font_row(section, key, label, preview_text)

        # Кнопки действий
        btn_frame = ttk.Frame(section)
        btn_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            btn_frame,
            text="Применить ко всем",
            command=self._apply_main_font_to_all,
            bootstyle="success-outline"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text="Загрузить",
            command=self._load_all_fonts_info,
            bootstyle="info-outline"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame,
            text="Сбросить",
            command=self._reset_all_fonts,
            bootstyle="warning-outline"
        ).pack(side="left", padx=2)

        return section

    def _create_font_row(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        preview_text: str
    ) -> None:
        """
        Создаёт строку настройки шрифта.

        Args:
            parent: Родительский виджет
            key: Ключ шрифта в конфиге
            label: Метка шрифта
            preview_text: Текст для превью
        """
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)

        ttk.Label(row, text=label, width=15).pack(side="left", padx=2)

        # Превью шрифта
        preview = tk.Label(
            row,
            text=preview_text,
            relief="sunken",
            anchor="w",
            padx=5
        )
        preview.pack(side="left", fill="x", expand=True, padx=2)
        self._font_previews[key] = preview

        # Кнопка выбора
        btn = ttk.Button(
            row,
            text="Выбрать",
            command=lambda k=key: self._change_font(k),
            bootstyle="primary-outline"
        )
        btn.pack(side="left", padx=2)
        self._font_entries[key] = btn

    def _change_font(self, key: str) -> None:
        """
        Открывает диалог выбора шрифта.

        Args:
            key: Ключ шрифта
        """
        current = self._get_current_font(key)
        dialog = FontDialog(initialfont=current[0], initialsize=current[1])
        if dialog.result:
            font_family = dialog.result[0]
            font_size = dialog.result[1]

            self.config.setdefault("fonts", {})[key] = {
                "family": font_family,
                "size": font_size,
            }

            self._update_font_preview(key, font_family, font_size)

            if self.apply_callback:
                self.apply_callback(key, font_family, font_size)

    def _apply_main_font_to_all(self) -> None:
        """Применяет основной шрифт ко всем элементам."""
        main_font = self.config.get("fonts", {}).get("main_font", {})
        family = main_font.get("family", "Segoe UI")
        size = main_font.get("size", 10)

        for key in ["log_font", "tree_font"]:
            self.config.setdefault("fonts", {})[key] = {
                "family": family,
                "size": size,
            }
            self._update_font_preview(key, family, size)

    def _load_all_fonts_info(self) -> None:
        """Загружает информацию о всех шрифтах."""
        fonts = self.config.get("fonts", {})
        for key in self.DEFAULT_FONTS:
            font_config = fonts.get(key, {})
            family = font_config.get("family", self.DEFAULT_FONTS[key][0])
            size = font_config.get("size", self.DEFAULT_FONTS[key][1])
            self._update_font_preview(key, family, size)

    def _reset_all_fonts(self) -> None:
        """Сбрасывает все шрифты к значениям по умолчанию."""
        from tkinter import messagebox
        if messagebox.askyesno("Сброс шрифтов", "Сбросить все шрифты к значениям по умолчанию?"):
            for key, (family, size) in self.DEFAULT_FONTS.items():
                self.config.setdefault("fonts", {})[key] = {
                    "family": family,
                    "size": size,
                }
                self._update_font_preview(key, family, size)

            if self.apply_callback:
                self.apply_callback("reset", None, None)

    def _get_current_font(self, key: str) -> tuple:
        """
        Получает текущие настройки шрифта.

        Args:
            key: Ключ шрифта

        Returns:
            Кортеж (family, size)
        """
        font_config = self.config.get("fonts", {}).get(key, {})
        family = font_config.get("family", self.DEFAULT_FONTS[key][0])
        size = font_config.get("size", self.DEFAULT_FONTS[key][1])
        return (family, size)

    def _update_font_preview(self, key: str, family: str, size: int) -> None:
        """
        Обновляет превью шрифта.

        Args:
            key: Ключ шрифта
            family: Семейство шрифта
            size: Размер шрифта
        """
        if key not in self._font_previews:
            return

        try:
            font = tkfont.Font(family=family, size=size)
            self._font_previews[key].config(font=font)
        except Exception:
            pass  # Шрифт может быть недоступен
