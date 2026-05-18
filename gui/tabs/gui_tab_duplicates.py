import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from config.paths_config import get_paths_config
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


class DuplicatesTab(ttk.Frame):
    def __init__(self, parent, config, on_merge_callback=None, on_path_change_callback=None):
        super().__init__(parent)
        self.config = config
        self.on_merge_callback = on_merge_callback
        self.on_path_change_callback = on_path_change_callback
        self.merge_var = tk.BooleanVar(value=True)
        self.backup_var = tk.BooleanVar(value=True)
        self.duplicates_data = []
        self.selected_duplicates = set()
        self._progress_updater = None
        self._dup_filter_debounce_timer = None  # Debounce таймер
        self._all_dup_items = []  # Все элементы дерева для фильтрации
        self._setup_ui()

    def _setup_ui(self):
        # Row 0: Настройки — пути и опции
        opts_frame = ttk.LabelFrame(self, text=tr("duplicates_merge_options", "⚙️ Настройки"))
        opts_frame.grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )

        # Папка с модами
        mods_frame = ttk.Frame(opts_frame)
        mods_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=PAD_X, pady=PAD_Y)
        ttk.Label(mods_frame, text=tr("duplicates_mods_folder", "Папка с модами:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        self.mods_entry = ttk.Entry(mods_frame, width=60)
        self.mods_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        self.mods_entry.insert(0, get_paths_config().get_mods_path())
        ToolTip(self.mods_entry, tr("dup_tooltip_mods", "Папка с модами RimWorld для сканирования"))
        btn_browse_mods = ttk.Button(mods_frame, text="📂", command=self._browse_mods, width=3)
        btn_browse_mods.pack(side="left")
        ToolTip(btn_browse_mods, tr("dup_tooltip_browse_mods", "Выбрать папку с модами"))
        opts_frame.columnconfigure(0, weight=1)

        # Папка вывода
        output_frame = ttk.Frame(opts_frame)
        output_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=PAD_X, pady=PAD_Y)
        ttk.Label(output_frame, text=tr("duplicates_output_folder", "Папка вывода:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        self.output_entry = ttk.Entry(output_frame, width=60)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        self.output_entry.insert(0, get_paths_config().get_output_path())
        ToolTip(
            self.output_entry, tr("dup_tooltip_output", "Папка для сохранения результата слияния")
        )
        btn_browse_out = ttk.Button(output_frame, text="📂", command=self._browse_output, width=3)
        btn_browse_out.pack(side="left")
        ToolTip(btn_browse_out, tr("dup_tooltip_browse_output", "Выбрать папку вывода"))
        opts_frame.columnconfigure(1, weight=1)

        # Чекбоксы опций
        chk_frame = ttk.Frame(opts_frame)
        chk_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=PAD_X, pady=PAD_Y)
        chk_merge = ttk.Checkbutton(
            chk_frame,
            text=tr("duplicates_auto_merge", "Автоматическое слияние"),
            variable=self.merge_var,
        )
        chk_merge.pack(side="left", padx=PAD_X)
        ToolTip(chk_merge, tr("dup_tooltip_auto_merge", "Автоматически объединять дубликаты"))
        chk_backup = ttk.Checkbutton(
            chk_frame,
            text=tr("duplicates_create_backup", "Создавать резервные копии"),
            variable=self.backup_var,
        )
        chk_backup.pack(side="left", padx=PAD_X)
        ToolTip(chk_backup, tr("dup_tooltip_backup", "Создавать бэкап перед слиянием"))

        # Row 1: Кнопки действий
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=PAD_FRAME_X, pady=PAD_Y)

        btn_scan = ttk.Button(
            btn_frame,
            text=tr("duplicates_scan_button", "🔍 Найти дубликаты"),
            command=self._scan_duplicates,
            bootstyle="info",
        )
        btn_scan.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_scan, tr("dup_tooltip_scan", "Просканировать папку модов на дубликаты"))

        btn_select_all = ttk.Button(
            btn_frame,
            text=tr("duplicates_select_all", "✅ Выбрать все"),
            command=self._select_all_duplicates,
        )
        btn_select_all.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_select_all, tr("dup_tooltip_select_all", "Выбрать все группы дубликатов"))

        btn_deselect = ttk.Button(
            btn_frame,
            text=tr("duplicates_deselect_all", "☐ Снять все"),
            command=self._deselect_all_duplicates,
        )
        btn_deselect.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_deselect, tr("dup_tooltip_deselect", "Снять выбор со всех групп"))

        btn_merge = ttk.Button(
            btn_frame,
            text=tr("duplicates_start_merge", "🚀 Запустить слияние"),
            command=self._on_merge,
            bootstyle="success",
        )
        btn_merge.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_merge, tr("dup_tooltip_merge", "Слить выбранные группы дубликатов"))

        btn_help = ttk.Button(
            btn_frame,
            text=tr("duplicates_help", "❓ Помощь"),
            command=self._show_help,
            bootstyle="secondary",
        )
        btn_help.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_help, tr("dup_tooltip_help", "Открыть справку по вкладке «Дубликаты»"))

        # Row 2: Прогресс (grid_remove по умолчанию)
        progress_frame = ttk.Frame(self)
        progress_frame.grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_Y
        )
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            bootstyle=PROGRESS_BOOTSTYLES["duplicates"],
        )
        self.progress_bar.pack(fill="x", padx=PAD_X, pady=3)
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack(anchor="w", padx=PAD_X, pady=(0, 3))
        progress_frame.grid_remove()  # Скрыт по умолчанию

        # Row 3: Поиск
        search_frame = ttk.Frame(self)
        search_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_Y)
        ttk.Label(search_frame, text="🔍 Поиск:").pack(side="left", padx=PAD_LABEL_X)
        self.dup_search_var = tk.StringVar()
        self.dup_search_entry = ttk.Entry(
            search_frame, textvariable=self.dup_search_var, bootstyle="info"
        )
        self.dup_search_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        # ✅ ИСПРАВЛЕНО: Debounce для поиска (300мс задержка)
        self._dup_filter_debounce_timer = None
        self.dup_search_entry.bind("<KeyRelease>", self._on_dup_filter_debounced)
        ToolTip(
            self.dup_search_entry,
            tr("dup_tooltip_search", "Введите текст для фильтрации дубликатов"),
        )
        btn_clear = ttk.Button(
            search_frame, text="✕", width=3, command=self._clear_search, bootstyle="secondary"
        )
        btn_clear.pack(side="left")
        ToolTip(btn_clear, tr("dup_tooltip_clear", "Очистить поиск"))

        # Row 4: Найденные дубликаты (дерево)
        preview_frame = ttk.LabelFrame(self, text=tr("duplicates_found", "📋 Найденные дубликаты"))
        preview_frame.grid(
            row=4, column=0, columnspan=3, padx=PAD_TREE_X, pady=PAD_TREE_Y, sticky="nsew"
        )

        from gui.components.scrollable_tree import ScrollableTree

        columns = ("select", "group", "files", "size")
        self.dup_tree_widget = ScrollableTree(
            preview_frame,
            columns=columns,
            headings={
                "select": tr("duplicates_col_select", "✓"),
                "group": tr("duplicates_col_group", "Группа дубликатов"),
                "files": tr("duplicates_col_files", "Файлы"),
                "size": tr("duplicates_col_size", "Размер"),
            },
            column_widths={"select": 30, "group": 200, "files": 350, "size": 80},
            column_mins={"select": 30},
            height=10,
            selectmode="browse",
        )
        self.dup_tree_widget.pack(fill="both", expand=True)
        self.dup_tree_widget.tree.column("select", stretch=False)
        self.dup_tree_widget.tree.tag_configure(
            "duplicate", background="#fff3cd", foreground="black"
        )
        self.dup_tree_widget.tree.bind("<Button-1>", self._on_dup_click)
        self.dup_tree_widget.tree.bind(
            "<Button-3>", self._show_dup_context_menu
        )  # Контекстное меню
        self.dup_tree = self.dup_tree_widget.tree

        # Row 5: Статистика
        stats_frame = ttk.LabelFrame(self, text=tr("duplicates_stats", "📊 Статистика"))
        stats_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_Y)
        self.stats_label = ttk.Label(
            stats_frame, text=tr("duplicates_not_found", "Дубликаты не найдены")
        )
        self.stats_label.pack(anchor="w", padx=PAD_X, pady=PAD_Y)

        # Row 6: Результаты слияния (лог)
        result_frame = ttk.LabelFrame(
            self, text=tr("duplicates_merge_results", "📝 Результаты слияния")
        )
        result_frame.grid(row=6, column=0, columnspan=3, padx=PAD_X, pady=PAD_Y, sticky="nsew")
        self.result_text = tk.Text(result_frame, height=8, wrap="word")
        vsb2 = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=vsb2.set)
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=PAD_X, pady=PAD_Y)
        vsb2.grid(row=0, column=1, sticky="ns", padx=(0, PAD_X), pady=PAD_Y)
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        # Настройка растягивания
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(4, weight=2)  # Дерево занимает больше места
        self.rowconfigure(6, weight=1)  # Лог занимает оставшееся место

    def _browse_mods(self):
        folder = filedialog.askdirectory(
            title=tr("duplicates_select_mods_folder", "Выберите папку с модами")
        )
        if folder:
            self.mods_entry.delete(0, tk.END)
            self.mods_entry.insert(0, folder)
            get_paths_config().set_mods_path(folder, save=True)
            if self.on_path_change_callback:
                self.on_path_change_callback("mods", folder)

    def _browse_output(self):
        folder = filedialog.askdirectory(
            title=tr("duplicates_select_output_folder", "Выберите папку вывода")
        )
        if folder:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            get_paths_config().set_output_path(folder, save=True)
            if self.on_path_change_callback:
                self.on_path_change_callback("output", folder)

    def _scan_duplicates(self):
        mods_folder = self.mods_entry.get()
        if not mods_folder or not os.path.exists(mods_folder):
            messagebox.showwarning(
                tr("duplicates_warning", "Предупреждение"),
                tr("duplicates_select_mods_folder_warning", "Выберите существующую папку с модами"),
            )
            return

        # Показать прогресс
        self._show_progress()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.progress_label.config(text=tr("duplicates_scanning", "Сканирование..."))

        self.log(tr("duplicates_scanning", "Сканирование папки: ") + mods_folder)
        self.dup_tree.delete(*self.dup_tree.get_children())
        self._all_dup_items.clear()  # Очищаем список всех элементов
        self.duplicates_data.clear()
        self.selected_duplicates.clear()

        thread = threading.Thread(
            target=self._scan_duplicates_worker,
            args=(mods_folder,),
            daemon=True,
        )
        thread.start()

    def _scan_duplicates_worker(self, mods_folder):
        """Фоновое сканирование дубликатов"""
        try:
            from duplicates.duplicate_merger import find_duplicates, scan_translations

            # Собираем все папки Languages из всех модов
            all_languages_data = {}

            # Сканируем папку модов или конкретный мод
            if os.path.exists(os.path.join(mods_folder, "About")) or os.path.exists(
                os.path.join(mods_folder, "Defs")
            ):
                # Это конкретный мод - сканируем его Languages
                lang_folders = self._collect_language_folders(mods_folder)
            else:
                # Это папка с модами - сканируем каждый мод
                lang_folders = []
                try:
                    for item in os.listdir(mods_folder):
                        mod_path = os.path.join(mods_folder, item)
                        if os.path.isdir(mod_path):
                            lang_folders.extend(self._collect_language_folders(mod_path))
                except Exception:
                    self.after(0, lambda: self.log(f"⚠️ Ошибка чтения папки модов: {ex}"))

            if not lang_folders:
                self.after(0, lambda: self.log("⚠️ Папки Languages не найдены"))
                self.after(0, lambda: self._populate_duplicates_results({}, {}, 0, 0))
                return

            # Сканируем каждую папку Languages
            for lang_folder, mod_path in lang_folders:
                lang_data = scan_translations(lang_folder, mod_path=mod_path)
                # Объединяем данные
                for tag, entries in lang_data.items():
                    if tag not in all_languages_data:
                        all_languages_data[tag] = []
                    all_languages_data[tag].extend(entries)

            translations = all_languages_data
            duplicates = find_duplicates(translations)
            total_keys = len(translations)
            dup_count = len(duplicates)

            # Безопасное обновление UI через after()
            self.after(
                0,
                lambda: self._populate_duplicates_results(
                    translations, duplicates, total_keys, dup_count
                ),
            )
        except Exception as e:
            error_msg = f"❌ Ошибка сканирования: {e}"
            import traceback

            trace_msg = traceback.format_exc()

            self.after(0, lambda: self.log(error_msg))
            self.after(0, lambda: self.log(trace_msg))
            self.after(0, lambda: self.finish_progress(success=False))

    def _collect_language_folders(self, mod_path):
        """Собирает все папки Languages из мода"""

        lang_folders = []
        # Ищем все языки (не только Russian)
        try:
            langs_base = os.path.join(mod_path, "Languages")
            if os.path.exists(langs_base):
                for lang in os.listdir(langs_base):
                    lang_path = os.path.join(langs_base, lang)
                    if os.path.isdir(lang_path):
                        lang_folders.append((lang_path, mod_path))  # ✅ Возвращаем кортеж

            # Также ищем в версионных папках
            for v in ["1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "Common"]:
                v_langs = os.path.join(mod_path, v, "Languages")
                if os.path.exists(v_langs):
                    for lang in os.listdir(v_langs):
                        lang_path = os.path.join(v_langs, lang)
                        if os.path.isdir(lang_path):
                            lang_folders.append((lang_path, mod_path))  # ✅ Возвращаем кортеж
        except Exception:
            pass

        return lang_folders

    def _populate_duplicates_results(self, translations, duplicates, total_keys, dup_count):
        """Заполнение дерева результатами (вызывается в main thread)"""
        # Остановить анимацию прогресса
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = 100
        self.progress_label.config(text=tr("duplicates_scan_complete", " Сканирование завершено"))
        self.after(2000, self._hide_progress)

        self.log(tr("duplicates_scanned_tags", "Просканировано тегов: ") + str(total_keys))

        if dup_count == 0:
            self.log(tr("duplicates_not_found_log", "Дубликаты не найдены"))
            self._update_stats()
            return

        for tag, entries in duplicates.items():
            # ✅ СОХРАНЯЕМ mod_path и lang вместе с rel_path
            unique_files = list(
                set(
                    (
                        e["rel_path"],
                        e.get("mod_path", ""),
                        e.get("lang", "Russian"),  # ✅ Извлекаем язык
                    )
                    for e in entries
                )
            )
            if len(unique_files) < 2:
                continue

            # Преобразуем в удобный формат
            files_with_mod = [
                (rel_path, mod_path, lang) for rel_path, mod_path, lang in unique_files
            ]

            self.duplicates_data.append(
                {
                    "tag": tag,
                    "files": files_with_mod,  # ✅ Теперь список кортежей (rel_path, mod_path, lang)
                    "count": len(entries),
                }
            )
            idx = len(self.duplicates_data) - 1
            group_name = f"{tag} ({len(entries)} {tr('duplicates_entries', 'записей')})"
            # ✅ Показываем только rel_path в UI
            files_text = "\n".join(
                f"  • {rel_path}" for rel_path, mod_path, lang in unique_files[:20]
            )
            if len(unique_files) > 20:
                files_text += (
                    f"\n  {tr('duplicates_and_more', '... и ещё ')}{len(unique_files) - 20}"
                )
            item_id = self.dup_tree.insert(
                "",
                "end",
                values=("☑", group_name, files_text, f"{len(entries)}"),
                tags=("duplicate",),
            )
            self._all_dup_items.append(item_id)  # Сохраняем для фильтрации
            self.selected_duplicates.add(idx)

        self.log(tr("duplicates_found_keys", "Найдено ключей с дубликатами: ") + str(dup_count))
        self._update_stats()

    def _on_merge(self):
        if not self.selected_duplicates:
            messagebox.showwarning(
                tr("duplicates_warning", "Предупреждение"),
                tr(
                    "duplicates_select_merge_group",
                    "Выберите хотя бы одну группу дубликатов для слияния",
                ),
            )
            return

        # Подтверждение перед слиянием
        dup_count = len(self.selected_duplicates)
        result = messagebox.askyesno(
            tr("duplicates_confirm_merge", "Подтверждение слияния"),
            tr(
                "duplicates_confirm_message",
                f"Вы собираетесь слить {dup_count} групп дубликатов.\n\nПродолжить?",
            ),
        )
        if not result:
            return

        mods_folder = self.mods_entry.get()
        output_folder = self.output_entry.get()
        if not mods_folder or not output_folder:
            messagebox.showwarning(
                tr("duplicates_warning", "Предупреждение"),
                tr("duplicates_select_mods_output", "Выберите папки модов и вывода"),
            )
            return

        # Показать прогресс слияния
        self._show_progress()
        self.progress_bar["value"] = 0
        self.progress_bar.configure(mode="determinate")
        self.progress_label.config(text=tr("duplicates_merging", "🔄 Слияние дубликатов..."))

        from utils.ui_helpers import create_debounced_progress

        root = self.winfo_toplevel()
        self._progress_updater = create_debounced_progress(self, root=root, delay_ms=150)

        if self.on_merge_callback:
            self.log(tr("duplicates_starting_merge", "Запуск слияния выбранных дубликатов..."))
            self.on_merge_callback(self.get_options())

    def get_options(self):
        return {
            "mods_folder": self.mods_entry.get(),
            "output_folder": self.output_entry.get(),
            "auto_merge": self.merge_var.get(),
            "create_backup": self.backup_var.get(),
            "selected_duplicates": list(self.selected_duplicates),
        }

    def log(self, message):
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)

    def update_progress(self, value, message=""):
        """Обновить прогресс слияния дубликатов"""
        self.progress_bar["value"] = value
        if message:
            self.progress_label.config(text=message)

    def finish_progress(self, success=True):
        """Завершить прогресс слияния"""
        self.progress_bar.stop()
        if success:
            self.progress_bar.configure(bootstyle="success-striped")
            self.progress_label.config(text=tr("duplicates_merge_success", " Слияние завершено успешно"))
        else:
            self.progress_bar.configure(bootstyle="danger-striped")
            self.progress_label.config(text=tr("duplicates_merge_error", " Ошибка при слиянии"))
        self.after(3000, self._hide_progress)
        self._progress_updater = None

    def _show_progress(self):
        """Показать прогресс-бар"""
        self.progress_bar["value"] = 0
        self.progress_bar.configure(mode="determinate", bootstyle=PROGRESS_BOOTSTYLES["duplicates"])
        self.progress_label.config(text="")
        progress_frame = self.progress_bar.master
        progress_frame.grid()

    def _hide_progress(self):
        """Скрыть прогресс-бар"""
        progress_frame = self.progress_bar.master
        progress_frame.grid_remove()

    def _on_dup_filter_debounced(self, event=None):
        """Debounce для фильтрации дубликатов (300мс задержка)"""
        if self._dup_filter_debounce_timer:
            self.after_cancel(self._dup_filter_debounce_timer)
        self._dup_filter_debounce_timer = self.after(300, self._filter_duplicates)

    def _filter_duplicates(self, event=None):
        """Фильтрация дубликатов по поисковому запросу"""
        try:
            if not hasattr(self, "dup_tree") or self.dup_tree is None:
                return

            search_text = self.dup_search_var.get().lower()

            # Итерируемся по ВСЕМ элементам (не только видимым)
            for item in self._all_dup_items:
                values = self.dup_tree.item(item, "values")
                if not values:
                    continue
                group_name = values[1].lower()
                files_text = values[2].lower()
                if not search_text or search_text in group_name or search_text in files_text:
                    self.dup_tree.reattach(item, "", "end")
                else:
                    self.dup_tree.detach(item)
        except Exception:
            # Тихо игнорируем ошибки фильтрации — не ломаем UI
            pass

    def _clear_search(self):
        """Очистить поиск и показать все дубликаты"""
        try:
            if not hasattr(self, "dup_tree") or self.dup_tree is None:
                return
            self.dup_search_var.set("")
            for item in self._all_dup_items:
                self.dup_tree.reattach(item, "", "end")
        except Exception:
            pass

    def _on_dup_click(self, event):
        """Обработка клика по дубликату в дереве"""
        try:
            item = self.dup_tree.identify_row(event.y)
            if not item:
                return

            # Используем _all_dup_items для корректного получения индекса
            if item in self._all_dup_items:
                idx = self._all_dup_items.index(item)
                values = self.dup_tree.item(item, "values")
                if values[0] == "☑":
                    self.dup_tree.set(item, "select", "☐")
                    self.selected_duplicates.discard(idx)
                else:
                    self.dup_tree.set(item, "select", "☑")
                    self.selected_duplicates.add(idx)
                self._update_stats()
        except Exception as e:
            print(f"Ошибка при обработке клика: {e}")

    def _show_dup_context_menu(self, event):
        """Показать контекстное меню для дубликата"""
        try:
            item = self.dup_tree.identify_row(event.y)
            if not item:
                return

            # Выбираем элемент
            self.dup_tree.selection_set(item)
            values = self.dup_tree.item(item, "values")
            if not values:
                return

            # Используем _all_dup_items для корректного получения индекса
            if item not in self._all_dup_items:
                return

            idx = self._all_dup_items.index(item)
            dup_data = self.duplicates_data[idx] if idx < len(self.duplicates_data) else None

            # Создаём контекстное меню
            context_menu = tk.Menu(self, tearoff=0)

            # Опции выбора
            if values[0] == "☑":
                context_menu.add_command(
                    label=tr("dup_ctx_deselect", "☐ Снять выбор"),
                    command=lambda: self._deselect_single_dup(item, idx),
                )
            else:
                context_menu.add_command(
                    label=tr("dup_ctx_select", "☑ Выбрать"),
                    command=lambda: self._select_single_dup(item, idx),
                )

            context_menu.add_separator()

            # Открыть папку
            if dup_data and dup_data.get("files"):
                first_file = dup_data["files"][0]
                # ✅ first_file теперь кортеж (rel_path, mod_path, lang)
                if isinstance(first_file, tuple) and len(first_file) >= 3:
                    rel_path, mod_path, lang = first_file
                elif isinstance(first_file, tuple) and len(first_file) == 2:
                    rel_path, mod_path = first_file
                    lang = "Russian"  # Fallback
                else:
                    # Обработка старого формата (только rel_path)
                    rel_path = first_file
                    mod_path = mods_folder
                    lang = "Russian"

                if mod_path and os.path.exists(mod_path):
                    context_menu.add_command(
                        label=tr("dup_ctx_open_folder", "📂 Открыть папку"),
                        command=lambda: self._open_dup_folder(mod_path, rel_path, lang),
                    )

            context_menu.add_separator()

            # Информация
            context_menu.add_command(
                label=tr("dup_ctx_info", "📊 Информация"),
                command=lambda: self._show_dup_info(dup_data, values),
            )

            context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Ошибка в контекстном меню: {e}")

    def _select_single_dup(self, item, idx):
        """Выбрать один дубликат"""
        self.dup_tree.set(item, "select", "☑")
        self.selected_duplicates.add(idx)
        self._update_stats()

    def _deselect_single_dup(self, item, idx):
        """Снять выбор с одного дубликата"""
        self.dup_tree.set(item, "select", "☐")
        self.selected_duplicates.discard(idx)
        self._update_stats()

    def _open_dup_folder(self, mods_folder, rel_path, lang="Russian"):
        """Открыть папку дубликата"""
        try:
            # ✅ ОТЛАДКА: Логируем что получаем
            print("[DEBUG] _open_dup_folder вызван:")
            print(f"  mods_folder: {mods_folder}")
            print(f"  rel_path: {rel_path}")
            print(f"  rel_path repr: {rel_path!r}")
            print(f"  lang: {lang}")

            # ✅ ИСПРАВЛЕНО: Добавляем Languages/{lang} между mod_path и rel_path
            # Структура: Mods/ModName/Languages/{lang}/DefInjected/...
            # rel_path = DefInjected\BodyPartDef\file.xml
            languages_segment = f"Languages{os.sep}{lang}"

            # Собираем полный путь к папке файла
            dir_part = os.path.dirname(rel_path)
            folder_path = os.path.join(mods_folder, languages_segment, dir_part)

            # Нормализуем разделители
            folder_path = os.path.normpath(folder_path)

            print(f"  folder_path: {folder_path}")
            print(f"  folder существует: {os.path.exists(folder_path)}")

            if os.path.exists(folder_path):
                os.startfile(folder_path)
            else:
                messagebox.showwarning(
                    tr("dup_warning", "Предупреждение"),
                    tr("dup_folder_not_found", "Папка не найдена:\n{path}").format(
                        path=folder_path
                    ),
                )
        except Exception as e:
            messagebox.showerror(
                tr("dup_error", "Ошибка"),
                tr("dup_open_folder_error", "Ошибка открытия папки:\n{error}").format(error=str(e)),
            )

    def _show_dup_info(self, dup_data, values):
        """Показать информацию о дубликате"""
        if not dup_data:
            return

        tag = dup_data.get("tag", "Неизвестно")
        files = dup_data.get("files", [])
        count = dup_data.get("count", 0)

        # ✅ files теперь список кортежей (rel_path, mod_path, lang)
        files_display = []
        for f in files:
            if isinstance(f, tuple) and len(f) >= 3:
                rel_path, mod_path, lang = f
                files_display.append(f"{rel_path} [{lang}]")
            elif isinstance(f, tuple) and len(f) == 2:
                rel_path, mod_path = f
                files_display.append(f"{rel_path} [Russian]")
            else:
                files_display.append(str(f))

        info_text = (
            f"{tr('dup_info_tag', 'Тег')}: {tag}\n"
            f"{tr('dup_info_count', 'Количество записей')}: {count}\n"
            f"{tr('dup_info_files', 'Файлы')}: {len(files_display)}\n\n"
            + "\n".join(f"  • {f}" for f in files_display[:10])
        )

        if len(files_display) > 10:
            info_text += f"\n  ... и ещё {len(files_display) - 10}"

        messagebox.showinfo(
            tr("dup_info_title", "Информация о дубликате"),
            info_text,
        )

    def _select_all_duplicates(self):
        """Выбрать все дубликаты (включая отфильтрованные)"""
        for i, item in enumerate(self._all_dup_items):
            self.dup_tree.set(item, "select", "☑")
            self.selected_duplicates.add(i)
        self._update_stats()

    def _deselect_all_duplicates(self):
        """Снять выбор со всех дубликатов (включая отфильтрованные)"""
        self.selected_duplicates.clear()
        for item in self._all_dup_items:
            self.dup_tree.set(item, "select", "☐")
        self._update_stats()

    def _update_stats(self):
        total = len(self.duplicates_data)
        selected = len(self.selected_duplicates)
        if total == 0:
            self.stats_label.config(text=tr("duplicates_not_found", "Дубликаты не найдены"))
        else:
            self.stats_label.config(
                text=tr("duplicates_stats_found_selected", "Найдено групп: ")
                + f"{total} | {tr('duplicates_stats_selected', 'Выбрано: ')}"
                + f"{selected}"
            )

    def _show_help(self):
        """Показать справку по вкладке «Дубликаты» из JSON файла"""
        try:
            from gui.help.help_loader import format_duplicates_help_text, load_duplicates_help

            help_data = load_duplicates_help()
            help_text = format_duplicates_help_text(help_data)
        except Exception:
            # Fallback на английском (универсальный язык)
            help_text = (
                "📖 Duplicates Tab Help\n\n"
                "🔄 Overview: Detect and merge duplicate translation tags\n"
                "⚙️ Settings: Mods folder, output folder, merge options\n"
                "🔍 Scanning: Find duplicates across all mods\n"
                "✅ Selection: Check groups to merge\n"
                "📋 Context Menu: Right-click for select, open folder, info\n"
                "🚀 Merge: Start duplicate merging operation\n"
                "📊 Statistics: Number of found and selected groups\n"
                "⌨️ Hotkeys: Ctrl+A, Ctrl+D, Ctrl+F, Delete, Enter"
            )

        messagebox.showinfo(tr("duplicates_help_title", "📖 Duplicates Help"), help_text)
