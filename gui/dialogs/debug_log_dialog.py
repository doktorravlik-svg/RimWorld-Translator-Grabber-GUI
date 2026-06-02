# gui/dialogs/debug_log_dialog.py
"""
Диалог просмотра лога отладки для RimWorld Translator Grabber.

Позволяет просматривать, фильтровать, очищать и сохранять лог-файл.
"""

import os
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import filedialog, scrolledtext

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from config.debug_config import DebugConfig
from gui.dialogs.messagebox_helpers import show_info, show_error, ask_confirm
from gui.gui_i18n import tr
from gui.core.debounce_mixin import DebounceMixin
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from utils.path_utils import get_project_root


def get_debug_log_path():
    """Возвращает путь к файлу отладки из конфигурации."""
    return DebugConfig().log_file


class DebugLogDialog(DebounceMixin):
    """Диалог для просмотра и управления логом отладки"""

    MAX_LINES = 5000

    def __init__(self, parent, debug_logger=None):
        super().__init__()
        self.parent = parent
        self.debug_logger = debug_logger
        self.auto_refresh_var = ttk.BooleanVar(value=False)
        self._filter_text = ""

        self._build_dialog()
        self._load_log()

    def _build_dialog(self):
        """Построить диалог"""
        self.dialog = ttk.Toplevel(self.parent)
        self.dialog.title(tr("debug_log_title", "🔧 Лог отладки"))
        self.dialog.geometry("900x600")
        self.dialog.minsize(600, 400)
        self.dialog.transient(self.parent)

        # Инициализируем debounce для поля фильтра
        self._init_debounce('filter')

        # Заголовок с иконкой
        header_frame = ttk.Frame(self.dialog)
        header_frame.pack(fill="x", padx=5, pady=(5, 0))

        if HAS_ICONS:
            dialog_icons = get_dialog_header_icons()
            icon = dialog_icons.get("debug_log")
            if icon:
                title_label = ttk.Label(
                    header_frame,
                    text=tr("debug_log_title", "🔧 Лог отладки"),
                    image=icon,
                    compound="left",
                    font=("Segoe UI", 14, "bold"),
                )
            else:
                title_label = ttk.Label(
                    header_frame,
                    text=tr("debug_log_title", "🔧 Лог отладки"),
                    font=("Segoe UI", 14, "bold"),
                )
        else:
            title_label = ttk.Label(
                header_frame,
                text=tr("debug_log_title", "🔧 Лог отладки"),
                font=("Segoe UI", 14, "bold"),
            )
        title_label.pack(side="left", padx=5)

        # Панель инструментов
        toolbar = ttk.Frame(self.dialog)
        toolbar.pack(fill="x", padx=5, pady=5)

        ttk.Button(
            toolbar, text=tr("debug_log_refresh", "🔄 Обновить"), command=self._load_log
        ).pack(side="left", padx=2)
        ttk.Button(toolbar, text=tr("debug_log_clear", "🗑️ Очистить"), command=self._clear_log).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text=tr("debug_log_save", "💾 Сохранить"), command=self._save_log).pack(
            side="left", padx=2
        )

        ttk.Checkbutton(
            toolbar,
            text=tr("debug_log_auto_refresh", "🔄 Авто-обновление"),
            variable=self.auto_refresh_var,
        ).pack(side="left", padx=10)

        # Поле фильтра с debounce
        ttk.Label(toolbar, text=tr("debug_log_filter", "Фильтр:")).pack(side="left", padx=5)
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(toolbar, textvariable=self.filter_var, width=20)
        filter_entry.pack(side="left", padx=2)
        self.filter_var.trace_add('write', self._on_filter_change)

        ttk.Label(toolbar, text=tr("debug_log_lines", "Строк:")).pack(side="left", padx=5)
        self.lines_var = ttk.IntVar(value=500)
        lines_spin = ttk.Spinbox(
            toolbar, from_=100, to=5000, increment=100, textvariable=self.lines_var, width=8
        )
        lines_spin.pack(side="left", padx=2)

        ttk.Button(
            toolbar, text=tr("debug_log_close", "✖️ Закрыть"), command=self.dialog.destroy
        ).pack(side="right", padx=2)

        # Статистика
        self.stats_label = ttk.Label(toolbar, text="", foreground="gray", font=("Segoe UI", 8))
        self.stats_label.pack(side="right", padx=10)

        # Текстовое поле с логом
        self.log_text = scrolledtext.ScrolledText(self.dialog, wrap="word", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Теги для подсветки
        self.log_text.tag_config("ERROR", foreground="#ef5350")
        self.log_text.tag_config("WARNING", foreground="#ffb74d")
        self.log_text.tag_config("INFO", foreground="#4fc3f7")
        self.log_text.tag_config("DEBUG", foreground="#66bb6a")

        # Привязка Escape для закрытия
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

    def _on_filter_change(self, *args):
        """Обработчик изменения фильтра с debounce"""
        self.debounce('filter', 300, self._apply_filter)

    def _apply_filter(self):
        """Применяет фильтр к логу"""
        self._filter_text = self.filter_var.get().lower()
        self._load_log()

    def _load_log(self):
        """Загрузить лог из файла (эффективное чтение последних строк)"""
        log_path = get_debug_log_path()
        self.log_text.delete("1.0", "end")

        if not os.path.exists(log_path):
            self.log_text.insert(
                "end",
                tr(
                    "debug_log_not_found",
                    "Лог-файл не найден.\nВключите Debug-режим в меню Справка → Debug-режим.\n",
                ),
            )
            self.stats_label.config(text=tr("debug_log_no_file", "Файл отсутствует"))
            return

        try:
            max_lines = self.lines_var.get()

            # Читаем только последние N строк
            last_lines = deque(maxlen=max_lines)

            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    last_lines.append(line)

            # Подсчёт статистики
            error_count = 0
            warning_count = 0
            info_count = 0
            debug_count = 0
            total_lines = 0

            with open(log_path, encoding="utf-8") as f:
                for line in f:
                    total_lines += 1
                    if "| ERROR" in line:
                        error_count += 1
                    elif "| WARNING" in line:
                        warning_count += 1
                    elif "| INFO" in line:
                        info_count += 1
                    elif "| DEBUG" in line:
                        debug_count += 1

            # Выводим только подходящие под фильтр строки
            for line in last_lines:
                if self._filter_text and self._filter_text not in line.lower():
                    continue

                # Определяем уровень для подсветки
                tag = "DEBUG"
                if "| ERROR" in line:
                    tag = "ERROR"
                elif "| WARNING" in line:
                    tag = "WARNING"
                elif "| INFO" in line:
                    tag = "INFO"

                self.log_text.insert("end", line, tag)

            self.stats_label.config(
                text=f"{tr('debug_log_stats', 'Строк')}: {total_lines} | "
                f"{tr('debug_log_errors', 'Ошибок')}: {error_count} | "
                f"{tr('debug_log_warnings', 'Предупреждений')}: {warning_count}"
            )

            # Прокрутка вниз
            self.log_text.see("end")

        except Exception as e:
            self.log_text.insert("end", f"Ошибка чтения лога: {e}\n")
            self.stats_label.config(text=tr("debug_log_error", "Ошибка"))

    def _clear_log(self):
        """Очистить лог"""
        if not ask_confirm(
            tr("debug_log_clear_confirm", "Вы уверены, что хотите очистить лог?"),
        ):
            return
        log_path = get_debug_log_path()
        if self.debug_logger:
            self.debug_logger.clear_log()
        elif os.path.exists(log_path):
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("Лог очищен\n")
        self._load_log()

    def _save_log(self):
        """Сохранить лог в файл"""
        file_path = filedialog.asksaveasfilename(
            title=tr("debug_log_save_dialog", "Сохранить лог"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
            initialfile=f"debug_log_{self._timestamp()}.txt",
        )
        if file_path:
            try:
                content = self.log_text.get("1.0", "end")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                show_info(self.dialog, tr("debug_log_saved", "Лог сохранён:\n{path}").format(path=file_path))
            except Exception as e:
                show_error(self.dialog, tr("debug_log_save_error", "Ошибка сохранения:\n{e}").format(e=e))

    def _timestamp(self):
        """Получить текущую метку времени"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def show(self):
        """Показать диалог"""
        self.dialog.wait_visibility()
        self.dialog.grab_set()
        return self.dialog


def show_debug_log(parent, debug_logger=None):
    """Показать диалог лога отладки"""
    dialog = DebugLogDialog(parent, debug_logger)
    dialog.show()
    return dialog