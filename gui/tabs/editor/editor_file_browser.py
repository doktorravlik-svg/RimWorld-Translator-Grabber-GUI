# gui/tabs/editor/editor_file_browser.py
"""
Вкладка выбора файлов и папок переводов.

Отвечает за:
- Выбор файла/папки переводов
- Сканирование папки модов
- Отображение списка файлов переводов с фильтрацией по версии
- Открытие диалога редактиирования

Вынесено из gui_translation_editor.py для разделения ответственности.
"""

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from gui.components.gui_file_colors import FILE_COLORS, FileColorMarker
from gui.constants import (
    PAD_BTN_X,
    PAD_ENTRY_X,
    PAD_FRAME_X,
    PAD_FRAME_Y,
    PAD_LABEL_X,
    PAD_TREE_X,
    PAD_TREE_Y,
    PAD_X,
    PAD_Y,
    PROGRESS_BOOTSTYLES,
)
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip

# Абсолютный путь к директории проекта
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, "gui_config.json")

# Импортируем диалог редактирования (будет импортирован динамически для избежания циклических зависимостей)


class TranslationEditorTab(ttk.Frame):
    """Вкладка для выбора и сканирования файлов переводов"""

    def __init__(
        self, parent, mods_folder: str = "", on_path_change_callback=None, log_callback=None
    ):
        super().__init__(parent)
        self.mods_folder = mods_folder
        self.color_marker = FileColorMarker()
        self.config = self._load_config()
        self.on_path_change_callback = on_path_change_callback
        self.log_callback = log_callback  # ✅ НОВОЕ: callback для логирования
        self._progress_updater = None
        self.editor_search_var = tk.StringVar()
        self._editor_filter_debounce_timer = None  # Debounce таймер
        self._all_editor_items = []  # Все элементы дерева для фильтрации
        self._setup_ui()

        # ✅ НОВОЕ: Автоматически сканируем папку модов при загрузке вкладки
        if self.mods_folder and os.path.exists(self.mods_folder):
            # Запускаем сканирование после отрисовки UI
            self.after(500, lambda: self._scan_folder(self.mods_folder))
            self.log(f"Авто-сканирование: {self.mods_folder}")

    def log(self, msg):
        """Логирование через callback или fallback в print"""
        if self.log_callback:
            try:
                self.log_callback(f"[Editor] {msg}")
            except (AttributeError, Exception):
                # Callback может быть недоступен во время __init__
                print(f"[Editor] {msg}")
        else:
            print(f"[Editor] {msg}")

    def _load_config(self):
        """Загрузить конфигурацию"""
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"editor": {"last_edited_files": [], "auto_save": True}}

    def _save_config(self, cfg):
        """Сохранить конфигурацию"""
        try:
            from config.config_manager import get_config_manager

            get_config_manager().update(cfg)
        except Exception as e:
            self.log(f"Не удалось сохранить конфиг: {e}")

    def _get_last_files(self):
        """Получить список последних открытых файлов"""
        return self.config.get("editor", {}).get("last_edited_files", [])

    def _add_to_history(self, fp):
        """Добавить файл в историю"""
        lf = self._get_last_files()
        if fp in lf:
            lf.remove(fp)
        lf.insert(0, fp)
        lf = lf[:10]
        self.config.setdefault("editor", {})["last_edited_files"] = lf
        self._save_config(self.config)
        if hasattr(self, "last_files_combo"):
            self.last_files_combo["values"] = lf

    def _setup_ui(self):
        """Настроить интерфейс"""
        # ── Выбор файла ──
        sf = ttk.LabelFrame(self, text=tr("editor_file_selection", "📂 Выбор файла перевода"))
        sf.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(sf, textvariable=self.file_var, width=50)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=PAD_X)
        ToolTip(self.file_entry, "Путь к файлу перевода")

        # ✅ НОВОЕ: Группа кнопок выбора в одном меню
        browse_btn = ttk.Menubutton(sf, text="📂 Выбрать ▾", width=14)
        browse_menu = tk.Menu(browse_btn, tearoff=0)
        browse_menu.add_command(label="📂 Обзор файла...", command=self._browse_file)
        browse_menu.add_command(label="📁 Открыть папку...", command=self._browse_folder)
        browse_menu.add_command(label="📁 Выбрать из модов...", command=self._browse_from_mods)
        browse_btn.configure(menu=browse_menu)
        browse_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(browse_btn, "Выбрать файл или папку переводов")

        # ── Версия игры ──
        version_frame = ttk.Frame(sf)
        version_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)

        ttk.Label(version_frame, text="Версия:").pack(side="left", padx=PAD_LABEL_X)
        self.game_version_var = tk.StringVar(value="Все версии")
        # ✅ ИСПРАВЛЕНО: Добавлен "Common" — файлы без папки версии
        # По wiki RimWorld: Languages должны быть в корне мода или Common, НЕ в папках версий
        self.game_version_combo = ttk.Combobox(
            version_frame,
            textvariable=self.game_version_var,
            values=[
                "Все версии",
                "Common (без версии)",
                "1.6",
                "1.5",
                "1.4",
                "1.3",
                "1.2",
                "1.1",
                "1.0",
            ],
            width=15,
            state="readonly",
        )
        self.game_version_combo.pack(side="left", padx=PAD_X)
        ToolTip(self.game_version_combo, "Фильтр по версии RimWorld")
        self.game_version_combo.bind("<<ComboboxSelected>>", self._on_version_change)

        self.show_versions_var = tk.BooleanVar(value=True)
        chk_versions = ttk.Checkbutton(
            version_frame,
            text="Показывать версии",
            variable=self.show_versions_var,
            command=self._on_show_versions_change,
        )
        chk_versions.pack(side="left", padx=PAD_X)
        ToolTip(chk_versions, "Включить/отключить фильтрацию по версии")

        # ── Последние файлы ──
        lf = self._get_last_files()
        if lf:
            ttk.Label(sf, text="🕐 Последние:").pack(side="left", padx=(10, 2))
            self.last_files_var = tk.StringVar()
            self.last_files_combo = ttk.Combobox(
                sf, textvariable=self.last_files_var, values=lf, width=40, state="readonly"
            )
            self.last_files_combo.pack(side="left", fill="x", expand=True, padx=PAD_X)
            self.last_files_combo.bind("<<ComboboxSelected>>", self._on_last_file_selected)
            btn_open_last = ttk.Button(sf, text="🕐 Открыть", command=self._open_last_file)
            btn_open_last.pack(side="left", padx=PAD_BTN_X)
            ToolTip(btn_open_last, "Открыть последний файл")

        # ── Прогресс сканирования ──
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_Y)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="indeterminate",
            bootstyle=PROGRESS_BOOTSTYLES.get("integrity", "info-striped"),
        )
        self.progress_bar.pack(fill="x", padx=PAD_X, pady=3)
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(anchor="w", padx=PAD_X, pady=(0, 3))
        progress_frame.pack_forget()  # Скрыт по умолчанию

        # ── Кнопки действий ──
        bf = ttk.Frame(self)
        bf.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_Y)
        btn_editor = ttk.Button(
            bf,
            text=tr("editor_btn_open_editor", "✏️ Открыть редактор"),
            command=self._open_editor,
            bootstyle="success",
        )
        btn_editor.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_editor, "Открыть редактор переводов")

        btn_refresh = ttk.Button(
            bf,
            text=tr("editor_btn_refresh", "🔄 Обновить"),
            command=self._refresh,
            bootstyle="info",
        )
        btn_refresh.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_refresh, "Обновить список файлов переводов")

        # ── Поиск ──
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_Y)
        ttk.Label(search_frame, text="🔍 Поиск:").pack(side="left", padx=PAD_LABEL_X)
        self.editor_search_var = tk.StringVar()
        self.editor_search_entry = ttk.Entry(
            search_frame, textvariable=self.editor_search_var, bootstyle="info"
        )
        self.editor_search_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        self.editor_search_entry.bind("<KeyRelease>", self._filter_editor_files)
        ToolTip(self.editor_search_entry, "Введите текст для фильтрации файлов")
        btn_clear_search = ttk.Button(
            search_frame,
            text="✕",
            width=3,
            command=self._clear_editor_search,
            bootstyle="secondary",
        )
        btn_clear_search.pack(side="left")
        ToolTip(btn_clear_search, "Очистить поиск")

        # ── Легенда цветов ──
        legend = ttk.LabelFrame(self, text=tr("editor_color_legend", "🎨 Легенда цветов"))
        legend.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_Y)
        for c, d in [
            (FILE_COLORS["complete"], tr("editor_legend_complete", "✅ Полностью переведён")),
            (FILE_COLORS["partial"], tr("editor_legend_partial", "⚠️ Частичный перевод")),
            (FILE_COLORS["error"], tr("editor_legend_error", "❌ Ошибка в файле")),
            (FILE_COLORS["empty"], tr("editor_legend_empty", "⬜ Не переведён")),
            (FILE_COLORS["missing"], tr("editor_legend_missing", "➖ Файл отсутствует")),
        ]:
            ttk.Label(legend, text=d, foreground=c).pack(side="left", padx=PAD_X)

        # ── Статистика ──
        stats_frame = ttk.LabelFrame(self, text=tr("editor_stats", "📊 Статистика"))
        stats_frame.pack(fill="x", padx=PAD_FRAME_X, pady=PAD_Y)
        self.stats_label = ttk.Label(
            stats_frame, text=tr("editor_not_scanned", "Сканирование не проводилось")
        )
        self.stats_label.pack(anchor="w", padx=PAD_X, pady=PAD_Y)

        # ── Список файлов ──
        list_f = ttk.LabelFrame(self, text=tr("editor_translation_files", "📋 Файлы переводов"))
        list_f.pack(fill="both", expand=True, padx=PAD_TREE_X, pady=PAD_TREE_Y)

        from gui.components.scrollable_tree import ScrollableTree

        cols = ("path", "entries", "status")
        self.tree_widget = ScrollableTree(
            list_f,
            columns=cols,
            headings={
                "path": tr("editor_file_list_path_col", "Путь"),
                "entries": tr("editor_file_list_entries_col", "Записей"),
                "status": tr("editor_file_list_status_col", "Статус"),
            },
            column_widths={"path": 350, "entries": 80, "status": 100},
            selectmode="browse",
        )
        self.tree_widget.pack(fill="both", expand=True)

        for s, c in FILE_COLORS.items():
            self.tree_widget.tree.tag_configure(s, background=c, foreground="white")

        # Привязки
        self.tree_widget.tree.bind("<<TreeviewSelect>>", self._on_file_select)
        self.tree_widget.tree.bind("<Double-1>", self._on_double_click)
        self.tree_widget.tree.bind("<Button-3>", self._show_context_menu)

        # Псевдоним для обратной совместимости
        self.tree = self.tree_widget.tree

    # ═══════════════════════════════════════════
    # Обработчики событий дерева
    # ═══════════════════════════════════════════

    def _on_file_select(self, event):
        """Обновляет file_var при выделении файла"""
        sel = self.tree.selection()
        if sel:
            fp = self.tree.item(sel[0]).get("text", "")
            if fp:
                self.file_var.set(fp)
                self.log(f"Файл выделен: {fp}")
                # ✅ ИСПРАВЛЕНО: Убрано авто-открытие редактора при выделении
                # Редактор открывается двойным кликом или из контекстного меню

    def _show_context_menu(self, event):
        """Контекстное меню для файла"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            m = tk.Menu(self, tearoff=0)
            m.add_command(
                label=tr("editor_ctx_open", "✏️ Открыть в редакторе"),
                command=self._open_selected_file,
            )
            m.add_separator()
            m.add_command(
                label=tr("editor_ctx_copy_path", "📋 Копировать путь"),
                command=self._copy_selected_path,
            )
            m.add_command(
                label=tr("editor_ctx_open_folder", "📂 Открыть папку"),
                command=self._open_selected_folder,
            )
            m.add_separator()
            m.add_command(
                label=tr("editor_ctx_info", "📊 Информация"), command=self._show_file_info
            )
            m.add_separator()
            m.add_command(
                label=tr("editor_ctx_refresh_list", "🔄 Обновить список"),
                command=self._refresh,
            )
            m.post(event.x_root, event.y_root)

    # ═══════════════════════════════════════════
    # Операции с файлами
    # ═══════════════════════════════════════════

    def _open_selected_file(self):
        """Открыть выбранный файл в редакторе"""
        sel = self.tree.selection()
        self.log(f"_open_selected_file: выделено={sel}")
        if not sel:
            return
        fp = self.tree.item(sel[0]).get("text", "")
        self.log(f"  Выбранный файл: '{fp}'")
        if fp and os.path.exists(fp):
            self.file_var.set(fp)
            self.log("✅ Файл установлен, открываю редактор")
            self._open_editor()
        else:
            self.log(f"❌ Файл не найден или не существует: '{fp}'")
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_file_not_found", "Файл не найден:\n{path}").format(path=fp),
            )

    def _copy_selected_path(self):
        """Копировать путь выбранного файла"""
        sel = self.tree.selection()
        if not sel:
            return
        fp = self.tree.item(sel[0]).get("text", "")
        if fp:
            self.clipboard_clear()
            self.clipboard_append(fp)
            self.log(f"Путь скопирован: {fp}")

    def _open_selected_folder(self):
        """Открыть папку выбранного файла"""
        sel = self.tree.selection()
        if not sel:
            return
        fp = self.tree.item(sel[0]).get("text", "")
        if fp and os.path.exists(fp):
            folder = os.path.dirname(fp)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        else:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_file_not_found", "Файл не найден:\n{path}").format(path=fp),
            )

    def _show_file_info(self):
        """Показать информацию о файле"""
        sel = self.tree.selection()
        if not sel:
            return
        fp = self.tree.item(sel[0]).get("text", "")
        vals = self.tree.item(sel[0])["values"]
        if not fp:
            return
        lines = [f"Путь: {fp}", f"Записей: {vals[1]}", f"Статус: {vals[2]}"]
        if os.path.exists(fp):
            lines.append(f"Размер: {os.path.getsize(fp)} байт")
            lines.append(
                f"Изменён: {datetime.fromtimestamp(os.path.getmtime(fp)).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        messagebox.showinfo(self.tr("editor_file_info", "Информация о файле"), "\n".join(lines))

    def _browse_file(self):
        """Выбрать XML файл через диалог"""
        fp = filedialog.askopenfilename(
            title=self.tr("editor_select_xml_file", "Выберите XML файл перевода"),
            filetypes=[("XML файлы", "*.xml")],
        )
        if fp:
            self.file_var.set(fp)
            self._open_editor()

    def _browse_folder(self):
        """Открыть всю папку с переводами (Keyed)"""
        folder = filedialog.askdirectory(
            title=self.tr("editor_select_keyed_folder", "Выберите папку Keyed с переводами"),
            initialdir=self.mods_folder,
        )
        if folder:
            self.log(f"Выбрана папка: {folder}")
            self._load_folder_with_filters(folder)

    def _browse_from_mods(self):
        """Выбрать папку модов и загрузить переводы"""
        if not self.mods_folder or not os.path.exists(self.mods_folder):
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_specify_mods_folder", "Укажите папку с модами"),
            )
            return

        target_lang = self._get_target_language()
        self.log(f"Целевой язык: {target_lang}")

        folder = filedialog.askdirectory(
            title=self.tr("editor_select_languages_folder", "Выберите папку Languages"),
            initialdir=self.mods_folder,
        )
        if folder:
            self.mods_folder = folder
            from config.paths_config import get_paths_config

            get_paths_config().set_mods_path(folder, save=True)
            if self.on_path_change_callback:
                self.on_path_change_callback("mods", folder)
            self._scan_language_folder(folder, target_lang)

    # ═══════════════════════════════════════════
    # Загрузка и сканирование
    # ═══════════════════════════════════════════

    def _load_folder_with_filters(self, folder):
        """Загружает папку с учетом фильтров по версии"""
        self.log(f"Загрузка папки: {folder}")

        if not os.path.exists(folder):
            messagebox.showerror(
                self.tr("editor_error", "Ошибка"),
                self.tr("editor_folder_not_found", "Папка не найдена:\n{path}").format(path=folder),
            )
            return

        xml_files = []
        for root, dirs, files in os.walk(folder):
            if not self._should_include_version(root):
                continue
            for fn in files:
                if fn.endswith(".xml"):
                    xml_files.append(os.path.join(root, fn))

        if not xml_files:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_no_xml_files", "В папке не найдено XML файлов:\n{path}").format(
                    path=folder
                ),
            )
            return

        self._load_folder(folder, xml_files)

    def _load_folder(self, folder, xml_files=None):
        """Загружает ВСЕ XML файлы из папки Keyed"""
        self.log(f"Загрузка папки: {folder}")

        if not os.path.exists(folder):
            messagebox.showerror(
                self.tr("editor_error", "Ошибка"),
                self.tr("editor_folder_not_found", "Папка не найдена:\n{path}").format(path=folder),
            )
            return

        if xml_files is None:
            xml_files = []
            import xml.etree.ElementTree as ET

            for root, dirs, files in os.walk(folder):
                if not self._should_include_version(root):
                    continue
                for fn in files:
                    if fn.endswith(".xml"):
                        xml_files.append(os.path.join(root, fn))

        if not xml_files:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_no_xml_files", "В папке не найдено XML файлов:\n{path}").format(
                    path=folder
                ),
            )
            return

        self.log(f"Найдено {len(xml_files)} файлов перевода")

        import xml.etree.ElementTree as ET

        all_entries = []
        file_map = {}

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                file_name = os.path.basename(xml_file)
                rel_path = os.path.relpath(xml_file, folder)

                for child in root:
                    key = child.tag
                    value = child.text or ""
                    status = "complete" if value.strip() else "empty"
                    all_entries.append(
                        {
                            "key": key,
                            "value": value,
                            "original_value": value,
                            "status": status,
                            "file": rel_path,
                        }
                    )
                    file_map[key] = rel_path

                self.log(f"  Загружен {file_name}: {len(list(root))} записей")
            except Exception as e:
                self.log(f"  ❌ Ошибка загрузки {xml_file}: {e}")

        if all_entries:
            # ✅ В TranslationEditorTab мы только логируем результат
            # entries/file_map/save_indicator/header_title — атрибуты TranslationEditorDialog

            self.log(f"✅ Загружено {len(all_entries)} записей из {len(xml_files)} файлов")

            messagebox.showinfo(
                self.tr("editor_success", "Успех"),
                self.tr(
                    "editor_folder_loaded", "Загружено {count} записей из {files} файлов"
                ).format(
                    count=len(all_entries),
                    files=len(xml_files),
                ),
            )
        else:
            messagebox.showwarning(
                self.tr("editor_warning", "Предупреждение"),
                self.tr("editor_no_entries", "Не удалось загрузить записи из файлов"),
            )

    def _get_target_language(self) -> str:
        """Получить целевой язык из настроек"""
        try:
            target_lang = self.config.get("target_language", "Russian")
            lang_map = {
                "Russian": "Russian",
                "English": "English",
                "German": "German",
                "French": "French",
                "Spanish": "Spanish",
                "Italian": "Italian",
                "Polish": "Polish",
                "Portuguese": "PortugueseBrazilian",
                "PortugueseBrazilian": "PortugueseBrazilian",
                "Chinese": "ChineseSimplified",
                "ChineseSimplified": "ChineseSimplified",
                "ChineseTraditional": "ChineseTraditional",
                "Japanese": "Japanese",
                "Korean": "Korean",
                "Thai": "Thai",
                "Vietnamese": "Vietnamese",
                "Czech": "Czech",
                "Dutch": "Dutch",
                "Swedish": "Swedish",
                "Turkish": "Turkish",
                "Ukrainian": "Ukrainian",
                "Hungarian": "Hungarian",
                "Romanian": "Romanian",
                "Catalan": "Catalan",
                "Arabic": "Arabic",
                "Finnish": "Finnish",
                "Norwegian": "Norwegian",
                "Danish": "Danish",
            }
            return lang_map.get(target_lang, target_lang)
        except Exception:
            return "Russian"

    # ═══════════════════════════════════════════
    # Версии и языки
    # ═══════════════════════════════════════════

    def _on_version_change(self, event=None):
        """Изменение выбранной версии игры"""
        self.log(f"Выбрана версия: {self.game_version_var.get()}")
        if self.mods_folder and os.path.exists(self.mods_folder):
            target_lang = self._get_target_language()
            self._scan_language_folder(self.mods_folder, target_lang)

    def _on_show_versions_change(self):
        """Показать/скрыть версии игры"""
        show = self.show_versions_var.get()
        self.game_version_combo.config(state="readonly" if show else "disabled")
        self.log(f"Показ версий: {'включён' if show else 'выключен'}")
        if self.mods_folder and os.path.exists(self.mods_folder):
            target_lang = self._get_target_language()
            self._scan_language_folder(self.mods_folder, target_lang)

    def _should_include_version(self, path: str) -> bool:
        """Проверить нужно ли включать файл по версии

        По wiki RimWorld: Languages должны быть в корне мода или Common,
        НЕ в папках версий. Поэтому файлы без папки версии включаем всегда.
        """
        if not self.show_versions_var.get():
            return True

        selected_version = self.game_version_var.get()
        if selected_version == "Все версии":
            return True

        path_lower = path.lower()

        # ✅ ИСПРАВЛЕНО: Проверяем есть ли ВООБЩЕ какая-либо версия в пути
        has_any_version = any(
            f"/{v}/" in path_lower or f"\\{v}\\" in path_lower
            for v in ["1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "1.0"]
        )

        # Если нет версии в пути — это Common файл, включаем всегда
        if not has_any_version:
            return True

        # Если есть версия — проверяем соответствие выбранной
        if selected_version == "Common (без версии)":
            return False  # Показываем только файлы без версии

        version_patterns = [
            f"/{selected_version}/",
            f"\\{selected_version}\\",
            f"/{selected_version}\\",
            f"\\{selected_version}/",
        ]
        return any(pattern.lower() in path_lower for pattern in version_patterns)

    def _scan_language_folder(self, base_folder: str, target_lang: str):
        """Сканирует только указанный язык во всех модах"""
        self.log(f"Сканирование языка '{target_lang}' в: {base_folder}")
        self._show_progress()

        if not hasattr(self, "tree") or self.tree is None:
            self.log("❌ ОШИБКА: tree не инициализирован!")
            self._hide_progress()
            return

        def _worker():
            """Собирает данные о файлах указанного языка"""
            files_data = []
            lang_lower = target_lang.lower()

            for root, dirs, files in os.walk(base_folder):
                root_lower = root.lower()
                if "languages" not in root_lower:
                    continue
                if lang_lower not in root_lower:
                    continue
                if "keyed" not in root_lower:
                    continue

                if not self._should_include_version(root):
                    continue

                for fn in files:
                    if fn.endswith(".xml"):
                        fp = os.path.join(root, fn)
                        try:
                            import xml.etree.ElementTree as ET

                            tree = ET.parse(fp)
                            cnt = len(list(tree.getroot()))
                        except Exception:
                            cnt = 0
                        try:
                            status = self.color_marker.get_file_color_info(fp)["status"]
                        except Exception:
                            status = "default"
                        rel = os.path.relpath(fp, base_folder)
                        files_data.append((fp, rel, cnt, status))

            if self.winfo_exists():
                self.after(0, lambda: self._populate_tree(files_data))
                self.log(f"✅ Найдено {len(files_data)} файлов '{target_lang}'")

        threading.Thread(target=_worker, daemon=True).start()

    def _scan_folder(self, folder):
        """Сканирует папку в фоновом потоке"""
        self.log(f"Начало сканирования: {folder}")
        self._show_progress()

        if not hasattr(self, "tree") or self.tree is None:
            self.log("❌ ОШИБКА: tree не инициализирован перед сканированием!")
            self._hide_progress()
            return

        def _worker():
            """Собирает данные о файлах в фоне."""
            files_data = []

            for root, dirs, files in os.walk(folder):
                if "languages" not in root.lower() and "keyed" not in root.lower():
                    continue

                for fn in files:
                    if fn.endswith(".xml"):
                        fp = os.path.join(root, fn)
                        try:
                            import xml.etree.ElementTree as ET

                            cnt = len(list(ET.parse(fp).getroot()))
                        except Exception:
                            cnt = 0
                        try:
                            status = self.color_marker.get_file_color_info(fp)["status"]
                        except Exception:
                            status = "default"
                        rel = os.path.relpath(fp, folder)
                        files_data.append((fp, rel, cnt, status))

            if self.winfo_exists():
                self.after(0, lambda: self._populate_tree(files_data))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_tree(self, files_data):
        """Заполняет дерево данными (вызывается в главном потоке)"""
        if not self.winfo_exists():
            return
        if not hasattr(self, "tree") or self.tree is None:
            self.log("❌ Дерево ещё не инициализировано!")
            return

        self.log(f"_populate_tree: {len(files_data)} файлов для вставки")
        self.tree.delete(*self.tree.get_children())
        self._all_editor_items.clear()  # Очищаем список всех элементов

        # Статистика
        total_files = len(files_data)
        total_entries = sum(cnt for _, _, cnt, _ in files_data)
        status_counts = {}
        for _, _, _, status in files_data:
            status_counts[status] = status_counts.get(status, 0) + 1

        for i, (fp, rel, cnt, status) in enumerate(files_data):
            item_id = self.tree.insert(
                "", "end", text=fp, values=(rel, cnt, status), tags=(status,)
            )
            self._all_editor_items.append(item_id)  # Сохраняем для фильтрации
            if i < 3:
                self.log(f"  [{i}] {rel} ({cnt}) [{status}]")

        self.log(f"✅ Дерево обновлено: {total_files} файлов")

        # Обновить статистику
        stats_parts = [
            f"Всего файлов: {total_files}",
            f"Записей: {total_entries}",
        ]
        for status, count in sorted(status_counts.items()):
            stats_parts.append(f"{status}: {count}")
        self.stats_label.config(text=" | ".join(stats_parts))

        # Скрыть прогресс
        self._hide_progress()

    def _filter_editor_files(self, event=None):
        """Фильтрация файлов по поисковому запросу"""
        search_text = self.editor_search_var.get().lower()

        # Итерируемся по ВСЕМ элементам (не только видимым)
        for item in self._all_editor_items:
            values = self.tree.item(item, "values")
            if not values:
                continue
            path_text = values[0].lower()
            text_value = self.tree.item(item, "text").lower()
            if not search_text or search_text in path_text or search_text in text_value:
                self.tree.reattach(item, "", "end")
            else:
                self.tree.detach(item)

    def _clear_editor_search(self):
        """Очистить поиск и показать все файлы"""
        self.editor_search_var.set("")
        for item in self._all_editor_items:
            self.tree.reattach(item, "", "end")

    def _show_progress(self):
        """Показать прогресс-бар"""
        if not self.progress_bar.winfo_manager():
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
            self.progress_label.config(text="🔄 Сканирование...")
            self.progress_bar.master.pack(
                fill="x",
                padx=PAD_FRAME_X,
                pady=PAD_Y,
                before=self.winfo_children()[0] if self.winfo_children() else None,
            )

    def _hide_progress(self):
        """Скрыть прогресс-бар"""
        if self.progress_bar.winfo_manager():
            self.progress_bar.stop()
            self.progress_label.config(text="✅ Сканирование завершено")
            self.after(2000, self.progress_bar.master.pack_forget)

    # ═══════════════════════════════════════════
    # Публичные методы
    # ═══════════════════════════════════════════

    def set_mods_folder(self, folder: str):
        """Установить папку с модами и обновить список"""
        if self.mods_folder != folder:
            self.mods_folder = folder
            if os.path.exists(folder):
                self.after(200, lambda: self._scan_folder(folder))

    def _refresh(self):
        """Обновить список файлов"""
        self.log("Обновление списка файлов")
        if self.mods_folder and os.path.exists(self.mods_folder):
            self._scan_folder(self.mods_folder)

    def _on_last_file_selected(self, event=None):
        """Открыть последний файл"""
        fp = self.last_files_var.get()
        if fp and os.path.exists(fp):
            self.file_var.set(fp)
            self._open_editor()

    def _open_last_file(self):
        """Открыть последний файл из истории"""
        lf = self._get_last_files()
        if lf and os.path.exists(lf[0]):
            self.file_var.set(lf[0])
            self._open_editor()
        else:
            self.log("Нет файлов в истории")

    def _open_editor(self):
        """Открыть диалог редактирования (даже если файл не выбран)"""
        fp = self.file_var.get()

        self.log(f"🔍 _open_editor: file_var='{fp}'")

        if fp and not os.path.exists(fp):
            self.log(f"⚠️ Файл не найден: {fp}, открываю пустой редактор")
            fp = ""

        if fp:
            self.log(f"✅ Файл существует: {fp}, размер: {os.path.getsize(fp)} байт")
            self._add_to_history(fp)
        else:
            self.log("⚠️ Файл не выбран, открываю пустой редактор")

        self.log(f"📝 Открываю редактор для: '{fp or 'пустой'}'")

        from gui.tabs.editor.editor_dialog import get_editor_dialog_class

        EditorDialog = get_editor_dialog_class()
        dlg = EditorDialog(self.winfo_toplevel(), file_path=fp)

        if fp:
            self.log(f"✅ Редактор открыт с файлом: {fp}")
        else:
            self.log("⚠️ Редактор открыт без файла (пустой)")

    def _on_double_click(self, event=None):
        """Двойной клик по файлу — открыть в редакторе"""
        self._open_selected_file()
