# gui/dialogs/shortcuts_dialog.py
"""
Диалог горячих клавиш для RimWorld Translator Grabber.

Показывает все доступные горячие клавиши сгруппированные по категориям.
"""

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttk
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from ttkbootstrap.constants import *
from gui.gui_i18n import tr

# Данные о горячих клавишах
SHORTCUTS_DATA = [
    (
        tr("shortcuts_group_file", "📁 Файл"),
        [
            ("Ctrl+O", tr("shortcuts_open_mods", "Открыть папку модов")),
            ("Ctrl+S", tr("shortcuts_save_settings", "Сохранить настройки")),
            ("Ctrl+L", tr("shortcuts_clear_log", "Очистить лог")),
        ],
    ),
    (
        tr("shortcuts_group_tools", "🔍 Инструменты"),
        [
            ("Ctrl+Shift+V", tr("shortcuts_verify", "Запустить верификацию")),
            ("Ctrl+Shift+F", tr("shortcuts_full_check", "Полная проверка")),
            ("Ctrl+Shift+I", tr("shortcuts_integrity", "Проверка целостности")),
            ("Ctrl+Shift+G", tr("shortcuts_load_game", "Загрузить данные игры")),
        ],
    ),
    (
        tr("shortcuts_group_tabs", "📑 Вкладки"),
        [
            ("Ctrl+Tab", tr("shortcuts_next_tab", "Следующая вкладка")),
            ("Ctrl+Shift+Tab", tr("shortcuts_prev_tab", "Предыдущая вкладка")),
            ("Ctrl+H", tr("shortcuts_show_shortcuts", "Показать горячие клавиши")),
        ],
    ),
    (
        tr("shortcuts_group_editor", "✏️ Редактор"),
        [
            ("Ctrl+Z", tr("shortcuts_undo", "Отменить")),
            ("Ctrl+Y", tr("shortcuts_redo", "Повторить")),
            ("Ctrl+F", tr("shortcuts_find", "Поиск")),
            ("Ctrl+H", tr("shortcuts_replace", "Заменить")),
            ("Ctrl+S", tr("shortcuts_save_file", "Сохранить файл")),
            ("Ctrl+↓", tr("shortcuts_next_entry", "Следующая запись")),
            ("Ctrl+↑", tr("shortcuts_prev_entry", "Предыдущая запись")),
            ("Ctrl+Enter", tr("shortcuts_save_next", "Сохранить и следующая")),
            ("F2", tr("shortcuts_rename_key", "Переименовать ключ")),
            ("Delete", tr("shortcuts_delete_entry", "Удалить запись")),
        ],
    ),
    (
        tr("shortcuts_group_debug", "🔧 Отладка"),
        [
            ("Ctrl+Shift+D", tr("shortcuts_toggle_debug", "Включить/выключить Debug")),
            ("Ctrl+Shift+L", tr("shortcuts_view_log", "Просмотреть лог")),
        ],
    ),
]


def show_shortcuts(parent):
    """Показать диалог горячих клавиш

    Args:
        parent: Родительское окно
    """
    dialog = tk.Toplevel(parent)
    dialog.title(tr("shortcuts_dialog_title", "⌨️ Горячие клавиши"))
    dialog.geometry("650x550")
    dialog.minsize(500, 400)
    dialog.transient(parent)
    dialog.grab_set()

    # Центрируем
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 325
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 275
    dialog.geometry(f"650x550+{x}+{y}")

    main_frame = ttk.Frame(dialog, padding=15)
    main_frame.pack(fill="both", expand=True)

    # Заголовок
    if HAS_ICONS:
        dialog_icons = get_dialog_header_icons()
        icon = dialog_icons.get("shortcuts")
        if icon:
            title_label = ttk.Label(
                main_frame,
                text=tr("shortcuts_title", "Горячие клавиши"),
                image=icon.image,
                compound="left",
                font=("Segoe UI", 16, "bold"),
            )
        else:
            title_label = ttk.Label(
                main_frame,
                text=tr("shortcuts_title", "Горячие клавиши"),
                font=("Segoe UI", 16, "bold"),
            )
    else:
        title_label = ttk.Label(
            main_frame,
            text=tr("shortcuts_title", "Горячие клавиши"),
            font=("Segoe UI", 16, "bold"),
        )
    title_label.pack(pady=(0, 10))

    # Прокручиваемый контейнер
    from ttkbootstrap.widgets.scrolled import ScrolledFrame

    scrollable = ScrolledFrame(main_frame, autohide=True)
    scrollable.pack(fill="both", expand=True)

    # Группы горячих клавиш
    for group_name, shortcuts in SHORTCUTS_DATA:
        group_frame = ttk.Frame(scrollable)
        group_frame.pack(fill="x", padx=5, pady=5)

        # Заголовок группы
        ttk.Label(
            group_frame,
            text=group_name,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 5))

        for key_combo, description in shortcuts:
            row = ttk.Frame(group_frame)
            row.pack(fill="x", pady=2)

            # Комбинация клавиш — стилизованная метка
            key_label = ttk.Label(
                row,
                text=key_combo,
                font=("Consolas", 9, "bold"),
                background="#e8e8e8",
                foreground="#333",
                padding=(8, 2),
                relief="solid",
                borderwidth=1,
                width=18,
            )
            key_label.pack(side="left", padx=(0, 10))

            # Описание
            ttk.Label(row, text=description, font=("Segoe UI", 9)).pack(side="left")

    # Кнопка закрытия
    ttk.Button(
        main_frame,
        text=tr("shortcuts_close", "✖️ Закрыть"),
        command=dialog.destroy,
        bootstyle="primary",
    ).pack(pady=10)

    # Привязка Escape
    dialog.bind("<Escape>", lambda e: dialog.destroy())
