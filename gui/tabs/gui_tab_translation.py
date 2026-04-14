import os
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from config.paths_config import get_paths_config
from gui.components.gui_components import FolderSelector, LanguageSelector, ModsPathSelector
from gui.constants import (
    PAD_BTN_X,
    PAD_ENTRY_X,
    PAD_FRAME_X,
    PAD_FRAME_Y,
    PAD_LABEL_X,
    PAD_X,
    PAD_Y,
    PROGRESS_BOOTSTYLES,
)
from gui.core.debounce_mixin import DebounceMixin
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from utils.mod_translation_status import ModTranslationChecker


class TranslationTab(ttk.Frame, DebounceMixin):
    def __init__(self, parent, config, on_change=None, on_translate=None, on_cancel=None):
        super().__init__(parent)
        self.config = config
        self.on_change = on_change
        self.on_translate = on_translate
        self.on_cancel = on_cancel
        self.selected_mods = {}
        self.is_translating = False
        self._init_debounce("filter")  # Инициализация debounce таймера
        self._all_mods_items = []  # Храним все item ID для корректной фильтрации
        self._all_mods_with_paths = {}  # Храним {item_id: mod_full_path} для _refresh_statuses

        # ✅ НОВОЕ: Создаём проверщик статуса переводов
        self.translation_checker = None

        from gui.components.gui_file_colors import FILE_COLORS

        self.file_colors = FILE_COLORS
        self._setup_ui()
        self._refresh_mods_list()

    def _setup_ui(self):
        self.mods_selector = ModsPathSelector(
            self,
            initial_value=get_paths_config().get_mods_path(),
            width=50,
            command=self._on_mods_folder_changed,
        )
        self.mods_selector.grid(row=0, column=0, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)
        ToolTip(self.mods_selector, "Выберите папку с модами RimWorld")

        # ✅ НОВОЕ: Инициализируем translation_checker СРАЗУ
        initial_folder = get_paths_config().get_mods_path()
        if initial_folder and os.path.exists(initial_folder):
            self.translation_checker = ModTranslationChecker(initial_folder)
            # ✅ Сканируем АСИНХРОННО чтобы не блокировать UI
            self._scan_mods_async()

        self.output_selector = FolderSelector(
            self,
            label_text=tr("translation_output_folder", "Папка вывода:"),
            button_text=tr("translation_browse", "Обзор..."),
            initial_value=get_paths_config().get_output_path(),
            width=50,
            command=self._on_change,
        )
        self.output_selector.grid(row=1, column=0, sticky="ew", padx=PAD_FRAME_X, pady=PAD_Y)
        ToolTip(self.output_selector, "Папка для сохранения переведённых модов")

        lang_frame = ttk.Frame(self)
        lang_frame.grid(row=2, column=0, sticky="w", padx=PAD_FRAME_X, pady=PAD_Y)
        self.source_lang = LanguageSelector(
            lang_frame,
            label_text=tr("translation_source_language", "Исходный язык:"),
            initial_value=self.config.get("source_language", "English"),
        )
        self.source_lang.pack(anchor="w", pady=2)
        ToolTip(self.source_lang, "Язык оригинала модов")

        self.target_lang = LanguageSelector(
            lang_frame,
            label_text=tr("translation_target_language", "Целевой язык:"),
            initial_value=self.config.get("target_language", "Russian"),
        )
        self.target_lang.pack(anchor="w", pady=2)
        ToolTip(self.target_lang, "Язык, на который будет выполнен перевод")

        mods_frame = ttk.LabelFrame(self, text=tr("translation_mods", "Моды для перевода"))
        mods_frame.grid(row=3, column=0, sticky="nsew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        btn_frame = ttk.Frame(mods_frame)
        btn_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)

        btn_select_all = ttk.Button(
            btn_frame,
            text=tr("translation_select_all", "Выбрать все"),
            command=self._select_all_mods,
        )
        btn_select_all.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_select_all, "Выбрать все моды для перевода")

        btn_deselect_all = ttk.Button(
            btn_frame,
            text=tr("translation_deselect_all", "Снять все"),
            command=self._deselect_all_mods,
        )
        btn_deselect_all.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_deselect_all, "Снять выбор со всех модов")

        btn_refresh = ttk.Button(
            btn_frame,
            text=tr("translation_refresh", "🔄 Обновить"),
            command=lambda: self._refresh_mods_list(force_rescan=True),
            bootstyle="info",
        )
        btn_refresh.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_refresh, "Обновить список модов (пересканировать папку)")

        btn_translated = ttk.Button(
            btn_frame,
            text=tr("translation_translated", "✅ Переведённые"),
            command=lambda: self._select_by_status(
                tr("translation_status_translated", "Переведён")
            ),
        )
        btn_translated.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_translated, "Выбрать только переведённые моды")

        btn_untranslated = ttk.Button(
            btn_frame,
            text=tr("translation_untranslated", "⬜ Не переведённые"),
            command=lambda: self._select_by_status(
                tr("translation_status_no_translation", "Нет переводов")
            ),
        )
        btn_untranslated.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_untranslated, "Выбрать только непереведённые моды")

        btn_separate = ttk.Button(
            btn_frame,
            text=tr("translation_separate", "🔵 Отдельные моды"),
            command=lambda: self._select_by_status(
                tr("translation_status_separate", "Отдельный мод")
            ),
        )
        btn_separate.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_separate, "Выбрать только отдельные моды-переводы")

        filter_frame = ttk.Frame(mods_frame)
        filter_frame.pack(fill="x", padx=PAD_X, pady=PAD_Y)
        ttk.Label(filter_frame, text=tr("translation_search", "🔍 Поиск:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(
            filter_frame, textvariable=self.search_var, width=30, bootstyle="info"
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        self.search_entry.bind("<KeyRelease>", self._on_filter_change_debounced)
        ToolTip(self.search_entry, "Введите текст для фильтрации списка модов")
        # Кнопка очистки поиска
        btn_clear_search = ttk.Button(
            filter_frame, text="✕", width=3, command=self._clear_mod_search, bootstyle="secondary"
        )
        btn_clear_search.pack(side="left")
        ToolTip(btn_clear_search, "Очистить поиск")

        self.show_translated_var = tk.BooleanVar(value=True)
        self.show_partial_var = tk.BooleanVar(value=True)
        self.show_untranslated_var = tk.BooleanVar(value=True)
        self.show_separate_var = tk.BooleanVar(value=True)

        chk_trans = ttk.Checkbutton(
            filter_frame,
            text=tr("translation_filter_translated", "✅ Переведённые"),
            variable=self.show_translated_var,
            command=self._apply_filters,
        )
        chk_trans.pack(side="left", padx=PAD_X)
        ToolTip(chk_trans, "Показать переведённые моды")

        chk_partial = ttk.Checkbutton(
            filter_frame,
            text=tr("translation_filter_partial", "⚠️ Частично"),
            variable=self.show_partial_var,
            command=self._apply_filters,
        )
        chk_partial.pack(side="left", padx=PAD_X)
        ToolTip(chk_partial, "Показать моды с частичным переводом")

        chk_untranslated = ttk.Checkbutton(
            filter_frame,
            text=tr("translation_filter_untranslated", "⬜ Не переведённые"),
            variable=self.show_untranslated_var,
            command=self._apply_filters,
        )
        chk_untranslated.pack(side="left", padx=PAD_X)
        ToolTip(chk_untranslated, "Показать моды без перевода")

        chk_separate = ttk.Checkbutton(
            filter_frame,
            text=tr("translation_filter_separate", "🔵 Отдельные моды"),
            variable=self.show_separate_var,
            command=self._apply_filters,
        )
        chk_separate.pack(side="left", padx=PAD_X)
        ToolTip(chk_separate, "Показать отдельные моды-переводы")

        tree_frame = ttk.Frame(mods_frame)
        tree_frame.pack(fill="both", expand=True, padx=PAD_X, pady=PAD_Y)

        # ✅ ИСПОЛЬЗУЕМ переиспользуемый компонент ScrollableTree
        from gui.components.scrollable_tree import ScrollableTree

        columns = ("select", "name", "status")
        self.mods_tree_widget = ScrollableTree(
            tree_frame,
            columns=columns,
            headings={
                "select": tr("translation_select_col", "✓"),
                "name": tr("translation_mod_name", "Название мода"),
                "status": tr("translation_status", "Статус"),
            },
            column_widths={"select": 30, "name": 300, "status": 100},
            column_mins={"select": 30, "name": 100, "status": 50},
            height=10,
            selectmode="browse",
        )
        # ✅ Упаковываем ScrollableTree
        self.mods_tree_widget.pack(fill="both", expand=True)
        # Настраиваем команду сортировки для заголовков
        self.mods_tree_widget.tree.heading(
            "name", command=lambda: self._sort_treeview("name", False)
        )
        self.mods_tree_widget.tree.heading(
            "status", command=lambda: self._sort_treeview("status", False)
        )

        # Настраиваем stretch=False для колонки select
        self.mods_tree_widget.tree.column("select", stretch=False)

        # Теги для статусов
        for status, color in self.file_colors.items():
            self.mods_tree_widget.tree.tag_configure(status, background=color, foreground="white")

        # Привязки событий
        self.mods_tree_widget.tree.bind("<Button-1>", self._on_mod_click)
        self.mods_tree_widget.tree.bind("<Button-3>", self._show_context_menu)

        # Псевдоним для обратной совместимости
        self.mods_tree = self.mods_tree_widget.tree

        # Прогресс перевода — нативный Progressbar с bootstyle
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=4, column=0, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y)
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            bootstyle=PROGRESS_BOOTSTYLES["translation"],
        )
        self.progress_bar.pack(fill="x", padx=PAD_X, pady=3)
        self.progress_label = ttk.Label(
            progress_frame, text=tr("translation_ready", "✅ Готов к переводу")
        )
        self.progress_label.pack(anchor="w", padx=PAD_X, pady=(0, 3))

        # ✅ НОВОЕ: Чекбокс принудительного обновления
        self.force_update_var = tk.BooleanVar(value=False)
        force_update_chk = ttk.Checkbutton(
            self,
            text=tr(
                "translation_force_update",
                "🔄 Принудительное обновление (перезаписать существующие переводы)",
            ),
            variable=self.force_update_var,
            bootstyle="warning",
        )
        force_update_chk.grid(row=5, column=0, sticky="w", padx=PAD_FRAME_X, pady=(0, PAD_Y))
        ToolTip(force_update_chk, "Если включено - перезапишет все существующие переводы")

        # ✅ НОВОЕ: Чекбокс Fuzzy поиска (как RimTrans)
        self.fuzzy_var = tk.BooleanVar(value=True)  # ✅ По умолчанию ВКЛЮЧЁН
        fuzzy_chk = ttk.Checkbutton(
            self,
            text=tr(
                "translation_fuzzy",
                "🔍 Fuzzy поиск (использовать переводы из переименованных тегов)",
            ),
            variable=self.fuzzy_var,
            bootstyle="info",
        )
        fuzzy_chk.grid(row=6, column=0, sticky="w", padx=PAD_FRAME_X, pady=(0, PAD_Y))
        ToolTip(
            fuzzy_chk,
            "Если включено - будет искать переводы по частичному совпадению ключей (40%+)",
        )

        btn_action_frame = ttk.Frame(self)
        btn_action_frame.grid(row=7, column=0, padx=PAD_FRAME_X, pady=PAD_FRAME_Y)

        # ✅ НОВОЕ: Кнопка очистки кэша
        self.clear_cache_btn = ttk.Button(
            btn_action_frame,
            text=tr("translation_clear_cache", "🗑 Очистить кэш"),
            command=self._on_clear_cache,
            bootstyle="warning",
        )
        self.clear_cache_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(
            self.clear_cache_btn,
            "Очистить кэш переводов и БД. Используйте если удалили переводы из XML но программа их ещё видит",
        )

        self.translate_btn = ttk.Button(
            btn_action_frame,
            text=tr("translation_start", "🚀 Запустить перевод"),
            command=self._on_translate,
            bootstyle="success",
        )
        self.translate_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(self.translate_btn, "Начать перевод выбранных модов")

        self.cancel_btn = ttk.Button(
            btn_action_frame,
            text=tr("translation_cancel", "⛔ Отмена"),
            command=self._on_cancel_translation,
            bootstyle="danger",
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(self.cancel_btn, "Отменить текущий перевод")

        # Настройка растягивания
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # mods_frame растягивается
        self.rowconfigure(6, weight=0)  # btn_action_frame

    def _show_context_menu(self, event):
        item = self.mods_tree.identify_row(event.y)
        if not item:
            return
        values = self.mods_tree.item(item, "values")
        if not values:
            return
        mod_name = values[1]
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(
            label=tr("translation_ctx_select", "☑ Выбрать"),
            command=lambda: self._select_mod(item, mod_name),
        )
        context_menu.add_command(
            label=tr("translation_ctx_deselect", "☐ Снять выбор"),
            command=lambda: self._deselect_mod(item, mod_name),
        )
        context_menu.add_separator()
        context_menu.add_command(
            label=tr("translation_ctx_open_folder", "📂 Открыть папку"),
            command=lambda: self._open_mod_folder(mod_name),
        )
        context_menu.post(event.x_root, event.y_root)

    def _select_mod(self, item, mod_name):
        self.selected_mods[mod_name] = True
        self.mods_tree.set(item, "select", "☑")

    def _deselect_mod(self, item, mod_name):
        if mod_name in self.selected_mods:
            del self.selected_mods[mod_name]
        self.mods_tree.set(item, "select", "☐")

    def _open_mod_folder(self, mod_name):
        mods_folder = self.mods_selector.get()
        if mods_folder:
            mod_path = os.path.join(mods_folder, mod_name)
            if os.path.exists(mod_path):
                os.startfile(mod_path)
            else:
                messagebox.showwarning(
                    tr("translation_warning", "Предупреждение"),
                    tr("translation_mod_not_found", "Папка мода не найдена:\n{mod_path}").format(
                        mod_path=mod_path
                    ),
                )

    def _sort_treeview(self, column, reverse):
        items = [(self.mods_tree.set(k, column), k) for k in self.mods_tree.get_children("")]
        items.sort(reverse=reverse)
        for index, (val, k) in enumerate(items):
            self.mods_tree.move(k, "", index)
        self.mods_tree.heading(column, command=lambda: self._sort_treeview(column, not reverse))

    def _on_change(self, value=None):
        """Callback при изменении конфигурации"""
        if self.on_change:
            self.on_change()

    def _on_clear_cache(self):
        """Очистка кэша переводов и БД"""
        from tkinter import messagebox

        cleared = 0

        # 1. Очищаем TranslationDatabase
        try:
            from translation_db import get_translation_db

            db = get_translation_db()
            if db and db.conn:
                # Считаем записи до очистки
                cursor = db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM translations")
                count_before = cursor.fetchone()[0]

                # Очищаем
                cursor.execute("DELETE FROM translations")
                db.conn.commit()
                cleared += count_before
        except Exception as e:
            print(f"⚠️ Ошибка очистки БД: {e}")

        # 2. Очищаем mod_cache
        try:
            from utils.mod_cache import get_mods_cache

            cache = get_mods_cache()
            mods_folder = self.mods_selector.get()
            if mods_folder:
                cache.clear(mods_folder)
        except Exception as e:
            print(f"⚠️ Ошибка очистки кэша модов: {e}")

        # Показываем результат
        if cleared > 0:
            messagebox.showinfo(
                tr("translation_cache_cleared", "Кэш очищен"),
                f"✅ Удалено {cleared} записей из БД переводов.\n\n"
                f"Теперь программа будет читать переводы напрямую из XML файлов.",
            )
        else:
            messagebox.showinfo(
                tr("translation_cache_empty", "Кэш пуст"),
                "ℹ️ База данных переводов пуста.\n\n"
                "Если проблема сохраняется - проверьте что вы действительно удалили переводы из XML файлов.",
            )

    def _on_translate(self):
        """Обработка нажатия кнопки запуска перевода"""
        if self.is_translating:
            return
        if self.on_change:
            self.on_change()

        # ✅ НОВОЕ: Создаём debounced обновитель прогресса
        from utils.ui_helpers import create_debounced_progress

        # Получаем root из виджета
        root = self.winfo_toplevel()
        self._progress_updater = create_debounced_progress(
            self,
            root=root,
            delay_ms=100,  # Обновляем UI не чаще 10 раз в секунду
        )

        # Активируем режим перевода
        self.is_translating = True
        self.translate_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_var.set(0)
        self.progress_label.config(text=tr("translation_starting", "Запуск перевода..."))
        if self.on_translate:
            self.on_translate(self.get_config())

    def _on_cancel_translation(self):
        if not self.is_translating:
            return
        if messagebox.askyesno(
            tr("translation_cancel_title", "Отмена перевода"),
            tr("translation_cancel_confirm", "Вы уверены, что хотите отменить перевод?"),
        ):
            # ✅ НОВОЕ: Очищаем debounced updater
            if hasattr(self, "_progress_updater") and self._progress_updater:
                self._progress_updater.flush()
                self._progress_updater = None

            self.is_translating = False
            self.translate_btn.config(state="normal")
            self.cancel_btn.config(state="disabled")
            self.progress_label.config(text=tr("translation_cancelled", "Перевод отменён"))
            if self.on_cancel:
                self.on_cancel()

    def update_progress(self, value, message=""):
        """
        Обновить прогресс перевода (вызывается извне).

        При использовании debounce обновления группируются и применяются
        с заданной частотой для предотвращения мерцания UI.

        Args:
            value: Значение прогресса (0-100)
            message: Сообщение для отображения
        """
        # Если есть debounced updater, используем его
        if hasattr(self, "_progress_updater") and self._progress_updater:
            self._progress_updater.update(value, message)
        else:
            # Fallback: немедленное обновление
            self.progress_var.set(value)
            if message:
                self.progress_label.config(text=message)

    def finish_translation(self, success=True):
        """
        Завершить операцию перевода.

        Args:
            success: Успешно ли завершён перевод
        """
        # Если есть debounced updater, используем его
        if hasattr(self, "_progress_updater") and self._progress_updater:
            # Очищаем updater чтобы избежать рекурсии
            updater = self._progress_updater
            self._progress_updater = None  # Сбрасываем ПЕРЕД вызовом
            updater.finish(success)

        # Fallback: обычное завершение
        self.is_translating = False
        self.translate_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        if success:
            self.progress_var.set(100)
            self.progress_label.config(
                text=tr("translation_completed", "✅ Перевод завершён успешно")
            )
        else:
            self.progress_label.config(
                text=tr("translation_error", "❌ Перевод завершён с ошибками")
            )

    def get_config(self):
        return {
            "mods_folder": self.mods_selector.get(),
            "output_folder": self.output_selector.get(),
            "source_language": self.source_lang.get(),
            "target_language": self.target_lang.get(),
            "selected_mods": self.get_selected_mods(),
            "force_update": self.force_update_var.get(),
            "fuzzy": self.fuzzy_var.get(),  # ✅ НОВОЕ: Fuzzy поиск
        }

    def apply_config(self, config):
        self.mods_selector.set(get_paths_config().get_mods_path())
        self.output_selector.set(get_paths_config().get_output_path())
        self.source_lang.set(config.get("source_language", "English"))
        self.target_lang.set(config.get("target_language", "Russian"))

    def _on_mods_folder_changed(self, folder):
        self._refresh_mods_list()

        # ✅ НОВОЕ: Инициализируем translation_checker при смене папки модов
        if folder and os.path.exists(folder):
            self.translation_checker = ModTranslationChecker(folder)
            # Сканируем асинхронно
            self._scan_mods_async()

            if self.on_change:
                self.on_change()

    def _scan_mods_async(self):
        """Асинхронное сканирование модов для проверки статусов"""
        if not self.translation_checker:
            return

        def do_scan():
            try:
                scanned_mods = self.translation_checker.scan_mods()
                # После сканирования обновляем статусы в UI
                # Обновляем _all_mods_with_paths из результатов сканирования
                # Используем lock если есть
                if hasattr(self.translation_checker, "_cache_lock"):
                    with self.translation_checker._cache_lock:
                        mod_items = list(scanned_mods.items())
                else:
                    mod_items = list(scanned_mods.items())

                for mod_id, mod_info in mod_items:
                    mod_path = mod_info.get("mod_path")
                    if mod_path:
                        # Находим item_id в дереве
                        for item in self.mods_tree.get_children():
                            values = self.mods_tree.item(item, "values")
                            if values and values[1] == mod_id:
                                self._all_mods_with_paths[item] = mod_path
                                break

                self.after(0, self._refresh_statuses)
            except Exception as e:
                print(f"Ошибка сканирования модов: {e}")

        import threading

        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()

    def _refresh_statuses(self):
        """Обновить статусы всех модов в дереве"""
        if not self.translation_checker:
            return

        # Используем сохранённые полные пути вместо reconstruction
        for item_id, mod_path in self._all_mods_with_paths.items():
            if not os.path.exists(mod_path):
                continue

            status = self._get_mod_translation_status(mod_path)
            tag = self._get_status_tag(status)
            # Обновляем только статус и тег
            self.mods_tree.set(item_id, column="status", value=status)
            # Обновляем теги
            self.mods_tree.item(item_id, tags=(tag,))

        # Применяем фильтры после обновления
        self._apply_filters()

    def _refresh_mods_list(self, force_rescan=False):
        """Обновить список модов с сохранением выбора"""
        # Сохраняем текущий выбор
        current_selection = set(self.selected_mods.keys())

        # Очищаем дерево и списки всех элементов
        for item in self.mods_tree.get_children():
            self.mods_tree.delete(item)
        self._all_mods_items.clear()
        self._all_mods_with_paths.clear()

        mods_folder = self.mods_selector.get()
        if not mods_folder or not os.path.exists(mods_folder):
            return

        try:
            # ✅ ИСПОЛЬЗУЕМ КЭШИРОВАНИЕ
            from utils.mod_cache import scan_mods_with_cache

            mods_list = scan_mods_with_cache(mods_folder, force_rescan=force_rescan)

            for item_path in mods_list:
                item = os.path.basename(item_path)
                status = self._get_mod_translation_status(item_path)
                tag = self._get_status_tag(status)
                # Восстанавливаем выбор если мод был выбран ранее
                select_mark = "☑" if item in current_selection else "☐"
                if item in current_selection:
                    self.selected_mods[item] = True

                self.mods_tree.insert(
                    "", "end", iid=item, values=(select_mark, item, status), tags=(tag,)
                )
                # Сохраняем item ID и полный путь для фильтрации и _refresh_statuses
                self._all_mods_items.append(item)
                self._all_mods_with_paths[item] = item_path

            # Применяем текущие фильтры после обновления
            self._apply_filters()

        except Exception as e:
            print(f"Ошибка сканирования модов: {e}")

    def _get_status_tag(self, status):
        """Получить тег для статуса перевода"""
        if "Переведён" in status:
            return "complete"
        elif "Частично" in status:
            return "partial"
        elif "Нет переводов" in status:
            return "empty"
        elif "Отдельный мод" in status or "separate" in status.lower():
            return "separate"
        else:
            return "empty"

    def _on_filter_change(self, event=None):
        self._apply_filters()

    def _on_filter_change_debounced(self, event=None):
        """Debounce для фильтрации (300мс задержка)"""
        self.debounce("filter", 300, self._apply_filters)

    def _clear_mod_search(self):
        """Очистить поиск и показать все моды"""
        self.search_var.set("")
        for item in self._all_mods_items:
            self.mods_tree.reattach(item, "", "end")

    def _apply_filters(self):
        """Применить фильтры к модом (поиск + статусы)"""
        search_text = self.search_var.get().lower()

        # Получаем i18n строки для сравнения
        status_translated = tr("translation_status_translated", "Переведён")
        status_partial = tr("translation_filter_partial", "⚠️ Частично")
        status_untranslated = tr("translation_status_no_translation", "Нет переводов")

        # Итерируемся по ВСЕМ элементам (не только видимым)
        for item in self._all_mods_items:
            values = self.mods_tree.item(item, "values")
            if not values:
                continue

            mod_name = values[1].lower()
            status = values[2]

            # Проверяем фильтр поиска
            if search_text and search_text not in mod_name:
                self.mods_tree.detach(item)
                continue

            # Проверяем фильтры статусов
            is_translated = "Переведён" in status or status_translated in status
            is_partial = "Частично" in status or status_partial in status
            is_untranslated = (
                "Нет переводов" in status
                or "Не переведён" in status
                or status_untranslated in status
            )
            is_separate = "Отдельный мод" in status or "separate" in status.lower()

            show = False
            if is_translated and self.show_translated_var.get():
                show = True
            elif is_partial and self.show_partial_var.get():
                show = True
            elif is_untranslated and self.show_untranslated_var.get():
                show = True
            elif (
                is_separate
                and getattr(self, "show_separate_var", None)
                and self.show_separate_var.get()
            ):
                show = True

            if show:
                self.mods_tree.reattach(item, "", "end")
            else:
                self.mods_tree.detach(item)

    def _get_mod_translation_status(self, mod_path):
        """
        Определяет статус перевода мода с использованием ModTranslationChecker.

        Возвращает:
            Статус перевода (✅ Переведён, ⚠️ Частично, ⬜ Не переведён, 🔵 Отдельный мод)
        """
        # ✅ НОВОЕ: Используем ModTranslationChecker для точной проверки
        if self.translation_checker and self.translation_checker._mods_cache:
            # Кэш уже заполнен (асинхронно) - используем checker
            try:
                info = self.translation_checker.get_mod_translation_status(mod_path)
                return info.status_text
            except Exception:
                pass  # В случае ошибки - используем fallback

        # Fallback: старая примитивная проверка
        languages_path = os.path.join(mod_path, "Languages")
        if not os.path.exists(languages_path):
            return "Нет переводов"
        russian_path = os.path.join(languages_path, "Russian")
        if os.path.exists(russian_path):
            for root, dirs, files in os.walk(russian_path):
                for file in files:
                    if file.endswith(".xml"):
                        return "✅ Переведён"
            return "⚠️ Частично"
        return "⬜ Не переведён"

    def _on_mod_click(self, event):
        """Обработка клика по моду в дереве"""
        try:
            item = self.mods_tree.identify_row(event.y)
            if not item:
                return
            values = self.mods_tree.item(item, "values")
            if not values:
                return
            mod_name = values[1]
            if mod_name in self.selected_mods:
                del self.selected_mods[mod_name]
                self.mods_tree.set(item, "select", "☐")
            else:
                self.selected_mods[mod_name] = True
                self.mods_tree.set(item, "select", "☑")
        except Exception as e:
            print(f"Ошибка при обработке клика: {e}")

    def _select_all_mods(self):
        """Выбрать все моды (включая отфильтрованные)"""
        for item in self._all_mods_items:
            values = self.mods_tree.item(item, "values")
            if values:
                mod_name = values[1]
                self.selected_mods[mod_name] = True
                self.mods_tree.set(item, "select", "☑")

    def _deselect_all_mods(self):
        """Снять выбор со всех модов (включая отфильтрованные)"""
        self.selected_mods.clear()
        for item in self._all_mods_items:
            self.mods_tree.set(item, "select", "☐")

    def _select_by_status(self, status):
        """Выбрать моды по статусу перевода"""
        # Снимаем все выборы сначала
        self._deselect_all_mods()

        for item in self._all_mods_items:
            values = self.mods_tree.item(item, "values")
            if values and status in values[2]:
                mod_name = values[1]
                self.selected_mods[mod_name] = True
                self.mods_tree.set(item, "select", "☑")

    def get_selected_mods(self):
        return list(self.selected_mods.keys())

    def _show_btn_tooltip(self, event, text: str):
        """Показать тултип для кнопки"""
        try:
            from ttkbootstrap.widgets import ToolTip

            widget = event.widget
            if not hasattr(widget, "_tooltip"):
                widget._tooltip = ToolTip(widget, text=text, bootstyle="info")
        except ImportError:
            pass

    def _hide_btn_tooltip(self):
        """Скрыть тултип кнопки"""
        # ToolTip из ttkbootstrap автоматически скрывается при уходе курсора
        pass
