# gui/dialogs/debug_log_dialog.py
"""
Диалог просмотра лога отладки для RimWorld Translator Grabber.

Позволяет просматривать, фильтровать, очищать и сохранять лог-файл.
"""

import os
from tkinter import filedialog, messagebox, scrolledtext

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from ttkbootstrap.constants import *

# Абсолютный путь к проекту
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEBUG_LOG_PATH = os.path.join(_PROJECT_ROOT, "debug.log")


class DebugLogDialog:
    """Диалог для просмотра и управления логом отладки"""

    MAX_LINES = 5000

    def __init__(self, parent, debug_logger=None):
        self.parent = parent
        self.debug_logger = debug_logger
        self.auto_refresh_var = ttk.BooleanVar(value=False)

        self._build_dialog()
        self._load_log()

    def _build_dialog(self):
        """Построить диалог"""
        self.dialog = ttk.Toplevel(self.parent)
        self.dialog.title(tr("debug_log_title", "🔧 Лог отладки"))
        self.dialog.geometry("900x600")
        self.dialog.minsize(600, 400)
        self.dialog.transient(self.parent)

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
                    image=icon.image,
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

    def _load_log(self):
        """Загрузить лог из файла"""
        self.log_text.delete("1.0", "end")

        if not os.path.exists(_DEBUG_LOG_PATH):
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
            with open(_DEBUG_LOG_PATH, encoding="utf-8") as f:
                all_lines = f.readlines()

            max_lines = self.lines_var.get()
            lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

            # Статистика
            errors = sum(1 for l in all_lines if "| ERROR" in l)
            warnings = sum(1 for l in all_lines if "| WARNING" in l)
            info = sum(1 for l in all_lines if "| INFO" in l)
            debug = sum(1 for l in all_lines if "| DEBUG" in l)

            for line in lines:
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
                text=f"{tr('debug_log_stats', 'Строк')}: {len(all_lines)} | "
                f"{tr('debug_log_errors', 'Ошибок')}: {errors} | "
                f"{tr('debug_log_warnings', 'Предупреждений')}: {warnings}"
            )

            # Прокрутка вниз
            self.log_text.see("end")

        except Exception as e:
            self.log_text.insert("end", f"Ошибка чтения лога: {e}\n")
            self.stats_label.config(text=tr("debug_log_error", "Ошибка"))

    def _clear_log(self):
        """Очистить лог"""
        result = messagebox.askyesno(
            tr("debug_log_clear_title", "Очистить лог"),
            tr("debug_log_clear_confirm", "Вы уверены, что хотите очистить лог?"),
        )
        if result:
            if self.debug_logger:
                self.debug_logger.clear_log()
            elif os.path.exists(_DEBUG_LOG_PATH):
                with open(_DEBUG_LOG_PATH, "w", encoding="utf-8") as f:
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
                messagebox.showinfo(
                    tr("debug_log_success", "Успех"),
                    tr("debug_log_saved", "Лог сохранён:\n{path}").format(path=file_path),
                )
            except Exception as e:
                messagebox.showerror(
                    tr("debug_log_error_title", "Ошибка"),
                    tr("debug_log_save_error", "Ошибка сохранения:\n{e}").format(e=e),
                )

    def _timestamp(self):
        """Получить текущую метку времени"""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")


def show_debug_log(parent, debug_logger=None):
    """Показать диалог лога отладки"""
    dialog = DebugLogDialog(parent, debug_logger)
    return dialog
