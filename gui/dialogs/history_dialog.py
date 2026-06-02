# gui/dialogs/history_dialog.py
"""
Диалог истории операций для RimWorld Translator Grabber.

Показывает все выполненные операции с возможностью фильтрации и сохранения.
"""

import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from ttkbootstrap.constants import *


def show_history(parent, operation_history=None):
    """Показать диалог истории операций

    Args:
        parent: Родительское окно
        operation_history: Список операций (deque)
    """
    if operation_history is None:
        operation_history = []

    if not operation_history:
        messagebox.showinfo(
            tr("history_dialog_title", "📜 История"),
            tr("history_empty", "История операций пуста"),
        )
        return

    dialog = tk.Toplevel(parent)
    dialog.title(tr("history_dialog_title", "📜 История операций"))
    dialog.geometry("700x500")
    dialog.minsize(500, 350)
    dialog.transient(parent)
    dialog.grab_set()

    # Иконки для заголовка
    if HAS_ICONS:
        dialog_icons = get_dialog_header_icons()

    # Основной контейнер
    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill="both", expand=True)

    # Заголовок и статистика
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(
        header_frame,
        text=tr("history_title", "История операций"),
        font=("Segoe UI", 14, "bold"),
    ).pack(side="left")

    stats_label = ttk.Label(
        header_frame,
        text=tr("history_count", "Всего операций: {}").format(len(operation_history)),
        font=("Segoe UI", 10),
        foreground="gray",
    )
    stats_label.pack(side="right", pady=5)

    # Панель фильтров
    filter_frame = ttk.Frame(main_frame)
    filter_frame.pack(fill="x", pady=(0, 10))

    ttk.Label(filter_frame, text=tr("history_filter", "Фильтр:")).pack(side="left", padx=(0, 5))

    filter_var = tk.StringVar(value="")

    # Поле поиска
    search_entry = ttk.Entry(filter_frame, textvariable=filter_var, width=30, bootstyle="search")
    search_entry.pack(side="left", padx=(0, 10))

    # Кнопки действий
    btn_filter_frame = ttk.Frame(main_frame)
    btn_filter_frame.pack(fill="x", pady=(0, 5))

    def apply_filter():
        """Применить фильтр поиска"""
        search_text = filter_var.get().lower()
        if not search_text:
            _populate_list(operation_history)
            return

        filtered = [
            entry
            for entry in operation_history
            if search_text in entry.get("operation", "").lower()
            or search_text in entry.get("details", "").lower()
        ]
        _populate_list(filtered)
        count_label.config(
            text=tr("history_filtered", "Показано: {} из {}").format(
                len(filtered), len(operation_history)
            )
        )

    def clear_filter():
        """Очистить фильтр"""
        filter_var.set("")
        _populate_list(operation_history)
        count_label.config(
            text=tr("history_count", "Всего операций: {}").format(len(operation_history))
        )

    ttk.Button(
        btn_filter_frame,
        text=tr("history_apply_filter", "🔍 Применить"),
        command=apply_filter,
        bootstyle="info",
        width=15,
    ).pack(side="left", padx=2)

    ttk.Button(
        btn_filter_frame,
        text=tr("history_clear_filter", "❌ Сброс"),
        command=clear_filter,
        bootstyle="secondary",
        width=10,
    ).pack(side="left", padx=2)

    # Счётчик
    count_label = ttk.Label(
        btn_filter_frame,
        text=tr("history_count", "Всего операций: {}").format(len(operation_history)),
        font=("Segoe UI", 9),
    )
    count_label.pack(side="right", pady=5)

    # Список операций
    list_frame = ttk.LabelFrame(
        main_frame, text=tr("history_operations_list", "Список операций"), padding=5
    )
    list_frame.pack(fill="both", expand=True, pady=5)

    # Прокручиваемый контейнер
    from ttkbootstrap.widgets.scrolled import ScrolledFrame

    scrollable = ScrolledFrame(list_frame, autohide=True)
    scrollable.pack(fill="both", expand=True)

    def _populate_list(entries):
        """Заполнить список операциями"""
        # Очищаем старые элементы
        for widget in scrollable.winfo_children():
            widget.destroy()

        if not entries:
            ttk.Label(
                scrollable,
                text=tr("history_no_results", "Нет результатов"),
                font=("Segoe UI", 10),
                foreground="gray",
            ).pack(pady=20)
            return

        # Показываем последние операции сверху
        for entry in reversed(entries):
            item_frame = ttk.Frame(scrollable)
            item_frame.pack(fill="x", pady=2, padx=5)

            # Время
            time_label = ttk.Label(
                item_frame,
                text=entry.get("timestamp", "—"),
                font=("Consolas", 9),
                foreground="gray",
                width=20,
            )
            time_label.pack(side="left", padx=(0, 10))

            # Операция
            op_label = ttk.Label(
                item_frame,
                text=entry.get("operation", "—"),
                font=("Segoe UI", 9, "bold"),
            )
            op_label.pack(side="left", padx=(0, 10))

            # Детали
            if entry.get("details"):
                details_label = ttk.Label(
                    item_frame,
                    text=f"— {entry['details']}",
                    font=("Segoe UI", 9),
                    foreground="dimgray",
                )
                details_label.pack(side="left")

    # Заполняем список
    _populate_list(operation_history)

    # Кнопка сохранения
    save_frame = ttk.Frame(main_frame)
    save_frame.pack(fill="x", pady=(5, 0))

    def save_history():
        """Сохранить историю в файл"""
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title=tr("history_save_title", "Сохранить историю"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"history_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(tr("history_file_header", "История операций") + "\n")
                    f.write("=" * 60 + "\n\n")

                    for entry in operation_history:
                        f.write(f"[{entry.get('timestamp', '—')}] ")
                        f.write(f"{entry.get('operation', '—')}")
                        if entry.get("details"):
                            f.write(f" - {entry['details']}")
                        f.write("\n")

                messagebox.showinfo(
                    tr("history_save_success", "История сохранена"),
                    tr("history_save_msg", "История сохранена в:\n{}").format(file_path),
                )
            except Exception as e:
                messagebox.showerror(
                    tr("history_save_error", "Ошибка сохранения"),
                    tr("history_save_error_msg", "Не удалось сохранить историю:\n{}").format(
                        str(e)
                    ),
                )

    ttk.Button(
        save_frame,
        text=tr("history_save_btn", "💾 Сохранить в файл"),
        command=save_history,
        bootstyle="success",
    ).pack(side="left", padx=2)

    # Кнопка закрытия
    ttk.Button(
        save_frame,
        text=tr("history_close", "✖️ Закрыть"),
        command=dialog.destroy,
        bootstyle="secondary",
    ).pack(side="right", padx=2)

    # Привязка Escape
    dialog.bind("<Escape>", lambda e: dialog.destroy())

    # Привязка поиска по Enter
    search_entry.bind("<Return>", lambda e: apply_filter())
