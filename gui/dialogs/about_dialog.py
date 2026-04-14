# gui/dialogs/about_dialog.py
"""
Диалог "О программе" для RimWorld Translator Grabber.

Содержит информацию о версии, технологиях, лицензии и команде.
"""

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from ttkbootstrap.constants import *


def show_about(parent):
    """Показать диалог "О программе"

    Args:
        parent: Родительское окно
    """
    dialog = tk.Toplevel(parent)
    dialog.title(tr("about_dialog_title", "О программе"))
    dialog.geometry("600x520")
    dialog.minsize(500, 450)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    # Центрируем
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 300
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 260
    dialog.geometry(f"600x520+{x}+{y}")

    # Фрейм с отступами
    main_frame = ttk.Frame(dialog, padding=20)
    main_frame.pack(fill="both", expand=True)

    # Логотип / Заголовок
    header_frame = ttk.Frame(main_frame)
    header_frame.pack(fill="x", pady=(0, 15))

    if HAS_ICONS:
        dialog_icons = get_dialog_header_icons()
        icon = dialog_icons.get("about")
        if icon:
            title_label = ttk.Label(
                header_frame,
                text=tr("app_title", "🌐 RimWorld Translator Grabber"),
                image=icon.image,
                compound="left",
                font=("Segoe UI", 18, "bold"),
            )
        else:
            title_label = ttk.Label(
                header_frame,
                text=tr("app_title", "🌐 RimWorld Translator Grabber"),
                font=("Segoe UI", 18, "bold"),
            )
    else:
        title_label = ttk.Label(
            header_frame,
            text=tr("app_title", "🌐 RimWorld Translator Grabber"),
            font=("Segoe UI", 18, "bold"),
        )
    title_label.pack(side="left")

    version_label = ttk.Label(
        header_frame,
        text="v2.1.0",
        font=("Segoe UI", 10),
        foreground="gray",
    )
    version_label.pack(side="right", pady=5)

    # Разделитель
    ttk.Separator(main_frame).pack(fill="x", pady=10)

    # Описание
    desc_text = tr(
        "about_description",
        "Профессиональный инструмент для перевода и верификации модов RimWorld.\n"
        "Автоматический перевод через Google Translate, проверка зависимостей,\n"
        "поиск дубликатов и полноценный редактор переводов.",
    )
    ttk.Label(
        main_frame, text=desc_text, font=("Segoe UI", 10), wraplength=550, justify="left"
    ).pack(fill="x", pady=10)

    # Notebook с вкладками
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill="both", expand=True, pady=10)

    # === Вкладка "О приложении" ===
    about_frame = ttk.Frame(notebook, padding=15)
    notebook.add(about_frame, text=tr("about_tab_info", "О приложении"))

    info_items = [
        (tr("about_version", "Версия:"), "2.1.0"),
        (tr("about_python", "Python:"), "3.14.3"),
        (tr("about_gui_framework", "GUI фреймворк:"), "ttkbootstrap 1.20.2"),
        (tr("about_translation_engine", "Движок перевода:"), "deep-translator (Google Translate)"),
        (tr("about_spellcheck", "Проверка орфографии:"), "pyspellchecker 0.9.0"),
        (
            tr("about_i18n_languages", "Языки интерфейса:"),
            "Русский, English, Deutsch, Polski, 日本語, Українська",
        ),
        (tr("about_license_type", "Лицензия:"), "MIT"),
        (tr("about_author", "Автор:"), "RimWorld Translator Team"),
    ]

    for label_text, value_text in info_items:
        row = ttk.Frame(about_frame)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label_text, font=("Segoe UI", 9, "bold"), width=25).pack(side="left")
        ttk.Label(row, text=value_text, font=("Segoe UI", 9)).pack(side="left")

    # === Вкладка "Технологии" ===
    tech_frame = ttk.Frame(notebook, padding=15)
    notebook.add(tech_frame, text=tr("about_tab_tech", "Технологии"))

    tech_text = tr(
        "about_tech_description",
        "Проект использует современные технологии для обеспечения качества перевода:\n\n"
        "• ttkbootstrap — современный GUI на базе tkinter с 8 темами оформления\n"
        "• ttkbootstrap-icons — векторные иконки Bootstrap Icons с адаптивными цветами\n"
        "• deep-translator — многоязычный перевод через Google Translate API\n"
        "• pyspellchecker — проверка орфографии для RU, EN, DE, FR, ES\n"
        "• PIL (Pillow) — обработка изображений для рендеринга иконок\n"
        "• SQLite — база данных переводов с глоссарием и историей\n"
        "• tkinterdnd2 — Drag & Drop файлов в редакторе переводов\n\n"
        "Архитектура проекта:\n"
        "• Модульная структура с разделением на GUI, бизнес-логику и данные\n"
        "• Система i18n с 700+ ключами на 4 языках\n"
        "• SignalBus для асинхронного взаимодействия компонентов\n"
        "• Система верификации с проверкой зависимостей и конфликтов",
    )
    tech_label = ttk.Label(
        tech_frame, text=tech_text, font=("Segoe UI", 9), wraplength=530, justify="left"
    )
    tech_label.pack(fill="both", expand=True)

    # === Вкладка "Возможности" ===
    features_frame = ttk.Frame(notebook, padding=15)
    notebook.add(features_frame, text=tr("about_tab_features", "Возможности"))

    features = [
        tr("about_feature_1", "🌐 Автоматический перевод модов через Google Translate"),
        tr("about_feature_2", "✅ Верификация модов — проверка зависимостей и конфликтов"),
        tr("about_feature_3", "🔄 Поиск и слияние дубликатов переводов"),
        tr("about_feature_4", "✏️ Полноценный редактор с Undo/Redo, поиском и заменой"),
        tr("about_feature_5", "🔤 Проверка орфографии для 5 языков"),
        tr("about_feature_6", "📖 Глоссарий терминов RimWorld (60+ терминов)"),
        tr("about_feature_7", "📊 Diff-сравнение с оригиналом (посимвольная подсветка)"),
        tr("about_feature_8", "📦 Управление модами — включение/отключение"),
        tr("about_feature_9", "📝 Фильтры тегов — настройка извлекаемых тегов XML"),
        tr("about_feature_10", "🔗 Анализ дерева зависимостей переводов"),
        tr("about_feature_11", "🎨 8 тем оформления с адаптивными иконками"),
        tr("about_feature_12", "🌍 6 языков интерфейса (RU, EN, DE, PL, JA, UA)"),
        tr("about_feature_13", "💾 Автосохранение и резервные копии"),
        tr("about_feature_14", "🔧 Debug-режим с логированием"),
    ]

    from ttkbootstrap.widgets.scrolled import ScrolledFrame

    scrollable = ScrolledFrame(features_frame, autohide=True)
    scrollable.pack(fill="both", expand=True)

    for feature in features:
        ttk.Label(scrollable, text=feature, font=("Segoe UI", 9), wraplength=520).pack(
            anchor="w", pady=2
        )

    # === Кнопка закрытия ===
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x", pady=10)

    ttk.Button(
        btn_frame,
        text=tr("about_close", "✖️ Закрыть"),
        command=dialog.destroy,
        bootstyle="primary",
    ).pack(side="right")

    # Привязка Escape
    dialog.bind("<Escape>", lambda e: dialog.destroy())
