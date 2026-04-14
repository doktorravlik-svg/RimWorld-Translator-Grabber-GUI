# gui/dialogs/documentation_dialog.py
"""
Диалог документации для RimWorld Translator Grabber.

Содержит подробную документацию по использованию приложения.
"""

import tkinter as tk
from tkinter import ttk

import ttkbootstrap as ttk
from gui.gui_i18n import tr
from gui.styling.icon_manager import HAS_ICONS, get_dialog_header_icons
from ttkbootstrap.constants import *


def show_documentation(parent):
    """Показать окно документации

    Args:
        parent: Родительское окно
    """
    dialog = tk.Toplevel(parent)
    dialog.title(tr("doc_dialog_title", "📖 Документация"))
    dialog.geometry("800x600")
    dialog.minsize(600, 400)
    dialog.transient(parent)
    dialog.grab_set()

    # Центрируем
    dialog.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 400
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 300
    dialog.geometry(f"800x600+{x}+{y}")

    main_frame = ttk.Frame(dialog, padding=10)
    main_frame.pack(fill="both", expand=True)

    # Заголовок
    if HAS_ICONS:
        dialog_icons = get_dialog_header_icons()
        icon = dialog_icons.get("documentation")
        if icon:
            title_label = ttk.Label(
                main_frame,
                text=tr("doc_title", "Документация RimWorld Translator Grabber"),
                image=icon.image,
                compound="left",
                font=("Segoe UI", 14, "bold"),
            )
        else:
            title_label = ttk.Label(
                main_frame,
                text=tr("doc_title", "Документация RimWorld Translator Grabber"),
                font=("Segoe UI", 14, "bold"),
            )
    else:
        title_label = ttk.Label(
            main_frame,
            text=tr("doc_title", "Документация RimWorld Translator Grabber"),
            font=("Segoe UI", 14, "bold"),
        )
    title_label.pack(pady=(0, 10))

    # Notebook с разделами
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill="both", expand=True, pady=5)

    # === Раздел: Быстрый старт ===
    quickstart_frame = ttk.Frame(notebook, padding=15)
    notebook.add(quickstart_frame, text=tr("doc_tab_quickstart", "Быстрый старт"))

    quickstart_text = tr(
        "doc_quickstart_content",
        "1. Укажите папку с модами RimWorld в настройках\n"
        "2. Перейдите на вкладку 'Перевод' и выберите моды\n"
        "3. Установите исходный и целевой языки\n"
        "4. Нажмите 'Запустить перевод'\n"
        "5. Проверьте результат на вкладке 'Верификация'\n"
        "6. При необходимости отредактируйте в 'Редакторе'",
    )
    ttk.Label(
        quickstart_frame,
        text=quickstart_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Перевод модов ===
    translation_frame = ttk.Frame(notebook, padding=15)
    notebook.add(translation_frame, text=tr("doc_tab_translation", "Перевод"))

    translation_text = tr(
        "doc_translation_content",
        "Автоматический перевод:\n"
        "• Выберите моды из списка — галочками отметьте нужные\n"
        "• Установите языки: исходный (обычно English) и целевой (например Russian)\n"
        "• Нажмите 'Запустить перевод' — процесс можно отменить\n\n"
        "Настройки перевода:\n"
        '• "Создать мод-перевод" (рекомендуется) — перевод сохраняется в отдельную папку\n'
        '• "Переводить в исходную папку" — перевод перезаписывает оригинал\n\n'
        "Фильтры тегов:\n"
        "• Вкладка 'Фильтры' позволяет настроить какие XML-теги извлекаются\n"
        "• Белый список — теги для извлечения (li, rule, description...)\n"
        "• Чёрный список — технические теги для пропуска (defName, recipeWorkers...)",
    )
    ttk.Label(
        translation_frame,
        text=translation_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Верификация ===
    verification_frame = ttk.Frame(notebook, padding=15)
    notebook.add(verification_frame, text=tr("doc_tab_verification", "Верификация"))

    verification_text = tr(
        "doc_verification_content",
        "Проверка модов включает:\n"
        "• Проверка переводов — поиск пустых и непереведённых записей\n"
        "• Проверка зависимостей — обнаружение отсутствующих родительских модов\n"
        "• Обнаружение конфликтов — поиск несовместимых модов\n\n"
        "Экспорт отчёта:\n"
        "• TXT — простой текстовый файл\n"
        "• JSON — структурированные данные\n"
        "• HTML — форматированный отчёт для браузера",
    )
    ttk.Label(
        verification_frame,
        text=verification_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Зависимости ===
    deps_frame = ttk.Frame(notebook, padding=15)
    notebook.add(deps_frame, text=tr("doc_tab_dependencies", "Зависимости"))

    deps_text = tr(
        "doc_dependencies_content",
        "Вкладка 'Зависимости' позволяет анализировать дерево зависимостей переводов модов.\n\n"
        "Возможности:\n"
        "• Автоматический поиск папки Mods\n"
        "• Анализ статусов всех переводов\n"
        "• Визуальное дерево зависимостей\n"
        "• Экспорт отчёта в TXT, JSON, HTML\n\n"
        "Цветовая маркировка статусов (легенда):\n"
        "🟢 Актуален — перевод соответствует последней версии родителя\n"
        "🟡 Устарел — доступна новая версия родительского мода\n"
        "🟠 Версия не совпадает — версия перевода не совпадает с родителем\n"
        "🔴 Отсутствует — перевод не найден или требует создания\n"
        "🔴 Родитель не найден — родительский мод отсутствует в папке Mods\n"
        "🟣 Пользовательский — пользовательский/независимый перевод\n"
        "⚪ Неизвестно — статус не определён\n\n"
        "Легенда автоматически обновляется при смене темы оформления.",
    )
    ttk.Label(
        deps_frame,
        text=deps_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Редактор ===
    editor_frame = ttk.Frame(notebook, padding=15)
    notebook.add(editor_frame, text=tr("doc_tab_editor", "Редактор"))

    editor_text = tr(
        "doc_editor_content",
        "Редактор переводов позволяет:\n"
        "• Открывать XML файлы переводов для ручного редактирования\n"
        "• Использовать Undo/Redo (Ctrl+Z / Ctrl+Y)\n"
        "• Поиск и замена (Ctrl+F / Ctrl+H)\n"
        "• Массовое редактирование нескольких записей\n"
        "• Проверка орфографии для RU/EN/DE/FR/ES\n"
        "• Diff-сравнение с оригиналом (посимвольная подсветка)\n"
        "• Глоссарий терминов RimWorld\n"
        "• Автосохранение каждые 5 секунд\n"
        "• Drag & Drop файлов для открытия\n\n"
        "Горячие клавиши редактора:\n"
        "• Ctrl+S — Сохранить\n"
        "• Ctrl+↓/↑ — Следующая/предыдущая запись\n"
        "• Ctrl+Enter — Сохранить и перейти к следующей\n"
        "• F2 — Переименовать ключ\n"
        "• Delete — Удалить запись",
    )
    ttk.Label(
        editor_frame,
        text=editor_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Настройки ===
    settings_frame = ttk.Frame(notebook, padding=15)
    notebook.add(settings_frame, text=tr("doc_tab_settings", "Настройки"))

    settings_text = tr(
        "doc_settings_content",
        "Вкладка настроек содержит:\n"
        "• Пути: папка модов, папка вывода, путь к игре\n"
        "• Внешний вид: шрифты, цвета, темы оформления\n"
        "• Перевод: режим (отдельный мод / в исходную папку)\n"
        "• Верификация: язык проверки\n\n"
        "Пресеты настроек:\n"
        "• Сохраните текущие настройки в файл\n"
        "• Загрузите настройки из файла пресета\n"
        "• Сбросьте все настройки к значениям по умолчанию\n\n"
        "Темы оформления (8 тем):\n"
        "• Светлая, Тёмная, Океан, Лес (стандартные)\n"
        "• Солнечная, Пар, Киборг, Супергерой (дополнительные)\n"
        "• Иконки адаптируют цвета к каждой теме",
    )
    ttk.Label(
        settings_frame,
        text=settings_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Переводчики (НОВОЕ) ===
    engines_frame = ttk.Frame(notebook, padding=15)
    notebook.add(engines_frame, text=tr("doc_tab_engines", "Переводчики"))

    engines_text = tr(
        "doc_engines_content",
        "Доступные движки перевода:\n"
        "• Google Translate — быстрый и стабильный\n"
        "• MyMemory — большой словарный запас\n"
        "• DeepL (веб) — высокое качество перевода\n"
        "• Bing Translator — альтернативный вариант\n"
        "• DeepLX (локальный сервер) — для обхода блокировок (требует DeepLX сервер)\n"
        "• Translators (20+ движков) — библиотека с множеством сервисов\n"
        "• LibreTranslate — свой сервер (open source)\n"
        "• Argos Translate — оффлайн переводчик\n\n"
        "Умная маршрутизация:\n"
        "• Автоматически приоритезирует движки по успешности\n"
        "• При сбое одного — переключается на следующий\n"
        "• Настраивается во вкладке 'Настройки → Переводчики'\n\n"
        "Дополнительные функции:\n"
        "• Умное разбиение длинного текста на предложения\n"
        "• Rate limiting — защита от бана по IP\n"
        "• Глоссарий — пользовательский словарь терминов",
    )
    ttk.Label(
        engines_frame,
        text=engines_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # === Раздел: Горячие клавиши ===
    hotkeys_frame = ttk.Frame(notebook, padding=15)
    notebook.add(hotkeys_frame, text=tr("doc_tab_hotkeys", "Горячие клавиши"))

    hotkeys_text = tr(
        "doc_hotkeys_content",
        "Глобальные:\n"
        "  Ctrl+O — Открыть папку модов\n"
        "  Ctrl+S — Сохранить настройки\n"
        "  Ctrl+L — Очистить лог\n\n"
        "Инструменты:\n"
        "  Ctrl+Shift+V — Верификация\n"
        "  Ctrl+Shift+F — Полная проверка\n"
        "  Ctrl+Shift+D — Debug режим\n"
        "  Ctrl+Shift+I — Проверка целостности\n"
        "  Ctrl+Shift+G — Загрузить данные игры\n"
        "  Ctrl+Shift+L — Просмотреть лог\n\n"
        "Навигация:\n"
        "  Ctrl+Tab — Следующая вкладка\n"
        "  Ctrl+Shift+Tab — Предыдущая вкладка\n\n"
        "Редактор:\n"
        "  Ctrl+Z — Отменить\n"
        "  Ctrl+Y — Повторить\n"
        "  Ctrl+F — Поиск\n"
        "  Ctrl+H — Заменить\n"
        "  Ctrl+A — Выделить всё\n"
        "  Delete — Удалить запись\n"
        "  Ctrl+↓/↑ — Следующая/предыдущая запись\n"
        "  Ctrl+Enter — Сохранить и перейти к следующей\n"
        "  F2 — Переименовать ключ\n"
        "  Esc — Закрыть диалог\n\n"
        'Полный список: Справка → "Горячие клавиши"',
    )
    ttk.Label(
        hotkeys_frame,
        text=hotkeys_text,
        font=("Segoe UI", 10),
        wraplength=730,
        justify="left",
    ).pack(fill="x", pady=5)

    # Кнопка закрытия
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x", pady=10)

    ttk.Button(
        btn_frame,
        text=tr("doc_close", "✖️ Закрыть"),
        command=dialog.destroy,
        bootstyle="primary",
    ).pack(side="right")

    # Привязка Escape
    dialog.bind("<Escape>", lambda e: dialog.destroy())
