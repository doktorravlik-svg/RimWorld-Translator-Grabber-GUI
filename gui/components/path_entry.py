# gui/components/path_entry.py
"""
Переиспользуемый компонент: Поле ввода пути с кнопкой "Обзор".

Устраняет дублирование паттерна Entry + Button (Обзор),
который повторяется 6+ раз по всему проекту.

Пример использования:
    path_entry = PathEntryWithBrowse(
        parent,
        label_text="Папка модов:",
        button_text=tr("path_entry_browse", "📂 Обзор..."),
        width=50,
        on_change_callback=my_callback
    )
    path_entry.pack(fill="x", padx=5, pady=2)

    # Получение/установка значения
    value = path_entry.get()
    path_entry.set("C:/Mods")
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from gui.gui_i18n import tr


class PathEntryWithBrowse(ttk.Frame):
    """
    Поле ввода пути с кнопкой "Обзор".

    Args:
        master: Родительский виджет
        label_text: Текст метки
        button_text: Текст кнопки (по умолчанию "📂 Обзор...")
        width: Ширина поля ввода
        initial_value: Начальное значение
        on_change_callback: Callback при изменении (опционально)
        dialog_title: Заголовок диалога выбора папки
        **kwargs: Дополнительные аргументы для ttk.Frame
    """

    def __init__(
        self,
        master,
        label_text: str = "",
        button_text: str = "📂 Обзор...",
        width: int = 50,
        initial_value: str = "",
        on_change_callback: Callable[[str], None] | None = None,
        dialog_title: str = "Выберите папку",
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.width = width
        self.on_change_callback = on_change_callback
        self.dialog_title = dialog_title

        # Создаём метку
        if label_text:
            self.label = ttk.Label(self, text=label_text)
            self.label.pack(anchor="w", pady=(0, 2))

        # Создаём фрейм для Entry + Button
        entry_frame = ttk.Frame(self)
        entry_frame.pack(fill="x")

        # Поле ввода
        self.entry_var = tk.StringVar(value=initial_value)
        self.entry = ttk.Entry(
            entry_frame,
            textvariable=self.entry_var,
            width=width,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Привязка события изменения
        self.entry_var.trace("w", lambda *args: self._on_change())
        self.entry.bind("<FocusOut>", lambda e: self.validate_path())

        # Кнопка "Обзор"
        self.browse_button = ttk.Button(
            entry_frame,
            text=button_text,
            command=self._browse,
            bootstyle="info-outline",
            width=12,
        )
        self.browse_button.pack(side="right")

        # Метка статуса валидации
        self.validation_label = ttk.Label(self, text="", font=("Segoe UI", 8))
        self.validation_label.pack(anchor="w", pady=(2, 0))

    def _on_change(self) -> None:
        """Вызывается при изменении значения"""
        if self.on_change_callback:
            try:
                self.on_change_callback(self.entry_var.get())
            except Exception:
                pass

    def _browse(self) -> None:
        """Открывает диалог выбора папки"""
        folder = filedialog.askdirectory(
            title=self.dialog_title, initialdir=self.entry_var.get() or "."
        )
        if folder:
            self.entry_var.set(folder)
            self._on_change()
            self.validate_path()

    def validate_path(self) -> bool:
        """Проверить существование пути и обновить визуальную индикацию"""
        path = self.entry_var.get().strip()

        if not path:
            self.validation_label.config(text="", foreground="")
            self.entry.configure(bootstyle="")
            return False

        import os

        if os.path.exists(path):
            self.validation_label.config(text=tr("path_validation_success", " Путь существует"), foreground="#22c55e")
            self.entry.configure(bootstyle="success")
            return True
        else:
            self.validation_label.config(text=tr("path_validation_not_found", "⚠️ Путь не найден"), foreground="#f59e0b")
            self.entry.configure(bootstyle="warning")
            return False

    def get(self) -> str:
        """Получить значение пути"""
        return self.entry_var.get()

    def set(self, value: str) -> None:
        """Установить значение пути"""
        self.entry_var.set(value)

    def clear(self) -> None:
        """Очистить значение"""
        self.entry_var.set("")
