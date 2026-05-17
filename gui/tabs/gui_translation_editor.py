"""
gui_translation_editor.py - Редактор переводов
Модуль для редактирования XML файлов переводов.
Позволяет выбирать файл перевода и редактировать его содержимое.
✅ ИСПРАВЛЕНО: Кроссплатформенное открытие папок
✅ ИСПРАВЛЕНО: История изменений (push/pull), корректные hotkeys, self.tr()
✅ СОВМЕСТИМОСТЬ: ttkbootstrap, Python 3.10+ (type hints, f-strings, dict methods)

⚠️ ПРИМЕЧАНИЕ (2026-04): Разделение на модули:
  - WrappingToolbar → gui/tabs/editor/editor_toolbar.py
  - TranslationEditorTab → gui/tabs/editor/editor_file_browser.py
  (удалены из этого файла, импортируются внизу для обратной совместимости)
"""

import csv
import json
import os
import re
import tkinter as tk
import xml.etree.ElementTree as ET
from tkinter import filedialog, messagebox

# Абсолютный путь к директории проекта (родительская от gui/tabs/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "gui_config.json")

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.widgets import ToolTip
except ImportError:
    raise ImportError("Установите ttkbootstrap: pip install ttkbootstrap")

try:
    from gui.components.gui_file_colors import FILE_COLORS, FileColorMarker
    from gui.components.gui_toolbar_icons import get_editor_toolbar_icons

    HAS_ICONS = True
except ImportError:
    HAS_ICONS = False

    def get_editor_toolbar_icons():
        return {}


try:
    from spellchecker import SpellChecker

    HAS_SPELLCHECKER = True
except ImportError:
    HAS_SPELLCHECKER = False

try:
    from translation_db import get_translation_db
except ImportError:

    def get_translation_db():
        return None


# Drag & Drop (опционально)
HAS_DND = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _test_root = TkinterDnD.Tk()
    _test_root.withdraw()
    _test_root.drop_target_register(DND_FILES)
    _test_root.destroy()
    HAS_DND = True
except Exception:
    DND_FILES = "DND_Files"
    pass

AUTO_SAVE_DELAY = 5000  # 5 секунд


