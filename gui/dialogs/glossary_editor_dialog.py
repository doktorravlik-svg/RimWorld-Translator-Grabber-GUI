# gui/dialogs/glossary_editor_dialog.py
"""
Визуальный редактор глоссария (переписанная версия).
Позволяет добавлять, редактировать и удалять термины глоссария.
Улучшенная версия с современным дизайном и расширенным функционалом.
"""

import json
import traceback
from datetime import datetime

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from loguru import logger
from ttkbootstrap.constants import *
from utils.path_utils import ensure_project_root_in_path


from config.language_constants import DEFAULT_TARGET_LANGUAGE
from gui.gui_i18n import tr
from translation_db import get_translation_db
ensure_project_root_in_path()


class GlossaryEditorDialog:
    """Диалог для редактирования глоссария (улучшенная версия)"""

    def __init__(self, parent, target_language=None):
        logger.debug("GlossaryEditorDialog.__init__ вызван")
        self.parent = parent
        self.target_language = target_language or self._get_default_target_language()
        self.db = get_translation_db(self.target_language)
        logger.debug(f"db = {self.db}")
        logger.debug(f"target_language = {self.target_language}")

        self.current_page = 0
        self.page_size = 100
        self.total_terms = 0

        try:
            logger.debug("Вызываем _create_dialog...")
            self._create_dialog()
            logger.debug("_create_dialog завершён")

            logger.debug("Вызываем _load_glossary...")
            self._load_glossary()
            logger.debug("_load_glossary завершён")
        except Exception as e:
            logger.error(f"Ошибка в __init__: {e}")
            logger.error(traceback.format_exc())
            raise

    def _get_default_target_language(self):
        try:
            from config.config_manager import get_config_manager
            return get_config_manager().get("target_language", DEFAULT_TARGET_LANGUAGE)
        except Exception:
            return DEFAULT_TARGET_LANGUAGE

    def _create_dialog(self):
        """Создаёт диалоговое окно с улучшенным дизайном"""
        self.dialog = tk.Toplevel(self.parent)

        self.dialog.title(tr("glossary_editor_title", "Редактор глоссария"))
        self.dialog.geometry("1000x700")
        self.dialog.minsize(800, 500)
        self.dialog.transient(self.parent)

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        self._build_content()

        # Центрируем относительно родительского окна
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        x = parent_x + (parent_width - 1000) // 2
        y = parent_y + (parent_height - 700) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.deiconify()
        self.dialog.grab_set()

    def _build_content(self):
        """Создаёт содержимое диалога с улучшенным layout"""
        logger.debug("Начало _build_content")

        # Главный контейнер с отступами
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Заголовок с иконкой
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 10))

        title_label = ttk.Label(
            header_frame,
            text="📖 " + tr("glossary_editor_title", "Редактор глоссария"),
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(side="left")

        # Статус справа
        self.status_label = ttk.Label(
            header_frame,
            text=tr("glossary_ready", "Готов"),
            font=("Segoe UI", 9),
            bootstyle="secondary"
        )
        self.status_label.pack(side="right")

        # Панель поиска и фильтров
        search_frame = ttk.LabelFrame(main_container, text=tr("glossary_search_filters", "Поиск и фильтры"))
        search_frame.pack(fill="x", padx=10, pady=10)

        # Поиск
        ttk.Label(search_frame, text=tr("glossary_search", "Поиск:")).grid(row=0, column=0, padx=(0, 5), sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=35)
        search_entry.grid(row=0, column=1, padx=5, sticky="ew")

        # Фильтр по категории
        ttk.Label(search_frame, text=tr("glossary_category", "Категория:")).grid(row=0, column=2, padx=(20, 5), sticky="w")

        #  ОБНОВЛЕНО: Динамическая загрузка категорий из БД
        category_values = ["Все"]
        if self.db:
            try:
                categories = self.db.get_all_categories()
                category_values.extend(sorted(categories))
            except Exception:
                # Fallback: старые категории
                category_values.extend(["game", "seed", "user", "auto", "general", "materials", "weapons", "interface", "names", "biomes", "body_parts", "factions"])

        self.category_var = tk.StringVar(value="Все")
        self.category_combo = ttk.Combobox(
            search_frame,
            textvariable=self.category_var,
            values=category_values,
            width=18,
            state="readonly",
        )
        self.category_combo.grid(row=0, column=3, padx=5, sticky="w")
        self.category_combo.bind("<<ComboboxSelected>>", self._on_search)

        #  CONFIDENCE SCORE (№14): Фильтр по уверенности
        ttk.Label(search_frame, text=tr("glossary_confidence_label", "Уверенность:")).grid(row=0, column=4, padx=(20, 5), sticky="w")
        self.confidence_var = tk.DoubleVar(value=0.0)
        self.confidence_scale = ttk.Scale(
            search_frame,
            from_=0.0,
            to=1.0,
            variable=self.confidence_var,
            orient="horizontal",
            length=100,
            bootstyle="info",
        )
        self.confidence_scale.grid(row=0, column=5, padx=5, sticky="w")
        self.confidence_scale.bind("<ButtonRelease-1>", self._on_search)

        # Отображение текущего значения
        self.confidence_label = ttk.Label(search_frame, text="0.0")
        self.confidence_label.grid(row=0, column=6, padx=(5, 0), sticky="w")
        self.confidence_var.trace("w", self._update_confidence_label)

        # Настройка grid weights
        search_frame.columnconfigure(1, weight=1)

        # Основная область с таблицей
        table_frame = ttk.Frame(main_container)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Таблица с прокруткой
        columns = ("term", "translation", "category", "mod_name", "description", "usage_count")
        self.glossary_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=20,
            bootstyle="info"
        )

        self._setup_category_tags()
        self._load_category_colors()

        # Заголовки с сортировкой
        self.glossary_tree.heading("term", text=tr("glossary_term", "Термин"), command=lambda: self._sort_column("term"))
        self.glossary_tree.heading("translation", text=tr("glossary_translation", "Перевод"), command=lambda: self._sort_column("translation"))
        self.glossary_tree.heading("category", text=tr("glossary_category_col", "Категория"), command=lambda: self._sort_column("category"))
        self.glossary_tree.heading("mod_name", text=tr("glossary_mod", "Мод"))
        self.glossary_tree.heading("description", text=tr("glossary_description", "Описание"), command=lambda: self._sort_column("description"))
        self.glossary_tree.heading("usage_count", text=tr("glossary_usage", "Использований"), command=lambda: self._sort_column("usage_count"))

        # Колонки с весами
        self.glossary_tree.column("term", width=150, minwidth=120)
        self.glossary_tree.column("translation", width=200, minwidth=150)
        self.glossary_tree.column("category", width=100, minwidth=80)
        self.glossary_tree.column("mod_name", width=100, minwidth=80)
        self.glossary_tree.column("description", width=200, minwidth=150)
        self.glossary_tree.column("usage_count", width=100, minwidth=80, anchor="center")

        # Скроллы
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.glossary_tree.yview, bootstyle="round")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.glossary_tree.xview, bootstyle="round")
        self.glossary_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Размещение с помощью grid
        self.glossary_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # События
        self.glossary_tree.bind("<Double-1>", self._edit_term)
        self.glossary_tree.bind("<Button-3>", self._show_context_menu)
        self.glossary_tree.bind("<Delete>", lambda e: self._delete_selected())

        # Панель кнопок
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill="x", pady=(5, 0))

        # Группа действий с терминами
        actions_frame = ttk.LabelFrame(btn_frame, text=tr("glossary_actions", "Действия"))
        actions_frame.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=5)

        ttk.Button(
            actions_frame,
            text=tr("editor_add", "➕ Добавить"),
            command=self._add_term,
            bootstyle="success-outline",
        ).pack(side="left", padx=2)

        ttk.Button(
            actions_frame,
            text=tr("editor_edit", "✏️ Редактировать"),
            command=lambda: self._edit_selected(),
            bootstyle="primary-outline",
        ).pack(side="left", padx=2)

        ttk.Button(
            actions_frame,
            text=tr("editor_delete", "🗑️ Удалить"),
            command=self._delete_selected,
            bootstyle="danger-outline",
        ).pack(side="left", padx=2)

        # Группа импорта/экспорта
        io_frame = ttk.LabelFrame(btn_frame, text=tr("glossary_io", "Импорт/Экспорт"))
        io_frame.pack(side="right", fill="x", padx=(5, 0), pady=5)

        ttk.Button(
            io_frame,
            text=tr("editor_import", "📥 Импорт"),
            command=self._import_glossary,
            bootstyle="info-outline",
        ).pack(side="left", padx=2)

        ttk.Button(
            io_frame,
            text=tr("editor_export", "📤 Экспорт"),
            command=self._export_glossary,
            bootstyle="info-outline",
        ).pack(side="left", padx=2)

        #  ПАГИНАЦИЯ: кнопки навигации
        pagination_frame = ttk.Frame(main_container)
        pagination_frame.pack(fill="x", pady=(0, 5))

        self.prev_btn = ttk.Button(
            pagination_frame,
            text=tr("pagination_prev", "◀ Пред."),
            command=self._prev_page,
            state="disabled",
            bootstyle="secondary-outline",
        )
        self.prev_btn.pack(side="left", padx=5)

        self.page_label = ttk.Label(
            pagination_frame,
            text=tr("pagination_page", "Страница 1"),
            font=("Segoe UI", 9),
        )
        self.page_label.pack(side="left", padx=10)

        self.next_btn = ttk.Button(
            pagination_frame,
            text=tr("pagination_next", "След. ▶"),
            command=self._next_page,
            state="disabled",
            bootstyle="secondary-outline",
        )
        self.next_btn.pack(side="left", padx=5)

        # Кнопка закрытия
        ttk.Button(
            pagination_frame,
            text=tr("editor_close", " Закрыть"),
            command=self._on_dialog_close,
            bootstyle="secondary",
        ).pack(side="right", padx=5)

        logger.debug("_build_content завершён")

    def _setup_category_tags(self):
        """Настраивает теги для цветовой кодировки категорий"""
        from config.config_manager import get_config_manager
        config = get_config_manager().get("glossary_category_colors", {})
        
        default_colors = {
            "game": "#2E7D32",
            "seed": "#6A1B9A",
            "user": "#1565C0",
            "auto": "#E65100",
            "general": "#583A3A",
        }
        
        colors = {**default_colors, **config}
        
        for category, color in colors.items():
            self.glossary_tree.tag_configure(
                category,
                background=color,
                foreground="white" if self._is_dark_color(color) else "black"
            )
        
        self.glossary_tree.tag_configure("general", background=colors.get("general", "#583A3A"))

    def _is_dark_color(self, color: str) -> bool:
        """Определяет, является ли цвет тёмным"""
        color = color.lstrip("#")
        if len(color) != 6:
            return False
        try:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return luminance < 0.5
        except ValueError:
            return False

    def _load_category_colors(self):
        """Загружает цвета категорий из конфигурации"""
        pass

    def _sort_column(self, col):
        """Сортировка по колонке"""
        items = [(self.glossary_tree.set(k, col), k) for k in self.glossary_tree.get_children("")]
        items.sort(reverse=False)

        for index, (val, k) in enumerate(items):
            self.glossary_tree.move(k, "", index)

    def _on_dialog_close(self):
        """Обработчик закрытия диалога"""
        try:
            if self.dialog and self.dialog.winfo_exists():
                self.dialog.grab_release()
                self.dialog.destroy()
        except Exception:
            pass

    def _load_glossary(self):
        """Загружает глоссарий из базы данных с пагинацией"""
        logger.debug("Начало _load_glossary")
        
        # Проверяем, что диалог и виджеты всё ещё существуют
        if not self.dialog.winfo_exists():
            logger.warning("_load_glossary called after dialog was destroyed")
            return
        
        if not self.db:
            self.status_label.config(text=tr("glossary_db_error", " База данных не доступна"))
            logger.warning("База данных недоступна")
            return

        # Очищаем таблицу
        for item in self.glossary_tree.get_children():
            self.glossary_tree.delete(item)

        # Загружаем термины с пагинацией
        category = self.category_var.get()
        search_query = self.search_var.get()
        confidence = self.confidence_var.get()

        try:
            if search_query:
                items = self.db.search_glossary(search_query, self.target_language, category=category if category and category != "Все" else None)
                self._display_items(items)
                return
            elif confidence > 0.0:
                if category and category != "Все":
                    self.total_terms = self.db.get_glossary_total_count_by_confidence(confidence, category, self.target_language)
                else:
                    self.total_terms = self.db.get_glossary_total_count_by_confidence(confidence, target_language=self.target_language)
            elif category and category != "Все":
                self.total_terms = self.db.get_glossary_total_count(category, self.target_language)
            else:
                self.total_terms = self.db.get_glossary_total_count(target_language=self.target_language)

            offset = self.current_page * self.page_size

            if confidence > 0.0:
                logger.debug(f"Загрузка терминов по confidence: min={confidence}, page={self.current_page}")
                items = self.db.get_glossary_by_confidence(confidence, category if category != "Все" else None, self.page_size, offset, self.target_language)
            elif category and category != "Все":
                logger.debug(f"Загрузка терминов: category={category}, page={self.current_page}, limit={self.page_size}")
                items = self.db.get_glossary_by_category(category, self.page_size, offset, self.target_language)
            else:
                logger.debug(f"Загрузка всех терминов: page={self.current_page}, limit={self.page_size}")
                items = self.db.get_all_glossary_paginated(self.page_size, offset, self.target_language)

            self._display_items(items)
            self._update_pagination_controls()

        except Exception as e:
            logger.error(f"Ошибка загрузки глоссария: {e}")
            self.status_label.config(text=tr("glossary_load_error", " Ошибка загрузки"))

    def _display_items(self, items):
        """Отображает термины в таблице с цветовым кодированием"""
        for item in items:
            if hasattr(item, "keys"):  # sqlite3.Row
                values = (
                    item["term"],
                    item["translation"],
                    item["category"],
                    item["mod_name"] if "mod_name" in item else "",
                    item["description"],
                    item["usage_count"] if "usage_count" in item else 0,
                )
                category = item["category"] or "general"
            else:  # tuple
                mod_name = item[5] if len(item) > 5 else ""
                values = (
                    item[1],  # term
                    item[2],  # translation
                    item[3],  # category
                    mod_name,
                    item[4] if len(item) > 4 else "",  # description
                    item[5] if len(item) > 5 else 0,  # usage_count
                )
                category = item[3] if len(item) > 3 else "general"

            #  ЦВЕТОВОЕ КОДИРОВАНИЕ: добавляем тег категории
            self.glossary_tree.insert(
                "",
                "end",
                values=values,
                tags=(category,),
            )

        count = len(items)
        total_pages = (self.total_terms + self.page_size - 1) // self.page_size
        self.status_label.config(
            text=tr("glossary_count", f"Страница {self.current_page + 1} из {total_pages} ({self.total_terms} всего)")
        )
        logger.info(f"Загружено терминов: {count} (страница {self.current_page + 1})")

    def _prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_glossary()

    def _next_page(self):
        """Переход на следующую страницу"""
        total_pages = (self.total_terms + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._load_glossary()

    def _update_confidence_label(self, *args):
        """Обновляет текстовую метку при изменении ползунка"""
        value = self.confidence_var.get()
        self.confidence_label.config(text=f"{value:.1f}")

    def _update_pagination_controls(self):
        """Обновляет состояние кнопок навигации"""
        total_pages = (self.total_terms + self.page_size - 1) // self.page_size

        # Кнопка "Пред."
        if self.current_page <= 0:
            self.prev_btn.config(state="disabled")
        else:
            self.prev_btn.config(state="normal")

        # Кнопка "След."
        if self.current_page >= total_pages - 1:
            self.next_btn.config(state="disabled")
        else:
            self.next_btn.config(state="normal")

        # Обновляем текст страницы
        self.page_label.config(text=f"Страница {self.current_page + 1} из {total_pages}")

    def _on_search(self, *args):
        """Обработка поиска - сбрасываем на первую страницу"""
        self.current_page = 0
        self._load_glossary()

    def _add_term(self):
        """Добавляет новый термин"""
        AddEditGlossaryTermDialog(
            self.dialog, callback=self._load_glossary, target_language=self.target_language
        )

    def _edit_selected(self):
        """Редактирует выбранный термин"""
        selection = self.glossary_tree.selection()
        if not selection:
            messagebox.showwarning(tr("editor_warning", "Внимание"), tr("editor_select_term", "Выберите термин для редактирования"))
            return
        self._edit_term(None)

    def _edit_term(self, event):
        """Редактирует выбранный термин"""
        selection = self.glossary_tree.selection()
        if not selection:
            return

        item = self.glossary_tree.item(selection[0])
        values = item["values"]

        AddEditGlossaryTermDialog(
            self.dialog,
            term=values[0],
            translation=values[1],
            category=values[2],
            description=values[4],
            callback=self._load_glossary,
            target_language=self.target_language,
        )

    def _delete_selected(self):
        """Удаляет выбранный термин"""
        selection = self.glossary_tree.selection()
        if not selection:
            messagebox.showwarning(tr("editor_warning", "Внимание"), tr("editor_select_term_delete", "Выберите термин для удаления"))
            return

        item = self.glossary_tree.item(selection[0])
        values = item["values"]
        self._delete_term(values[0])

    def _show_context_menu(self, event):
        """Показывает контекстное меню"""
        item = self.glossary_tree.identify_row(event.y)
        if not item:
            return

        self.glossary_tree.selection_set(item)
        values = self.glossary_tree.item(item, "values")

        menu = tk.Menu(self.dialog, tearoff=0)
        menu.add_command(
            label="✏️ Редактировать",
            command=lambda: self._edit_term(event)
        )
        menu.add_separator()
        menu.add_command(
            label="🗑️ Удалить",
            command=lambda: self._delete_term(values[0])
        )
        menu.post(event.x_root, event.y_root)

    def _delete_term(self, term):
        """Удаляет термин"""
        logger.debug(f"Вызов _delete_term: {term}")
        if messagebox.askyesno(
            tr("glossary_delete_title", "Удаление термина"),
            tr("glossary_delete_confirm", f"Удалить термин '{term}' из глоссария?"),
        ):
            logger.info(f"Удаление термина: {term}")
            if self.db:
                try:
                    self.db.remove_glossary_term(term, self.target_language)
                    self._load_glossary()
                    logger.debug(f"Термин удалён из глоссария: {term}")
                except Exception as e:
                    logger.error(f"Ошибка удаления термина: {e}")
                    messagebox.showerror(tr("glossary_error", "Ошибка"), tr("glossary_delete_failed", f"Не удалось удалить термин: {e}"))

    def _import_glossary(self):
        """Импортирует глоссарий из файла"""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Импорт глоссария",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            entries = data.get('entries', {})
            file_target_language = data.get('target_language', self.target_language)

            if file_target_language and file_target_language != self.target_language:
                result = messagebox.askyesno(
                    tr("glossary_import", "Импорт"),
                    f"Язык глоссария: {file_target_language}\nТекущий язык: {self.target_language}\nЗаменить?",
                    parent=self.dialog
                )
                if not result:
                    return
                self.target_language = file_target_language
                self.db = get_translation_db(self.target_language)

            if isinstance(entries, dict):
                for term, translation in entries.items():
                    if self.db:
                        # ✅ ИСПРАВЛЕНО: Пропускаем записи, где term == translation
                        if term == translation:
                            logger.debug(f"Skipping term '{term}' - original equals translation")
                            continue
                        self.db.add_glossary_term(term, translation, "imported", "", self.target_language)
                        count += 1
            
            if count == 0:
                return
            
            self._load_glossary()
            messagebox.showinfo(tr("glossary_import", "Импорт"), tr("glossary_import_success", f"Импортировано {count} терминов"))
            logger.info(f"Импортировано {count} терминов из {file_path}")
        except Exception as e:
            logger.error(f"Ошибка импорта глоссария: {e}")
            messagebox.showerror(tr("glossary_error", "Ошибка"), tr("glossary_import_failed", f"Не удалось импортировать: {e}"))

    def _export_glossary(self):
        """Экспортирует глоссарий в файл"""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Экспорт глоссария",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            if self.db:
                terms = self.db.get_all_glossary(target_language=self.target_language)
                entries = {}
                for term in terms:
                    if hasattr(term, "keys"):
                        entries[term["term"]] = term["translation"]
                    else:
                        entries[term.term] = term.translation
                
                data = {
                    "entries": entries,
                    "exported_at": str(datetime.now()),
                    "target_language": self.target_language
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo(tr("glossary_export", "Экспорт"), tr("glossary_export_success", f"Экспортировано {len(entries)} терминов"))
                logger.info(f"Экспортировано {len(entries)} терминов в {file_path}")
        except Exception as e:
            logger.error(f"Ошибка экспорта глоссария: {e}")
            messagebox.showerror(tr("glossary_error", "Ошибка"), tr("glossary_export_failed", f"Не удалось экспортировать: {e}"))


class AddEditGlossaryTermDialog:
    """Диалог для добавления/редактирования термина глоссария (улучшенная версия)"""

    def __init__(
        self, parent, term="", translation="", category="general", description="", callback=None, target_language=None
    ):
        self.parent = parent
        self.target_language = target_language if target_language else self._get_default_target_language()
        self.db = get_translation_db(self.target_language)
        self.is_edit = bool(term)
        self.original_term = term
        self.callback = callback
        self.term_var = tk.StringVar(value=term)
        self.translation_var = tk.StringVar(value=translation)
        self.category_var = tk.StringVar(value=category)
        self.description_var = tk.StringVar(value=description)

        self._create_dialog()

    def _get_default_target_language(self):
        try:
            from config.config_manager import get_config_manager
            return get_config_manager().get("target_language", DEFAULT_TARGET_LANGUAGE)
        except Exception:
            return DEFAULT_TARGET_LANGUAGE

    def _create_dialog(self):
        """Создаёт диалоговое окно с улучшенным дизайном"""
        title = (
            tr("glossary_edit_term", "Редактировать термин")
            if self.is_edit
            else tr("glossary_add_term", "Добавить термин")
        )

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("550x450")
        self.dialog.minsize(450, 350)
        self.dialog.transient(self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        # Главный контейнер
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Заголовок
        header_text = "✏️ " + tr("glossary_edit_term", "Редактирование термина") if self.is_edit else "➕ " + tr("glossary_add_term", "Новый термин")
        header_label = ttk.Label(main_frame, text=header_text, font=("Segoe UI", 14, "bold"))
        header_label.pack(anchor="w", pady=(0, 15))

        # Поля ввода с улучшенным дизайном
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill="both", expand=True)

        # Термин
        ttk.Label(fields_frame, text=tr("glossary_term_label", "Термин:"), font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(5, 2)
        )
        term_entry = ttk.Entry(fields_frame, textvariable=self.term_var, font=("Segoe UI", 10))
        term_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        if not self.is_edit:
            term_entry.focus()

        # Перевод
        ttk.Label(fields_frame, text=tr("glossary_translation_label", "Перевод:"), font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, sticky="w", pady=(5, 2)
        )
        ttk.Entry(fields_frame, textvariable=self.translation_var, font=("Segoe UI", 10)).grid(
            row=3, column=0, sticky="ew", pady=(0, 10)
        )

        # Категория
        ttk.Label(fields_frame, text=tr("glossary_category_label", "Категория:"), font=("Segoe UI", 10, "bold")).grid(
            row=4, column=0, sticky="w", pady=(5, 2)
        )
        category_values = ["general"]
        if self.db:
            try:
                db_categories = self.db.get_all_categories()
                category_values.extend(sorted(db_categories))
            except Exception:
                pass
        if self.category_var.get() and self.category_var.get() not in category_values:
            category_values.insert(0, self.category_var.get())
        category_combo = ttk.Combobox(
            fields_frame, textvariable=self.category_var, values=category_values, state="readonly", font=("Segoe UI", 10)
        )
        category_combo.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        # Описание
        ttk.Label(fields_frame, text=tr("glossary_description_label", "Описание:"), font=("Segoe UI", 10, "bold")).grid(
            row=6, column=0, sticky="w", pady=(5, 2)
        )
        ttk.Entry(fields_frame, textvariable=self.description_var, font=("Segoe UI", 10)).grid(
            row=7, column=0, sticky="ew", pady=(0, 10)
        )

        fields_frame.columnconfigure(0, weight=1)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(15, 0))

        ttk.Button(
            btn_frame,
            text=tr("editor_save", " Сохранить"),
            command=self._save,
            bootstyle="success",
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame, text=tr("editor_cancel", "Отмена"), command=self._on_dialog_close
        ).pack(side="right", padx=5)

        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.grab_set()

    def _on_dialog_close(self):
        """Обработчик закрытия диалога"""
        logger.debug("Вызов _on_dialog_close")
        try:
            self.dialog.grab_release()
        except Exception:
            pass
        self.dialog.destroy()

    def _save(self):
        """Сохраняет термин"""
        logger.debug("Вызов _save")
        term = self.term_var.get().strip()
        translation = self.translation_var.get().strip()
        category = self.category_var.get()
        description = self.description_var.get().strip()

        if not term or not translation:
            messagebox.showwarning(
                tr("glossary_error", "Ошибка"),
                tr("glossary_fill_required", "Заполните термин и перевод!"),
            )
            return

        if self.db:
            try:
                if self.is_edit and term != self.original_term:
                    logger.info(f"Переименование термина: {self.original_term} -> {term}")
                    self.db.rename_glossary_term(
                        self.original_term, term, translation, category, description, self.target_language
                    )
                else:
                    logger.info(f"Добавление термина: {term}")
                    self.db.add_glossary_term(term, translation, category, description, self.target_language, mod_name="")

                messagebox.showinfo(tr("editor_success", "Готово"), tr("glossary_term_saved", f"Термин '{term}' успешно сохранён!"))

            except Exception as e:
                logger.error(f"Ошибка сохранения термина: {e}")
                messagebox.showerror(
                    tr("glossary_error", "Ошибка"),
                    tr("glossary_save_failed", f"Не удалось сохранить термин: {e}")
                )
                return

            if self.callback:
                self.callback()

            self._on_dialog_close()