class TranslationEditorDialog:
    """Диалог для редактирования файла перевода"""

    def __init__(self, parent, file_path: str = "", title: str = "Редактор перевода"):
        self.parent = parent
        self.file_path = file_path
        self.title = title
        self.modified = False
        self.entries = []
        self.file_map = {}
        self.folder_mode = False
        self.color_marker = FileColorMarker()
        self._auto_save_id = None
        self._sort_column = None
        self._sort_reverse = False
        self._glossary_sync_enabled = True
        self._glossary_min_confidence = 0.9

        from helpers.editor_history import HistoryManager

        self.history_manager = HistoryManager(max_history=50)
        self.tr = self._create_tr_function()
        self._create_dialog()
        self._bind_language_change()

    def _create_tr_function(self):
        # Используем глобальную tr() из i18n — всегда актуальный язык
        try:
            from gui.gui_i18n import i18n

            def tr(key, default=None):
                return i18n.tr(key, default)

            return tr
        except Exception:
            return lambda k, d=None: d or k

    def _bind_language_change(self):
        """Подписаться на событие смены языка"""
        self.dialog.bind("<<LanguageChanged>>", self._on_language_changed)

    def _on_language_changed(self, event=None):
        """Обновить интерфейс при смене языка"""
        self._update_ui_language()

    def _update_ui_language(self):
        """Обновить все тексты в редакторе"""
        try:
            # Обновить заголовок окна
            self.dialog.title(self.title)

            # Обновить header
            if hasattr(self, "header_content"):
                for widget in self.header_content.winfo_children():
                    if isinstance(widget, ttk.Label) and hasattr(widget, "_i18n_key"):
                        widget.config(text=self.tr(widget._i18n_key))

            # Обновить статус
            if hasattr(self, "status_label"):
                self.status_label.config(text=self.tr("editor_status", "Статус"))

            # Обновить кнопки и лейблы
            self._update_widget_texts(self.dialog)

        except Exception as e:
            print(f"Ошибка обновления языка в редакторе: {e}")

    def _update_widget_texts(self, widget):
        """Рекурсивно обновить тексты виджетов"""
        for child in widget.winfo_children():
            if hasattr(child, "_i18n_key"):
                child.config(text=self.tr(child._i18n_key))
            self._update_widget_texts(child)

    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("1200x850")
        self.dialog.minsize(800, 600)
        self._build_dialog_content()
        self.dialog.update_idletasks()
        self.dialog.grab_set()
        if self.file_path:
            self._load_file(self.file_path)
        self._setup_keyboard_shortcuts()
        self._apply_fonts_from_config()

    def _build_dialog_content(self):
        self.dialog.bind("<Escape>", lambda e: self._close_dialog())

        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill="both", expand=True)

        self._build_header(main_container)
        self._build_info_bar(main_container)
        self._build_toolbar(main_container)
        self._build_search_bar(main_container)
        self._build_content_paned(main_container)

        # Bottom bar
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill="x", padx=15, pady=5)
        ttk.Button(
            bottom_frame, text=self.tr("editor_help", "❓ Помощь"), command=self._show_editor_help
        ).pack(side="left", padx=2)
        ttk.Button(
            bottom_frame,
            text=self.tr("editor_close", "✖️ Закрыть"),
            command=self._close_dialog,
            bootstyle="danger",
        ).pack(side="right", padx=2)

        if HAS_DND:
            try:
                self.tree.drop_target_register(DND_FILES)
                self.tree.dnd_bind("<<Drop>>", self._on_drop_file)
                self.dialog.drop_target_register(DND_FILES)
                self.dialog.dnd_bind("<<Drop>>", self._on_drop_file)
            except Exception:
                pass

    def _build_header(self, parent):
        """Создаёт заголовок диалога с индикатором сохранения"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x")
        self.header_content = ttk.Frame(header_frame)
        self.header_content.pack(fill="x", padx=15, pady=8)

        self.header_title = ttk.Label(
            self.header_content,
            text=self.tr("editor_title", "✏️ Редактор перевода"),
            font=("Segoe UI", 16, "bold"),
            foreground="#1976D2",
        )
        self.header_title.pack(side="left")

        self.save_indicator = ttk.Label(
            self.header_content,
            text=self.tr("editor_ready", "💾 Готов"),
            font=("Segoe UI", 9),
            foreground="#757575",
        )
        self.save_indicator.pack(side="right")

    def _build_info_bar(self, parent):
        """Создаёт информационную панель (файл, статус, статистика)"""
        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=15, pady=2)

        self.info_bar = ttk.Frame(parent)
        self.info_bar.pack(fill="x", padx=15, pady=5)
        self.file_label = ttk.Label(
            self.info_bar,
            text=self.tr("editor_file_not_selected", "📁 Файл: Не выбран"),
            font=("Segoe UI", 9),
            foreground="#424242",
        )
        self.file_label.pack(side="left", padx=5)
        self.status_label = ttk.Label(self.info_bar, text=" ", font=("Segoe UI", 9))
        self.status_label.pack(side="left", padx=10)
        self.stats_label = ttk.Label(
            self.info_bar,
            text=self.tr(
                "editor_stats_format", "📊 Всего: {} | ✅ {} | ⚠️ {} | ⬜ {} | Показано: {}"
            ).format(0, 0, 0, 0, 0),
            foreground="#757575",
            font=("Segoe UI", 9),
        )
        self.stats_label.pack(side="right", padx=5)

    def _build_toolbar(self, parent):
        """Создаёт панель инструментов с группами кнопок"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", padx=15, pady=5)
        self.editor_icons = get_editor_toolbar_icons() if HAS_ICONS else {}

        def icon_btn(p, icon, tooltip, cmd, color="primary", key=None):
            """Создать кнопку с тултипом"""
            btn_icon = self.editor_icons.get(key) if key else None
            b = ttk.Button(
                p,
                text=icon,
                image=getattr(btn_icon, "image", None),
                compound="left",
                bootstyle=f"{color}-outline",
                command=cmd,
                padding=8,
            )
            # fill="x" + expand=True — кнопки растягиваются равномерно
            # но не становятся слишком высокими
            b.pack(side="left", fill="x", expand=True, padx=2)
            if tooltip:
                ToolTip(b, text=tooltip)
            return b

        # Группы кнопок — expand=True для равномерного распределения
        file_g = ttk.LabelFrame(toolbar, text=self.tr("editor_toolbar_file", "📁 Файл"))
        file_g.pack(side="left", fill="x", expand=True, padx=1)
        icon_btn(
            file_g, "📂", self.tr("editor_open", "Открыть файл"), self._open_file, "primary", "open"
        )
        icon_btn(
            file_g,
            "📁",
            self.tr("editor_open_folder_toolbar", "Открыть папку"),
            self._open_folder,
            "info",
            "open_folder",
        )
        icon_btn(
            file_g, "💾", self.tr("editor_save", "Сохранить"), self._save_file, "success", "save"
        )
        icon_btn(
            file_g, "🔄", self.tr("editor_refresh", "Обновить"), self._refresh, "info", "refresh"
        )

        edit_g = ttk.LabelFrame(toolbar, text=self.tr("editor_toolbar_edit", "✍️ Ред."))
        edit_g.pack(side="left", fill="x", expand=True, padx=1)
        self.undo_btn = icon_btn(
            edit_g, "↩️", self.tr("editor_undo", "Отменить"), self._undo, "warning", "undo"
        )
        self.undo_btn.config(state="disabled")
        self.redo_btn = icon_btn(
            edit_g, "↪️", self.tr("editor_redo", "Повторить"), self._redo, "warning", "redo"
        )
        self.redo_btn.config(state="disabled")
        icon_btn(
            edit_g,
            "➕",
            self.tr("editor_add", "Добавить запись"),
            self._add_entry,
            "primary",
            "add",
        )
        icon_btn(
            edit_g,
            "🗑️",
            self.tr("editor_delete", "Удалить запись"),
            self._delete_entry,
            "danger",
            "delete",
        )

        mass_g = ttk.LabelFrame(toolbar, text=self.tr("editor_toolbar_ops", "🔧 Опер."))
        mass_g.pack(side="left", fill="x", expand=True, padx=1)
        icon_btn(
            mass_g,
            "✏️",
            self.tr("editor_mass_edit", "Массовое редактирование"),
            self._show_mass_edit_dialog,
            "secondary",
            "mass_edit",
        )
        icon_btn(
            mass_g,
            "🌐",
            self.tr("editor_auto_translate", "Автоперевод пустых"),
            self._translate_empty,
            "info",
            "auto_translate",
        )

        check_g = ttk.LabelFrame(toolbar, text=self.tr("editor_toolbar_check", "✅ Проверка"))
        check_g.pack(side="left", fill="x", expand=True, padx=1)
        icon_btn(
            check_g,
            "📤",
            self.tr("editor_export", "Экспорт в CSV"),
            self._export_selected_to_csv,
            "info",
            "export",
        )
        icon_btn(
            check_g,
            "🔍",
            self.tr("editor_quality", "Проверка качества"),
            self._check_translation_quality,
            "success",
            "check",
        )
        icon_btn(
            check_g,
            "🔤",
            self.tr("editor_spelling", "Проверка орфографии"),
            self._check_spelling,
            "warning",
            "spellcheck",
        )

        tools_g = ttk.LabelFrame(toolbar, text=self.tr("editor_toolbar_tools", "🛠️ Инстр."))
        tools_g.pack(side="left", fill="x", expand=True, padx=1)

        # Загружаем тултипы из файла для расширенных подсказок
        try:
            from gui.help.help_loader import get_tooltip, load_editor_tooltips

            tooltips = load_editor_tooltips()
            diff_tip = get_tooltip(tooltips, "diff")
            glossary_tip = get_tooltip(tooltips, "glossary")
        except Exception:
            diff_tip = None
            glossary_tip = None

        icon_btn(
            tools_g, "🔀", diff_tip or self.tr("editor_diff", "Diff"), self._show_diff_view, "info"
        )
        icon_btn(
            tools_g,
            "📖",
            glossary_tip or self.tr("editor_glossary", "Глоссарий"),
            self._show_glossary,
            "secondary",
        )

        icon_btn(
            tools_g,
            "📜",
            self.tr("editor_history_btn", "История версий"),
            self._show_file_history,
            "primary",
        )
        icon_btn(
            tools_g,
            "💡",
            self.tr("editor_suggestions", "Подсказки"),
            self._show_suggestions,
            "success",
        )

    def _build_search_bar(self, parent):
        """Создаёт панель поиска и фильтрации"""
        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=15, pady=2)

        self.search_frame = ttk.Frame(parent)
        self.search_frame.pack(fill="x", padx=15, pady=5)
        ttk.Label(
            self.search_frame, text=self.tr("editor_search", "🔍 Поиск:"), font=("Segoe UI", 9)
        ).pack(side="left")
        ttk.Button(
            self.search_frame, text=self.tr("editor_find", "➡️"), width=3, command=self._find_next
        ).pack(side="left", padx=2)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            self.search_frame, textvariable=self.search_var, width=20, font=("Segoe UI", 9)
        )
        self.search_entry.pack(side="left", padx=5)
        # ✅ ИСПОЛЬЗУЕМ Debounce для оптимизации поиска
        self._editor_filter_debounce_timer = None
        self.search_entry.bind("<KeyRelease>", self._filter_entries_debounced)
        self.search_entry.bind("<Return>", lambda e: self._find_next())
        ttk.Separator(self.search_frame, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Label(
            self.search_frame, text=self.tr("editor_status_filter", "Статус:"), font=("Segoe UI", 9)
        ).pack(side="left")
        self.status_filter_var = tk.StringVar(value=self.tr("editor_all", "Все"))
        self.status_filter_combo = ttk.Combobox(
            self.search_frame,
            textvariable=self.status_filter_var,
            values=[
                self.tr("editor_all", "Все"),
                self.tr("editor_translated", "✅ Переведённые"),
                self.tr("editor_partial", "⚠️ Частично"),
                self.tr("editor_untranslated", "⬜ Не переведённые"),
            ],
            width=18,
            state="readonly",
            font=("Segoe UI", 9),
        )
        self.status_filter_combo.pack(side="left", padx=5)
        self.status_filter_combo.bind("<<ComboboxSelected>>", self._on_status_filter_change)

    def _build_content_paned(self, parent):
        """Создаёт разделяемую панель с деревом записей и редактором"""
        ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=15, pady=2)

        content_paned = ttk.Panedwindow(parent, orient="horizontal")
        content_paned.pack(fill="both", expand=True, padx=15, pady=5)

        # Панель дерева записей
        tree_panel = ttk.LabelFrame(
            content_paned, text=self.tr("editor_records", "📋 Записи перевода")
        )
        content_paned.add(tree_panel, weight=3)

        # ✅ ИСПОЛЬЗУЕМ переиспользуемый компонент ScrollableTree
        from gui.components.scrollable_tree import ScrollableTree

        columns = ("key", "value", "status")
        self.tree_widget = ScrollableTree(
            tree_panel,
            columns=columns,
            headings={
                "key": self.tr("editor_key_col", "🔑 Ключ"),
                "value": self.tr("editor_value_col", "📝 Значение"),
                "status": self.tr("editor_status_col", "📊 Статус"),
            },
            column_widths={"key": 250, "value": 400, "status": 100},
            column_mins={"key": 100, "value": 150, "status": 80},
            selectmode="extended",
        )
        # ✅ Упаковываем ScrollableTree в панель дерева
        self.tree_widget.pack(fill="both", expand=True)

        self.tree_widget.tree.heading("key", command=lambda: self._sort_by("key"))
        self.tree_widget.tree.heading("value", command=lambda: self._sort_by("value"))
        self.tree_widget.tree.heading("status", command=lambda: self._sort_by("status"))

        for status, color in FILE_COLORS.items():
            self.tree_widget.tree.tag_configure(status, background=color, foreground="white")

        self.tree_widget.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree_widget.tree.bind("<Double-1>", self._on_double_click)
        self.tree_widget.tree.bind("<Button-3>", self._show_context_menu)

        # Псевдоним для обратной совместимости
        self.tree = self.tree_widget.tree

        # Панель редактирования
        edit_panel = ttk.LabelFrame(
            content_paned, text=self.tr("editor_editing", "✍️ Редактирование")
        )
        content_paned.add(edit_panel, weight=2)
        edit_panel.config(width=350)

        # Используем grid для всех виджетов в edit_panel
        ttk.Label(
            edit_panel, text=self.tr("editor_key", "🔑 Ключ:"), font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        self.key_entry = ttk.Entry(edit_panel, width=40, font=("Consolas", 10))
        self.key_entry.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 10))

        ttk.Label(
            edit_panel,
            text=self.tr("editor_original", "📄 Оригинал:"),
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=5, pady=(0, 0))
        self.original_text = tk.Text(edit_panel, height=4, wrap="word", font=("Segoe UI", 9))
        self.original_text.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))
        self.original_text.config(state="disabled")

        ttk.Label(
            edit_panel, text=self.tr("editor_value", "📝 Значение:"), font=("Segoe UI", 9, "bold")
        ).grid(row=4, column=0, sticky="w", padx=5, pady=(0, 0))
        self.value_text = tk.Text(edit_panel, height=8, wrap="word", font=("Consolas", 10))

        for tag, cfg in {
            "xml_tag": {"foreground": "#0000FF", "font": ("Consolas", 10, "bold")},
            "xml_attr": {"foreground": "#008000", "font": ("Consolas", 10)},
            "xml_string": {"foreground": "#FF0000", "font": ("Consolas", 10)},
            "xml_comment": {"foreground": "#808080", "font": ("Consolas", 10, "italic")},
            "xml_decl": {"foreground": "#800080", "font": ("Consolas", 10, "bold")},
            "spell_error": {"foreground": "red", "underline": True},
            "modified_bg": {"background": "#fff9c4"},
        }.items():
            self.value_text.tag_configure(tag, **cfg)

        text_scroll = ttk.Scrollbar(edit_panel, orient="vertical", command=self.value_text.yview)
        self.value_text.configure(yscrollcommand=text_scroll.set)

        self.value_text.grid(row=5, column=0, sticky="nsew", padx=5, pady=(0, 5))
        text_scroll.grid(row=5, column=1, sticky="ns", padx=(0, 5), pady=(0, 5))
        edit_panel.grid_rowconfigure(5, weight=1)
        edit_panel.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.key_entry.bind("<KeyRelease>", self._on_edit)
        self.value_text.bind("<KeyRelease>", self._on_edit_and_highlight)
        self.value_text.bind("<ButtonRelease>", self._on_edit_and_highlight)
        self.value_text.bind("<Button-3>", self._show_value_context_menu)

    def _open_file(self):
        fp = filedialog.askopenfilename(
            title=self.tr("editor_select_xml_file", "Выберите XML файл перевода"),
            filetypes=[
                (self.tr("filetype_xml", "XML файлы"), "*.xml"),
                (self.tr("filetype_all", "Все файлы"), "*.*"),
            ],
        )
        if fp:
            self._load_file(fp)

    def _open_folder(self):
        """Открыть все Keyed файлы из выбранной папки"""
        folder = filedialog.askdirectory(
            title=self.tr("editor_select_keyed_folder", "Выберите папку Keyed с переводами"),
        )
        if folder:
            self._load_folder(folder)

    def _load_folder(self, folder: str):
        """Загрузить все Keyed XML файлы из папки"""
        self.file_path = folder
        self.entries.clear()
        self.file_map = {}
        self.folder_mode = True  # ✅ Режим папки

        self.file_label.config(text=self.tr("editor_folder_label", "Папка: ") + folder)
        self.save_indicator.config(
            text=self.tr("editor_status_loading", "⏳ Загрузка..."), foreground="orange"
        )
        self.dialog.update()

        total_entries = 0
        files_loaded = 0
        files_errors = 0

        for root, dirs, files in os.walk(folder):
            for fn in files:
                if not fn.endswith(".xml"):
                    continue
                fp = os.path.join(root, fn)
                try:
                    tree = ET.parse(fp)
                    root_elem = tree.getroot()
                    rel_path = os.path.relpath(fp, folder)

                    for child in root_elem:
                        key = child.tag
                        value = child.text or ""
                        status = "complete" if value.strip() else "empty"
                        self.entries.append(
                            {
                                "key": key,
                                "value": value,
                                "original_value": value,
                                "status": status,
                                "file": rel_path,
                            }
                        )
                        self.file_map[key] = rel_path

                    total_entries += len(list(root_elem))
                    files_loaded += 1
                    print(f"  Загружен {fn}: {len(list(root_elem))} записей")
                except Exception as e:
                    files_errors += 1
                    print(f"  ❌ Ошибка {fn}: {e}")

        self._update_tree()
        self.save_indicator.config(text=self.tr("editor_ready", "💾 Готов"), foreground="#757575")
        self.header_title.config(
            text=f"📁 Папка: {os.path.basename(folder)} ({files_loaded} файлов)"
        )
        print(
            f"✅ Загружено {total_entries} записей из {files_loaded} файлов"
            + (f" ({files_errors} с ошибками)" if files_errors else "")
        )

        if total_entries == 0:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_no_xml_files", "В папке не найдено XML файлов:\n{path}").format(
                    path=folder
                ),
            )

    def _load_file(self, file_path: str):
        self.file_path = file_path
        self.file_label.config(text=self.tr("editor_file_label", "Файл: ") + file_path)
        self.entries.clear()
        self.save_indicator.config(
            text=self.tr("editor_status_loading", "⏳ Загрузка..."), foreground="orange"
        )
        self.dialog.update()

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # RimWorld Keyed XML: <LanguageData><Key1>Value1</Key1><Key2>Value2</Key2>...</LanguageData>
            # Все ключи - прямые потомки корня (LanguageData)
            for child in root:
                key = child.tag
                value = child.text or ""
                status = "complete" if value.strip() else "empty"
                self.entries.append(
                    {"key": key, "value": value, "original_value": value, "status": status}
                )

            self._update_tree()
            self.save_indicator.config(
                text=self.tr("editor_ready", "💾 Готов"), foreground="#757575"
            )
        except ET.ParseError as e:
            messagebox.showerror(
                self.tr("editor_error", "Ошибка"),
                self.tr("editor_parse_error", "Ошибка парсинга XML:\n{}").format(e),
            )
        except Exception as e:
            messagebox.showerror(
                self.tr("editor_error", "Ошибка"),
                self.tr("editor_load_error", "Ошибка загрузки файла:\n{}").format(e),
            )

    def _update_tree(self, filter_text: str = ""):
        for item in self.tree.get_children():
            self.tree.delete(item)

        status_filter_key = self._get_status_filter_key()
        total, complete, partial, empty = len(self.entries), 0, 0, 0

        # Проверяем загружена ли папка (есть ли file_map)
        is_folder_mode = hasattr(self, "file_map") and self.file_map

        for entry in self.entries:
            key = entry["key"]
            value = entry["value"]
            status = entry.get("status", "empty")
            file_name = entry.get("file", "")

            if status == "complete":
                complete += 1
            elif status == "partial":
                partial += 1
            else:
                empty += 1

            if status_filter_key != "all":
                if status_filter_key != status:
                    continue
            if filter_text and filter_text not in key.lower() and filter_text not in value.lower():
                continue

            # В режиме папки показываем имя файла и версию в колонке status
            if is_folder_mode and file_name:
                # Извлекаем версию из пути (проверяем что show_versions_var существует)
                version = self._extract_version_from_path(file_name)
                if (
                    version
                    and getattr(self, "show_versions_var", None)
                    and self.show_versions_var.get()
                ):
                    display_status = f"📄 {version}/{os.path.basename(file_name)}"
                else:
                    display_status = f"📄 {os.path.basename(file_name)}"
            else:
                display_status = status

            self.tree.insert("", "end", values=(key, value, display_status), tags=(status,))

        if hasattr(self, "stats_label"):
            shown = len(self.tree.get_children())
            stats_text = f"📊 Всего: {total} | ✅ {complete} | ⬜ {empty} | Показано: {shown}"
            if is_folder_mode:
                files_count = len(set(e.get("file", "") for e in self.entries))
                # Подсчитываем версии
                versions = set()
                for e in self.entries:
                    v = self._extract_version_from_path(e.get("file", ""))
                    if v:
                        versions.add(v)
                if versions:
                    stats_text = f"📊 Всего: {total} | ✅ {complete} | ⬜ {empty} | 📁 Файлов: {files_count} | 🎮 Версий: {', '.join(sorted(versions))} | Показано: {shown}"
                else:
                    stats_text = f"📊 Всего: {total} | ✅ {complete} | ⬜ {empty} | 📁 Файлов: {files_count} | Показано: {shown}"
            self.stats_label.config(text=stats_text)

    def _extract_version_from_path(self, path: str) -> str | None:
        """Извлекает версию игры из пути файла"""
        if not path:
            return None
        # Ищем паттерн версии в пути
        import re

        match = re.search(r"[\\/](\d+\.\d+)[\\/]", path)
        if match:
            return match.group(1)
        return None

    def _sort_by(self, column):
        if self._sort_column == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = column
            self._sort_reverse = False

        def sort_key(entry):
            val = entry.get(column, "")
            return int(val) if val.isdigit() else val.lower()

        self.entries.sort(key=sort_key, reverse=self._sort_reverse)
        self._update_tree(self.search_var.get().lower() if hasattr(self, "search_var") else "")

    def _select_all_entries(self):
        self.tree.selection_set(self.tree.get_children())

    def _on_status_filter_change(self, event=None):
        self._update_tree(self.search_var.get().lower() if hasattr(self, "search_var") else "")

    def _get_status_filter_key(self):
        val = self.status_filter_var.get() if hasattr(self, "status_filter_var") else "Все"
        mapping = {
            self.tr("editor_translated", "✅ Переведённые"): "complete",
            self.tr("editor_partial", "⚠️ Частично"): "partial",
            self.tr("editor_untranslated", "⬜ Не переведённые"): "empty",
        }
        return mapping.get(val, "all")

    def _on_edit_and_highlight(self, event=None):
        self._on_edit(event)
        self._highlight_syntax()
        self._highlight_spelling()

    def _highlight_syntax(self, event=None):
        for tag in [
            "xml_tag",
            "xml_attr",
            "xml_string",
            "xml_comment",
            "xml_decl",
            "spell_error",
            "modified_bg",
        ]:
            self.value_text.tag_remove(tag, "1.0", tk.END)

        content = self.value_text.get("1.0", tk.END)
        patterns = [
            (r"<!--.*?-->", "xml_comment", re.DOTALL),
            (r"<\?xml.*?\?>", "xml_decl", re.DOTALL),
            (r"</?[a-zA-Z_:][a-zA-Z0-9_:.-]*", "xml_tag"),
            (r"\s+[a-zA-Z_:][a-zA-Z0-9_:.-]*\s*=", "xml_attr"),
            (r'"[^"]*"|\'[^\']*\'', "xml_string"),
            (r"\[[a-zA-Z][^\]]*\]", "xml_tag"),
            (r"\{[^}]+\}", "xml_attr"),
        ]
        for pat, tag, *flags in patterns:
            for m in re.finditer(pat, content, *flags):
                self.value_text.tag_add(tag, f"1.0+{m.start()}c", f"1.0+{m.end()}c")

        current_value = content.strip()
        original_value = ""
        sel = self.tree.selection()
        if sel:
            key = self.tree.item(sel[0])["values"][0]
            for entry in self.entries:
                if entry["key"] == key:
                    original_value = entry.get("original_value", "").strip()
                    break
        if current_value and current_value != original_value:
            self.value_text.tag_add("modified_bg", "1.0", tk.END)

    def _highlight_spelling(self, event=None):
        if not HAS_SPELLCHECKER:
            return
        self.value_text.tag_remove("spell_error", "1.0", tk.END)
        text = self.value_text.get("1.0", tk.END)
        if not text.strip():
            return

        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            lang = cfg.get("target_language", "Russian").lower()
            spell_lang = {"russian": "ru", "english": "en", "german": "de", "polish": "pl"}.get(
                lang, "ru"
            )
        except Exception:
            spell_lang = "ru"

        try:
            spell = SpellChecker(language=spell_lang)
            words = re.findall(r"\b[a-zA-Zа-яА-ЯёЁ]+\b", text)
            misspelled = spell.unknown(words)
            for word in misspelled:
                if len(word) < 3:
                    continue
                for m in re.finditer(re.escape(word), text, re.IGNORECASE):
                    self.value_text.tag_add("spell_error", f"1.0+{m.start()}c", f"1.0+{m.end()}c")
        except Exception:
            pass

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        key, value, _ = item["values"]

        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, key)

        original_value = ""
        for entry in self.entries:
            if entry["key"] == key:
                original_value = entry.get("original_value", "")
                break
        self.original_text.config(state="normal")
        self.original_text.delete("1.0", tk.END)
        self.original_text.insert("1.0", original_value)
        self.original_text.config(state="disabled")

        self.value_text.delete("1.0", tk.END)
        self.value_text.insert("1.0", value)
        self._highlight_syntax()
        self._highlight_spelling()

    def _on_double_click(self, event):
        self._on_select(event)
        self.value_text.focus_set()

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
        self._create_context_menu()
        self._context_menu.post(event.x_root, event.y_root)

    def _create_context_menu(self):
        self._context_menu = ttk.Menu(self.dialog, tearoff=0)
        
        self._context_menu.add_command(
            label=self.tr("ctx_copy_key", "Копировать ключ"),
            command=self._ctx_copy_key
        )
        self._context_menu.add_command(
            label=self.tr("ctx_copy_value", "Копировать значение"),
            command=self._ctx_copy_value
        )
        self._context_menu.add_command(
            label=self.tr("ctx_paste_value", "Вставить значение"),
            command=self._ctx_paste_value
        )
        self._context_menu.add_separator()
        self._context_menu.add_command(
            label=self.tr("ctx_delete_entry", "Удалить запись"),
            command=self._delete_entry
        )
        self._context_menu.add_separator()
        self._context_menu.add_command(
            label=self.tr("ctx_add_to_glossary", "Добавить в глоссарий"),
            command=self._add_selection_to_glossary
        )
        self._context_menu.add_command(
            label=self.tr("ctx_auto_translate", "Автоперевод"),
            command=self._ctx_auto_translate
        )
        self._context_menu.add_separator()
        self._context_menu.add_command(
            label=self.tr("ctx_export_csv", "Экспорт в CSV"),
            command=self._ctx_export_selected
        )
        self._context_menu.add_command(
            label=self.tr("ctx_quality_check", "Проверка качества"),
            command=self._ctx_check_quality
        )

    def _show_value_context_menu(self, event):
        """Контекстное меню для поля значения"""
        self._value_context_menu = ttk.Menu(self.dialog, tearoff=0)
        self._value_context_menu.add_command(
            label=self.tr("ctx_cut", "Вырезать"),
            command=self._value_cut
        )
        self._value_context_menu.add_command(
            label=self.tr("ctx_copy", "Копировать"),
            command=self._value_copy
        )
        self._value_context_menu.add_command(
            label=self.tr("ctx_paste", "Вставить"),
            command=self._value_paste
        )
        self._value_context_menu.add_separator()
        self._value_context_menu.add_command(
            label=self.tr("ctx_select_all", "Выделить всё"),
            command=self._value_select_all
        )
        self._value_context_menu.post(event.x_root, event.y_root)

    def _value_cut(self):
        self.value_text.event_generate("<<Cut>>")

    def _value_copy(self):
        self.value_text.event_generate("<<Copy>>")

    def _value_paste(self):
        self.value_text.event_generate("<<Paste>>")

    def _value_select_all(self):
        self.value_text.tag_add("sel", "1.0", "end")

    def _ctx_copy_key(self):
        sel = self.tree.selection()
        if sel:
            key = self.tree.item(sel[0])["values"][0]
            self.clipboard_clear()
            self.clipboard_append(key)

    def _ctx_copy_value(self):
        sel = self.tree.selection()
        if sel:
            value = self.tree.item(sel[0])["values"][1]
            self.clipboard_clear()
            self.clipboard_append(value)

    def _ctx_paste_value(self):
        sel = self.tree.selection()
        if sel:
            try:
                value = self.clipboard_get()
                self.value_text.delete("1.0", tk.END)
                self.value_text.insert("1.0", value)
                self._on_edit(None)
            except tk.TclError:
                pass

    def _ctx_auto_translate(self):
        sel = self.tree.selection()
        if not sel:
            return
        from config.config_manager import get_config_manager
        from translation.translator import AutoTranslator

        item = self.tree.item(sel[0])
        key, value = item["values"][0], item["values"][1]
        
        if value.strip():
            return
            
        cfg = get_config_manager()
        translator = AutoTranslator(
            enabled=True,
            source_lang=cfg.get("source_language", "English"),
            target_lang=cfg.get("target_language", "Russian"),
            engine_names=None,
        )
        
        try:
            translated = translator.translate(key, key)
            if translated:
                for entry in self.entries:
                    if entry["key"] == key:
                        entry["value"] = translated
                        entry["status"] = "partial"
                        break
                self._update_tree()
                self._on_select(None)
        except Exception:
            pass

    def _ctx_export_selected(self):
        sel = self.tree.selection()
        if not sel:
            sel_entries = self.entries
        else:
            sel_entries = []
            for iid in sel:
                k = self.tree.item(iid)["values"][0]
                for e in self.entries:
                    if e["key"] == k:
                        sel_entries.append(e)
                        break
        
        fp = filedialog.asksaveasfilename(
            title=self.tr("editor_save_csv_title", "Сохранить CSV"),
            defaultextension=".csv",
            filetypes=[(self.tr("filetype_csv", "CSV файлы"), "*.csv")],
        )
        if fp:
            import csv
            with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow([self.tr("csv_header_key", "Ключ"), self.tr("csv_header_value", "Значение"), self.tr("csv_header_status", "Статус")])
                for e in sel_entries:
                    w.writerow([e["key"], e["value"], e.get("status", "empty")])

    def _ctx_check_quality(self):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])
        key, value = item["values"][0], item["values"][1]
        issues = []
        if not value.strip():
            issues.append(self.tr("editor_quality_untranslated", "❌ Не переведено"))
        if value and (value.startswith(" ") or value.endswith(" ") or "  " in value):
            issues.append(self.tr("editor_quality_extra_spaces", "⚠️ Лишние пробелы"))
        
        from tkinter import messagebox
        msg = "\n".join(issues) if issues else self.tr("editor_quality_ok", "✅ OK")
        messagebox.showinfo(self.tr("editor_quality_check_warn", "Проверка качества"), f"{key}:\n{msg}")

    def _on_edit(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        if self._auto_save_id:
            self.dialog.after_cancel(self._auto_save_id)
        self.save_indicator.config(
            text=self.tr("editor_status_unsaved", "🔴 Не сохранено"), foreground="red"
        )
        self._auto_save_id = self.dialog.after(AUTO_SAVE_DELAY, self._auto_save)

        item_id = sel[0]
        old_key = self.tree.item(item_id)["values"][0]
        new_key = self.key_entry.get()
        new_value = self.value_text.get("1.0", tk.END).strip()

        found = None
        for entry in self.entries:
            if entry["key"] == old_key:
                entry["key"] = new_key
                entry["value"] = new_value
                entry["status"] = "complete" if new_value.strip() else "empty"
                found = entry
                self.modified = True
                break

        if not found:
            found = {
                "key": new_key,
                "value": new_value,
                "original_value": "",
                "status": "complete" if new_value.strip() else "empty",
            }
            self.entries.append(found)
            self.modified = True

        self.tree.item(
            item_id, values=(new_key, new_value, found["status"]), tags=(found["status"],)
        )
        self.history_manager.push_state(self.entries.copy())
        self._update_undo_redo_buttons()

    def _auto_save(self):
        if not hasattr(self, "dialog") or not self.dialog.winfo_exists():
            return
        if self.modified and self.file_path:
            self.save_indicator.config(
                text=self.tr("editor_saving", "🟡 Сохранение..."), foreground="orange"
            )
            self._save_file(silent=True)
            self.modified = False

    def _add_entry(self):
        self.entries.append({"key": "NewKey", "value": "", "original_value": "", "status": "empty"})
        self._update_tree()
        self.modified = True
        self.history_manager.push_state(self.entries.copy())
        self._update_undo_redo_buttons()

    def _delete_entry(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_select_entry_delete", "Выберите запись для удаления"),
            )
            return
        key = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno(
            self.tr("editor_confirm", "Подтверждение"),
            self.tr("editor_confirm_delete", "Удалить запись") + f" '{key}'?",
        ):
            self.entries = [e for e in self.entries if e["key"] != key]
            self._update_tree()
            self.modified = True
            self.history_manager.push_state(self.entries.copy())
            self._update_undo_redo_buttons()

    def _save_file(self, silent=False):
        if not self.file_path:
            self._save_as_file()
            return
        try:
            import shutil

            backup_path = self.file_path + ".bak"
            if os.path.exists(self.file_path):
                shutil.copy2(self.file_path, backup_path)

            root = ET.Element("LanguageData")
            for entry in self.entries:
                elem = ET.SubElement(root, entry["key"])
                elem.text = entry["value"]
            ET.ElementTree(root).write(self.file_path, encoding="utf-8", xml_declaration=True)

            for entry in self.entries:
                entry["original_value"] = entry["value"]
            self.modified = False
            self.save_indicator.config(
                text=self.tr("editor_status_saved", "✅ Сохранено"), foreground="green"
            )

            if not silent:
                messagebox.showinfo(
                    self.tr("editor_success", "Успех"),
                    self.tr("editor_saved_msg", "Файл сохранён:\n{}\nBackup: {}").format(
                        self.file_path, backup_path
                    ),
                )
                self._sync_translations_to_glossary()
        except Exception as e:
            messagebox.showerror(
                self.tr("editor_error", "Ошибка"),
                self.tr("editor_save_error", "Ошибка сохранения:\n{}").format(e),
            )

    def _save_as_file(self):
        fp = filedialog.asksaveasfilename(
            title=self.tr("editor_save_file_title", "Сохранить файл перевода"),
            defaultextension=".xml",
            filetypes=[
                (self.tr("filetype_xml", "XML файлы"), "*.xml"),
                (self.tr("filetype_all", "Все файлы"), "*.*"),
            ],
        )
        if fp:
            self.file_path = fp
            self._save_file()

    def _sync_translations_to_glossary(self):
        """Синхронизирует качественные переводы в глоссарий"""
        if not self._glossary_sync_enabled:
            return 0
        
        try:
            from config.config_manager import get_config_manager
            target_lang = get_config_manager().get("target_language", "Russian")
            db = get_translation_db(target_lang)
            if not db:
                return 0
            
            synced_count = 0
            
            for entry in self.entries:
                key = entry.get("key", "")
                value = entry.get("value", "")
                
                if not key or not value:
                    continue
                
                if len(value.strip()) < 2:
                    continue
                
                try:
                    db.add_glossary_term(key, value, category="auto", description="Auto-synced from translation", target_language=target_lang)
                    synced_count += 1
                except Exception:
                    pass
            
            if synced_count > 0:
                self.log(f"Синхронизировано {synced_count} терминов в глоссарий")
            return synced_count
        except Exception as e:
            self.log(f"Ошибка синхронизации с глоссарий: {e}")
            return 0

    def _refresh(self):
        if self.file_path:
            self._load_file(self.file_path)

    def _filter_entries_debounced(self, event=None):
        """Debounce для фильтрации записей редактора (300мс задержка)"""
        if self._editor_filter_debounce_timer:
            self.dialog.after_cancel(self._editor_filter_debounce_timer)
        self._editor_filter_debounce_timer = self.dialog.after(300, self._filter_entries)

    def _filter_entries(self, event=None):
        self._update_tree(self.search_var.get().lower())

    def _undo(self):
        state = self.history_manager.pop_state()
        if state is not None:
            self.entries = state
            self._update_tree()
            self._update_undo_redo_buttons()
            self.modified = True

    def _redo(self):
        state = self.history_manager.redo_state()
        if state is not None:
            self.entries = state
            self._update_tree()
            self._update_undo_redo_buttons()
            self.modified = True

    def _update_undo_redo_buttons(self):
        if hasattr(self, "undo_btn"):
            self.undo_btn.config(state="normal" if self.history_manager.can_undo() else "disabled")
        if hasattr(self, "redo_btn"):
            self.redo_btn.config(state="normal" if self.history_manager.can_redo() else "disabled")

    def _show_editor_help(self):
        """Показать справку из JSON файла"""
        try:
            from gui.help.help_loader import format_editor_help_text, load_editor_help

            help_data = load_editor_help()
            help_text = format_editor_help_text(help_data)
        except Exception:
            # Fallback на английском (универсальный язык)
            help_text = self.tr(
                "editor_help_fallback",
                "📖 Translation Editor Help\n\n"
                "📂 File: Open / Save / Update\n"
                "✍️ Editing: Ctrl+Z / Ctrl+Y / Ctrl+S\n"
                "🔀 Diff: Compare with original\n"
                "🔧 Operations: Mass editing / Auto-translate\n"
                "✅ Check: CSV export / Quality / Spell check\n"
                "⌨️ Hotkeys: Ctrl+S, Ctrl+A, Ctrl+F, Esc",
            )

        messagebox.showinfo(self.tr("editor_help_title", "📖 Help"), help_text)

    def _on_drop_file(self, event):
        try:
            fp = event.data.strip("{} ").strip('"')
            if fp.endswith(".xml"):
                self._load_file(fp)
        except Exception:
            pass

    def _close_dialog(self):
        if self.modified:
            res = messagebox.askyesnocancel(
                self.tr("editor_unsaved_title", "Несохранённые изменения"),
                self.tr("editor_unsaved_msg", "Сохранить перед закрытием?"),
            )
            if res is None:
                return
            if res:
                self._save_file(silent=True)
        if self._auto_save_id:
            self.dialog.after_cancel(self._auto_save_id)
        if hasattr(self, "dialog") and self.dialog.winfo_exists():
            self.dialog.destroy()

    def _apply_fonts_from_config(self):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        main_f = cfg.get("main_font", {"family": "Segoe UI", "size": 9})
        log_f = cfg.get("log_font", {"family": "Consolas", "size": 10})
        mf, ms = main_f.get("family", "Segoe UI"), main_f.get("size", 9)
        lf, ls = log_f.get("family", "Consolas"), log_f.get("size", 10)

        for w in self.header_content.winfo_children():
            if isinstance(w, tk.Label):
                txt = w.cget("text")
                if "✏️" in txt:
                    w.config(font=(mf, ms + 7, "bold"))
                elif "💾" in txt:
                    w.config(font=(mf, max(8, ms - 1)))
        for w in self.info_bar.winfo_children():
            if isinstance(w, tk.Label):
                w.config(font=(mf, max(8, ms - 1)))
        if hasattr(self, "tree"):
            style = ttk.Style()
            style.configure("Editor.Treeview", font=(lf, ls))
            style.configure("Editor.Treeview.Heading", font=(lf, ls, "bold"))
            self.tree.configure(style="Editor.Treeview")
        if hasattr(self, "key_entry"):
            self.key_entry.config(font=(lf, ls))
        if hasattr(self, "original_text"):
            self.original_text.config(font=(lf, max(8, ls - 1)))
        if hasattr(self, "value_text"):
            self.value_text.config(font=(lf, ls))
        for w in self.search_frame.winfo_children():
            if isinstance(w, tk.Label):
                w.config(font=(mf, max(8, ms - 1)))
            elif isinstance(w, ttk.Combobox):
                w.config(font=(mf, max(8, ms - 1)))
            elif isinstance(w, ttk.Entry):
                w.config(font=(mf, ms))

    def _setup_keyboard_shortcuts(self):
        """Настройка горячих клавиш с поддержкой всех раскладок"""
        from gui.keyboard import HotkeyManager

        # ✅ Создаём менеджер хоткеев для редактора
        self.editor_hotkeys = HotkeyManager(self.dialog)

        # Файл и редактирование
        self.editor_hotkeys.register("Ctrl+Z", lambda e: self._undo())
        self.editor_hotkeys.register("Ctrl+Y", lambda e: self._redo())
        self.editor_hotkeys.register("Ctrl+S", lambda e: self._save_file())
        self.editor_hotkeys.register("Ctrl+F", lambda e: self.search_entry.focus_set())
        self.editor_hotkeys.register("Ctrl+H", lambda e: self._show_replace_dialog())
        self.editor_hotkeys.register("Ctrl+A", lambda e: self._select_all_entries())

        # Навигация
        self.editor_hotkeys.register("Ctrl+Down", lambda e: self._next_entry())
        self.editor_hotkeys.register("Ctrl+Up", lambda e: self._prev_entry())
        self.editor_hotkeys.register("Ctrl+ENTER", lambda e: self._save_and_next())

        # Действия
        self.editor_hotkeys.register("F2", lambda e: self._rename_key())
        self.editor_hotkeys.register("Delete", lambda e: self._delete_entry())

        #  НОВОЕ (#17): Горячая клавиша "Add to Glossary" — Ctrl+G
        self.editor_hotkeys.register("Ctrl+G", lambda e: self._add_selection_to_glossary())
        
        # ✅ Escape для закрытия
        self.editor_hotkeys.register("Escape", lambda e: self._close_dialog())

    def _next_entry(self):
        items = list(self.tree.get_children())
        if not items:
            return
        sel = self.tree.selection()
        idx = items.index(sel[0]) + 1 if sel and sel[0] in items else 0
        next_item = items[idx % len(items)]
        self.tree.selection_set(next_item)
        self.tree.see(next_item)
        self._on_select(None)

    def _prev_entry(self):
        items = list(self.tree.get_children())
        if not items:
            return
        sel = self.tree.selection()
        idx = items.index(sel[0]) - 1 if sel and sel[0] in items else 0
        prev_item = items[idx % len(items)]
        self.tree.selection_set(prev_item)
        self.tree.see(prev_item)
        self._on_select(None)

    def _save_and_next(self):
        if self.modified and self.file_path:
            self._save_file(silent=True)
        self._next_entry()

    def _rename_key(self):
        sel = self.tree.selection()
        if not sel:
            return
        self.key_entry.focus_set()
        self.key_entry.select_range(0, tk.END)

    def _find_next(self):
        q = self.search_var.get().lower()
        if not q:
            return
        items = self.tree.get_children()
        if not items:
            return
        sel = self.tree.selection()
        start = items.index(sel[0]) + 1 if sel and sel[0] in items else 0
        for i in list(range(start, len(items))) + list(range(0, start)):
            vals = self.tree.item(items[i])["values"]
            if q in str(vals[0]).lower() or q in str(vals[1]).lower():
                self.tree.selection_set(items[i])
                self.tree.see(items[i])
                self._on_select(None)
                return
        messagebox.showinfo(
            self.tr("editor_search", "Поиск"),
            self.tr("editor_not_found", "Не найдено: {q}").format(q=q),
        )

    def _show_replace_dialog(self):
        dlg = tk.Toplevel(self.dialog)
        dlg.title(self.tr("editor_search_replace", "Поиск и замена"))
        dlg.geometry("400x200")
        dlg.transient(self.dialog)
        dlg.grab_set()
        ttk.Label(dlg, text=self.tr("editor_find", "Найти:")).grid(row=0, column=0, padx=5, pady=5)
        find_var = tk.StringVar(value=self.search_var.get())
        find_entry = ttk.Entry(dlg, textvariable=find_var, width=30)
        find_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(dlg, text=self.tr("editor_replace_with", "Заменить на:")).grid(
            row=1, column=0, padx=5, pady=5
        )
        repl_var = tk.StringVar()
        repl_entry = ttk.Entry(dlg, textvariable=repl_var, width=30)
        repl_entry.grid(row=1, column=1, padx=5, pady=5)

        def do_replace_one():
            self._replace(find_var.get(), repl_var.get())
            dlg.destroy()

        def do_replace_all():
            c = self._replace_all(find_var.get(), repl_var.get())
            dlg.destroy()
            messagebox.showinfo(
                self.tr("editor_replace", "Замена"),
                f"{self.tr('editor_replaced_count', 'Заменено')} {c} {self.tr('editor_occurrences', 'вхождений')}",
            )

        bf = ttk.Frame(dlg)
        bf.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(
            bf, text=self.tr("editor_find_next", "Найти далее"), command=self._find_next
        ).pack(side="left", padx=2)
        ttk.Button(bf, text=self.tr("editor_replace", "Заменить"), command=do_replace_one).pack(
            side="left", padx=2
        )
        ttk.Button(
            bf, text=self.tr("editor_replace_all", "Заменить все"), command=do_replace_all
        ).pack(side="left", padx=2)

    def _replace(self, find, repl):
        sel = self.tree.selection()
        if not sel:
            return
        old_key = self.tree.item(sel[0])["values"][0]
        for entry in self.entries:
            if entry["key"] == old_key:
                entry["key"] = (
                    entry["key"].replace(find, repl) if find in entry["key"] else entry["key"]
                )
                entry["value"] = (
                    entry["value"].replace(find, repl) if find in entry["value"] else entry["value"]
                )
                entry["status"] = "complete" if entry["value"].strip() else "empty"
                self.modified = True
                self.history_manager.push_state(self.entries.copy())
                break
        self._update_tree()

    def _replace_all(self, find, repl):
        if not find:
            return 0
        c = 0
        for entry in self.entries:
            k = find.lower() in entry["key"].lower()
            v = find.lower() in entry["value"].lower()
            if k:
                entry["key"] = re.sub(re.escape(find), repl, entry["key"], flags=re.IGNORECASE)
            if v:
                entry["value"] = re.sub(re.escape(find), repl, entry["value"], flags=re.IGNORECASE)
                entry["status"] = "complete" if entry["value"].strip() else "empty"
            if k or v:
                c += 1
        if c > 0:
            self.modified = True
            self._update_tree()
            self.history_manager.push_state(self.entries.copy())
        return c

    def _show_mass_edit_dialog(self):
        """Массовое редактирование (вынесено в отдельный диалог)"""
        from gui.dialogs.mass_edit_dialog import MassEditDialog

        count = MassEditDialog(self.dialog, self.tree, self.entries, self.history_manager)
        if count:
            self.modified = True
            self._update_tree()
            self.history_manager.push_state(self.entries.copy())
            self.save_indicator.config(
                text=self.tr("editor_status_unsaved", "🔴 Не сохранено"), foreground="red"
            )
            messagebox.showinfo(
                self.tr("editor_success", "Успех"),
                self.tr("editor_mass_edit_applied", "Обновлено {count} записей").format(
                    count=count
                ),
            )

    def _translate_empty(self):
        from config.config_manager import get_config_manager
        from translation.translator import AutoTranslator

        ec = sum(1 for e in self.entries if not e.get("value", "").strip())
        if ec == 0:
            messagebox.showinfo(
                self.tr("editor_info", "Инфо"),
                self.tr("editor_no_empty_entries", "Нет пустых записей для перевода"),
            )
            return

        cfg = get_config_manager()
        source_lang = cfg.get("source_language", "English")
        target_lang = cfg.get("target_language", "Russian")
        auto_split_glossary = cfg.get("auto_split_glossary", True)

        translator = AutoTranslator(
            enabled=True,
            source_lang=source_lang,
            target_lang=target_lang,
            engine_names=None,
            config={"auto_split_glossary": auto_split_glossary},
        )

        if not messagebox.askyesno(
            self.tr("editor_translate_empty_title", "Подтверждение"),
            self.tr("editor_translate_empty_confirm", "Найдено {count} пустых записей. Выполнить автоперевод?").format(count=ec),
        ):
            return

        cnt = 0
        for e in self.entries:
            if not e.get("value", "").strip():
                try:
                    translated = translator.translate(e["key"], e["key"])
                    if translated:
                        e["value"] = translated
                        e["status"] = "partial"
                        cnt += 1
                except Exception:
                    e["value"] = e["key"].replace("_", " ").title()
                    e["status"] = "partial"
                    cnt += 1

        self.modified = True
        self._update_tree()
        self.history_manager.push_state(self.entries.copy())
        self.save_indicator.config(
            text=self.tr("editor_status_unsaved", "🔴 Не сохранено"), foreground="red"
        )
        messagebox.showinfo(
            self.tr("editor_success", "Успех"),
            self.tr("editor_translated_empty", "Переведено {cnt} записей").format(
                cnt=cnt
            ),
        )

    def _export_selected_to_csv(self):
        sel = self.tree.selection()
        if not sel:
            if not messagebox.askyesno(
                self.tr("editor_info", "Инфо"),
                self.tr(
                    "editor_export_all_prompt", "Ничего не выбрано. Экспортировать все записи?"
                ),
            ):
                return
            sel_entries = self.entries
        else:
            sel_entries = []
            for iid in sel:
                k = self.tree.item(iid)["values"][0]
                for e in self.entries:
                    if e["key"] == k:
                        sel_entries.append(e)
                        break

        fp = filedialog.asksaveasfilename(
            title=self.tr("editor_save_csv_title", "Сохранить CSV"),
            defaultextension=".csv",
            filetypes=[(self.tr("filetype_csv", "CSV файлы"), "*.csv")],
            initialfile=f"export_{os.path.basename(self.file_path) if self.file_path else 'translation'}.csv",
        )
        if not fp:
            return
        with open(fp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    self.tr("csv_header_key", "Ключ"),
                    self.tr("csv_header_value", "Значение"),
                    self.tr("csv_header_status", "Статус"),
                ]
            )
            for e in sel_entries:
                w.writerow([e["key"], e["value"], e.get("status", "empty")])
        messagebox.showinfo(
            self.tr("editor_success", "Успех"),
            self.tr("editor_exported_csv", "Экспортировано {cnt} записей в:\n{path}").format(
                cnt=len(sel_entries), path=fp
            ),
        )

    def _check_translation_quality(self):
        issues = []
        for i, e in enumerate(self.entries, 1):
            k, v, s = e["key"], e["value"], e.get("status", "empty")
            if s == "empty":
                issues.append(
                    self.tr(
                        "editor_quality_untranslated", "❌ Строка {i}: '{k}' - не переведена"
                    ).format(i=i, k=k)
                )
            if v and (v.startswith(" ") or v.endswith(" ") or "  " in v):
                issues.append(
                    self.tr(
                        "editor_quality_extra_spaces", "⚠️ Строка {i}: '{k}' - лишние пробелы"
                    ).format(i=i, k=k)
                )
            orig = e.get("original_value", "")
            p_orig = re.findall(r"\{\d+\}", orig)
            p_trans = re.findall(r"\{\d+\}", v)
            if set(p_orig) != set(p_trans):
                issues.append(
                    self.tr(
                        "editor_quality_placeholder_mismatch",
                        "⚠️ Строка {i}: '{k}' - несоответствие плейсхолдеров",
                    ).format(i=i, k=k)
                )
            tags_o = re.findall(r"\[.*?\]|<.*?>", orig)
            tags_t = re.findall(r"\[.*?\]|<.*?>", v)
            if tags_o and not tags_t:
                issues.append(
                    self.tr(
                        "editor_quality_missing_tags", "⚠️ Строка {i}: '{k}' - отсутствуют теги"
                    ).format(i=i, k=k)
                )
            if v and orig and len(v) > len(orig) * 1.5:
                issues.append(
                    self.tr(
                        "editor_quality_too_long", "ℹ️ Строка {i}: '{k}' - перевод слишком длинный"
                    ).format(i=i, k=k)
                )
            if v and v.isupper() and len(v) > 3:
                issues.append(
                    self.tr(
                        "editor_quality_caps_lock", "ℹ️ Строка {i}: '{k}' - возможен Caps Lock"
                    ).format(i=i, k=k)
                )

        if not issues:
            messagebox.showinfo(
                "✅ Проверка качества", f"Проблем не найдено!\nВсего записей: {len(self.entries)}"
            )
        else:
            report = f"Найдено проблем: {len(issues)}\n\n" + "\n".join(issues[:20])
            if len(issues) > 20:
                report += f"\n\n... и ещё {len(issues) - 20} проблем"
            messagebox.showwarning(
                self.tr("editor_quality_check_warn", "⚠️ Проверка качества"), report
            )

    def _check_spelling(self):
        if not HAS_SPELLCHECKER:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr(
                    "editor_spellcheck_not_installed", "Установите: pip install pyspellchecker"
                ),
            )
            return
        dlg = tk.Toplevel(self.dialog)
        dlg.title(self.tr("editor_spellcheck_title", "Выбор языка"))
        dlg.geometry("300x200")
        dlg.transient(self.dialog)
        dlg.grab_set()
        ttk.Label(dlg, text=self.tr("editor_spellcheck_lang", "Выберите язык проверки:")).pack(
            pady=10
        )
        lv = tk.StringVar(value="ru")
        for d, c in [
            ("🇷🇺 Русский", "ru"),
            ("🇬🇧 English", "en"),
            ("🇩🇪 Deutsch", "de"),
            ("🇫🇷 Français", "fr"),
            ("🇪🇸 Español", "es"),
        ]:
            ttk.Radiobutton(dlg, text=d, variable=lv, value=c).pack(anchor="w", padx=20)
        res = [None]

        def ok():
            res[0] = lv.get()
            dlg.destroy()

        ttk.Button(
            dlg, text=self.tr("editor_spellcheck_start", "Начать проверку"), command=ok
        ).pack(pady=10)
        dlg.wait_window()
        if not res[0]:
            return

        spell = SpellChecker(language=res[0])
        issues = []
        for i, e in enumerate(self.entries, 1):
            k, v = e["key"], e["value"]
            if not v.strip():
                continue
            words = re.findall(r"\b\w+\b", v)
            miss = []
            for w in words:
                if len(w) < 2 or w.startswith("<") or w.startswith("["):
                    continue
                if spell.unknown([w.lower()]):
                    miss.append((w, spell.correction(w.lower())))
            if miss:
                issues.append(
                    f"Строка {i}: '{k}'\n  "
                    + ", ".join(f"'{w}'→'{s}'" if s else f"'{w}'" for w, s in miss[:3])
                )

        if not issues:
            messagebox.showinfo(
                self.tr("editor_spellcheck", "🔤 Орфография"),
                self.tr("editor_spellcheck_no_errors", "Ошибок не найдено!\nЯзык: {lang}").format(
                    lang=res[0].upper()
                ),
            )
        else:
            report = f"Найдено проблем: {len(issues)}\n\n" + "\n\n".join(issues[:15])
            if len(issues) > 15:
                report += f"\n\n... и ещё {len(issues) - 15}"
            messagebox.showwarning(self.tr("editor_spellcheck_title", "🔤 Орфография"), report)

    def _show_diff_view(self):
        import difflib

        dlg = tk.Toplevel(self.dialog)
        dlg.title(self.tr("editor_diff", "🔀 Diff"))
        dlg.geometry("950x650")
        dlg.transient(self.dialog)

        hf = ttk.Frame(dlg)
        hf.pack(fill="x", padx=10, pady=5)
        ttk.Label(
            hf,
            text=self.tr("editor_diff_title", "Сравнение с оригиналом"),
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")
        self.diff_count_label = ttk.Label(hf, text=" ", font=("Segoe UI", 10), foreground="gray")
        self.diff_count_label.pack(side="right")

        # Информационная подпись
        info_lbl = ttk.Label(
            dlg,
            text=self.tr(
                "editor_diff_info",
                "💡 Данные берутся из current value (ваш перевод) vs original_value (из XML файла)",
            ),
            font=("Segoe UI", 9),
            foreground="gray",
        )
        info_lbl.pack(fill="x", padx=10, pady=(0, 5))

        lf = ttk.Frame(dlg)
        lf.pack(fill="x", padx=10, pady=3)
        ttk.Label(
            lf,
            text=self.tr("editor_diff_deleted", "🟥 Удалено"),
            foreground="white",
            background="#ff4444",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=5)
        ttk.Label(
            lf,
            text=self.tr("editor_diff_modified", "🟨 Изменено"),
            foreground="black",
            background="#ffffaa",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=5)
        ttk.Label(
            lf,
            text=self.tr("editor_diff_added", "🟩 Добавлено"),
            foreground="white",
            background="#44cc44",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=5)

        cv = tk.Canvas(dlg)
        sb = ttk.Scrollbar(dlg, orient="vertical", command=cv.yview)
        sf = ttk.Frame(cv)
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        changed = 0
        total = sum(1 for e in self.entries if e.get("original_value", "") != e.get("value", ""))
        for e in self.entries:
            k, o, c = e["key"], e.get("original_value", ""), e.get("value", "")
            if o == c:
                continue
            changed += 1
            frm = ttk.LabelFrame(sf, text=f"🔑 {k}", padding=5)
            frm.pack(fill="x", padx=10, pady=5)

            diff = list(difflib.ndiff(o or "", c or ""))
            orig_t, curr_t = "", ""
            orig_tags, curr_tags = [], []
            pos_o, pos_c = 0, 0

            for line in diff:
                txt = line[2:]
                if line.startswith("  "):
                    orig_t += txt
                    curr_t += txt
                    orig_tags.append(("unchanged", pos_o, pos_o + len(txt)))
                    curr_tags.append(("unchanged", pos_c, pos_c + len(txt)))
                    pos_o += len(txt)
                    pos_c += len(txt)
                elif line.startswith("- "):
                    orig_t += txt
                    orig_tags.append(("deleted", pos_o, pos_o + len(txt)))
                    pos_o += len(txt)
                elif line.startswith("+ "):
                    curr_t += txt
                    curr_tags.append(("added", pos_c, pos_c + len(txt)))
                    pos_c += len(txt)

            orig_text_widget = tk.Text(
                frm, height=3, wrap="word", font=("Consolas", 9), bg="#f9f9f9"
            )
            orig_text_widget.pack(fill="x", pady=(0, 5))
            curr_text_widget = tk.Text(
                frm, height=3, wrap="word", font=("Consolas", 9), bg="#f0f8ff"
            )
            curr_text_widget.pack(fill="x")
            for tag, cfg in {
                "deleted": ("#ffcccc", "#cc0000"),
                "added": ("#ccffcc", "#006600"),
                "unchanged": ("white", "black"),
            }.items():
                orig_text_widget.tag_configure(tag, background=cfg[0], foreground=cfg[1])
                curr_text_widget.tag_configure(tag, background=cfg[0], foreground=cfg[1])
            orig_text_widget.insert("end", orig_t)
            curr_text_widget.insert("end", curr_t)
            for tag, s, e in orig_tags:
                orig_text_widget.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")
            for tag, s, e in curr_tags:
                curr_text_widget.tag_add(tag, f"1.0+{s}c", f"1.0+{e}c")
            orig_text_widget.config(state="disabled")
            curr_text_widget.config(state="disabled")
            self.diff_count_label.config(text=f"{changed}/{total}")

        if changed == 0:
            ttk.Label(
                sf, text=self.tr("editor_diff_no_changes", "Нет изменений"), font=("Segoe UI", 12)
            ).pack(pady=50)
        ttk.Button(dlg, text=self.tr("editor_close", "✖️ Закрыть"), command=dlg.destroy).pack(
            pady=10
        )

    def _show_glossary(self):
        """Показать глоссарий (вынесено в отдельный диалог)"""
        from gui.dialogs.glossary_viewer_dialog import GlossaryViewerDialog
        from config.config_manager import get_config_manager

        target_language = get_config_manager().get("target_language", "Russian")
        GlossaryViewerDialog(self.dialog, editor=self, target_language=target_language)

    def _show_file_history(self):
        """Показать историю версий (вынесено в отдельный диалог)"""
        from gui.dialogs.file_history_dialog import FileHistoryDialog
        from config.config_manager import get_config_manager

        target_language = get_config_manager().get("target_language", "Russian")
        FileHistoryDialog(self.dialog, self.file_path, editor=self, target_language=target_language)

    def _show_suggestions(self):
        """Показать подсказки перевода (вынесено в отдельный диалог)"""
        from gui.dialogs.suggestions_dialog import SuggestionsDialog
        from config.config_manager import get_config_manager

        target_language = get_config_manager().get("target_language", "Russian")
        SuggestionsDialog(self.dialog, self.entries, self.file_path, editor=self, target_language=target_language)

    def _show_glossary_menu(self, event):
        """Показывает контекстное меню глоссария"""
        # Показываем меню только если есть выделенный текст
        try:
            selected = self.value_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected and selected.strip():
                self._glossary_menu.post(event.x_root, event.y_root)
        except tk.TclError:
            # Нет выделения
            pass

    def _add_selection_to_glossary(self):
        """Добавляет выделенный текст в глоссарий"""
        # Получаем выделенный текст
        try:
            selected_text = self.value_text.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            # Нет выделения
            from tkinter import messagebox
            messagebox.showwarning(
                "Внимание",
                "Выделите текст для добавления в глоссарий"
            )
            return

        if not selected_text or not selected_text.strip():
            return

        selected_text = selected_text.strip()

        # Получаем ключ из выбранного элемента дерева
        key = ""
        sel = self.tree.selection()
        if sel:
            item = self.tree.item(sel[0])
            key = item["values"][0] if item["values"] else ""

        if not key:
            # Если нет ключа, используем выделенный текст как ключ
            key = selected_text

# Получаем базу данных глоссария
        try:
            from config.config_manager import get_config_manager
            from gui.gui_i18n import tr
            target_lang = get_config_manager().get("target_language", "Russian")
            db = get_translation_db(target_lang)
            if not db:
                from tkinter import messagebox
                messagebox.showerror(tr("glossary_db_unavailable", "Ошибка"), tr("glossary_db_unavailable", "База данных глоссария недоступна"))
                return

            # Добавляем в глоссарий с категорией "user"
            db.add_glossary_term(key, selected_text, category="user", target_language=target_lang)
            
            from tkinter import messagebox
            messagebox.showinfo(
                tr("editor_success", "Готово"),
                f"Термин '{key}'\nс переводом '{selected_text}'\nдобавлен в глоссарий (категория: user)"
            )
            
            # Если есть другие открытые окна глоссария, обновляем их
            self._notify_glossary_updated()

        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(tr("glossary_add_failed", "Ошибка"), tr("glossary_add_failed", f"Не удалось добавить в глоссарий:\n{e}"))

    def _notify_glossary_updated(self):
        """Уведомляет другие окна об обновлении глоссария"""
        try:
            self.dialog.event_generate("<<GlossaryUpdated>>")
        except Exception:
            pass

    from gui.tabs.editor.editor_file_browser import TranslationEditorTab  # noqa: E402, F401
    from gui.tabs.editor.editor_toolbar import WrappingToolbar  # noqa: E402, F401
