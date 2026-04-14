# gui/dialogs/glossary_editor_dialog.py
"""
Визуальный редактор глоссария.
Позволяет добавлять, редактировать и удалять термины глоссария.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from gui.gui_i18n import tr
from translation_db import get_translation_db


class GlossaryEditorDialog:
    """Диалог для редактирования глоссария"""

    def __init__(self, parent):
        self.parent = parent
        self.db = get_translation_db()

        self._create_dialog()
        self._load_glossary()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("glossary_editor_title", "📖 Редактор глоссария"))
        self.dialog.geometry("800x600")
        self.dialog.minsize(600, 400)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        self._build_content()

        # Центрируем
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 800) // 2
        y = (self.dialog.winfo_screenheight() - 600) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _build_content(self):
        """Создаёт содержимое диалога"""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text=tr("glossary_editor_title", "📖 Редактор глоссария"),
            font=("Segoe UI", 14, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # Панель инструментов
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill="x", pady=5)

        # Поиск
        ttk.Label(toolbar, text=tr("glossary_search", "🔍 Поиск:")).pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=5)

        # Фильтр по категории
        ttk.Label(toolbar, text=tr("glossary_category", "Категория:")).pack(
            side="left", padx=(10, 5)
        )
        self.category_var = tk.StringVar(value="Все")
        self.category_combo = ttk.Combobox(
            toolbar,
            textvariable=self.category_var,
            values=["Все", "general", "materials", "weapons", "interface", "names"],
            width=15,
            state="readonly",
        )
        self.category_combo.pack(side="left", padx=5)
        self.category_combo.bind("<<ComboboxSelected>>", self._on_search)

        # Кнопки добавления
        ttk.Button(
            toolbar,
            text=tr("glossary_add", "➕ Добавить"),
            command=self._add_term,
            bootstyle="success",
        ).pack(side="right", padx=2)

        ttk.Button(
            toolbar,
            text=tr("glossary_import", "📥 Импорт"),
            command=self._import_glossary,
            bootstyle="info",
        ).pack(side="right", padx=2)

        # Таблица
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)

        columns = ("term", "translation", "category", "description")
        self.glossary_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        # Заголовки
        self.glossary_tree.heading("term", text=tr("glossary_term", "Термин"))
        self.glossary_tree.heading("translation", text=tr("glossary_translation", "Перевод"))
        self.glossary_tree.heading("category", text=tr("glossary_category_col", "Категория"))
        self.glossary_tree.heading("description", text=tr("glossary_description", "Описание"))

        # Колонки
        self.glossary_tree.column("term", width=150)
        self.glossary_tree.column("translation", width=200)
        self.glossary_tree.column("category", width=100)
        self.glossary_tree.column("description", width=250)

        # Скроллы
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.glossary_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.glossary_tree.xview)
        self.glossary_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # grid для корректного пересечения скроллбаров
        self.glossary_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Двойной клик для редактирования
        self.glossary_tree.bind("<Double-1>", self._edit_term)

        # Контекстное меню
        self.glossary_tree.bind("<Button-3>", self._show_context_menu)

        # Статус
        self.status_label = ttk.Label(
            main_frame, text=tr("glossary_ready", "✅ Загружено терминов: 0"), font=("Segoe UI", 9)
        )
        self.status_label.pack(anchor="w", pady=2)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(
            btn_frame,
            text=tr("glossary_close", "❌ Закрыть"),
            command=self.dialog.destroy,
            bootstyle="secondary",
        ).pack(side="right")

    def _load_glossary(self):
        """Загружает глоссарий из базы данных"""
        if not self.db:
            self.status_label.config(text=tr("glossary_db_error", "❌ База данных не доступна"))
            return

        # Очищаем таблицу
        for item in self.glossary_tree.get_children():
            self.glossary_tree.delete(item)

        # Загружаем термины
        category = self.category_var.get()
        search_query = self.search_var.get()

        if category and category != "Все":
            items = self.db.get_all_glossary(category=category)
        elif search_query:
            items = self.db.search_glossary(search_query)
        else:
            items = self.db.get_all_glossary()

        for item in items:
            # item это tuple: (id, term, translation, category, description, usage_count, created_at)
            # или sqlite3.Row
            if hasattr(item, "keys"):  # sqlite3.Row
                self.glossary_tree.insert(
                    "",
                    "end",
                    values=(
                        item["term"],
                        item["translation"],
                        item["category"],
                        item["description"],
                    ),
                )
            else:  # tuple
                self.glossary_tree.insert(
                    "",
                    "end",
                    values=(
                        item[1],  # term
                        item[2],  # translation
                        item[3],  # category
                        item[4],  # description
                    ),
                )

        count = len(items)
        self.status_label.config(text=tr("glossary_count", f"✅ Загружено терминов: {count}"))

    def _on_search(self, *args):
        """Обработка поиска"""
        self._load_glossary()

    def _add_term(self):
        """Добавляет новый термин"""
        AddEditGlossaryTermDialog(self.dialog, callback=self._load_glossary)

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
            description=values[3],
            callback=self._load_glossary,
        )

    def _show_context_menu(self, event):
        """Показывает контекстное меню"""
        item = self.glossary_tree.identify_row(event.y)
        if not item:
            return

        self.glossary_tree.selection_set(item)
        values = self.glossary_tree.item(item, "values")

        menu = tk.Menu(self.dialog, tearoff=0)
        menu.add_command(
            label=tr("glossary_edit", "✏️ Редактировать"), command=lambda: self._edit_term(event)
        )
        menu.add_command(
            label=tr("glossary_delete", "🗑️ Удалить"), command=lambda: self._delete_term(values[0])
        )
        menu.post(event.x_root, event.y_root)

    def _delete_term(self, term):
        """Удаляет термин"""
        if messagebox.askyesno(
            tr("glossary_delete_title", "Удаление термина"),
            tr("glossary_delete_confirm", f"Удалить термин '{term}' из глоссария?"),
        ):
            if self.db:
                self.db.remove_glossary_term(term)
                self._load_glossary()
                # Debug: логируем удаление термина
                if hasattr(self, "_log_callback") and self._log_callback:
                    self._log_callback(f"[DEBUG] Термин удалён из глоссария: {term}")

    def _import_glossary(self):
        """Импортирует глоссарий из файла (можно доработать)"""
        # Debug: логируем попытку импорта
        if hasattr(self, "_log_callback") and self._log_callback:
            self._log_callback("[DEBUG] Попытка импорта глоссария (функция в разработке)")
        messagebox.showinfo(
            tr("glossary_import", "Импорт"),
            tr(
                "glossary_import_info",
                "Импорт из файла будет добавлен в следующей версии.\n"
                "Сейчас можно добавить термины вручную.",
            ),
        )


class AddEditGlossaryTermDialog:
    """Диалог для добавления/редактирования термина глоссария"""

    def __init__(
        self, parent, term="", translation="", category="general", description="", callback=None
    ):
        self.parent = parent
        self.db = get_translation_db()
        self.is_edit = bool(term)
        self.original_term = term
        self.callback = callback

        self.term_var = tk.StringVar(value=term)
        self.translation_var = tk.StringVar(value=translation)
        self.category_var = tk.StringVar(value=category)
        self.description_var = tk.StringVar(value=description)

        self._create_dialog()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        title = (
            tr("glossary_edit_term", "✏️ Редактировать термин")
            if self.is_edit
            else tr("glossary_add_term", "➕ Добавить термин")
        )

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("500x350")
        self.dialog.minsize(400, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Термин
        ttk.Label(main_frame, text=tr("glossary_term_label", "Термин:")).pack(
            anchor="w", pady=(5, 2)
        )
        ttk.Entry(main_frame, textvariable=self.term_var).pack(fill="x", pady=2)

        # Перевод
        ttk.Label(main_frame, text=tr("glossary_translation_label", "Перевод:")).pack(
            anchor="w", pady=(5, 2)
        )
        ttk.Entry(main_frame, textvariable=self.translation_var).pack(fill="x", pady=2)

        # Категория
        ttk.Label(main_frame, text=tr("glossary_category_label", "Категория:")).pack(
            anchor="w", pady=(5, 2)
        )
        categories = [
            "general",
            "materials",
            "weapons",
            "interface",
            "names",
            "biomes",
            "body_parts",
        ]
        ttk.Combobox(
            main_frame, textvariable=self.category_var, values=categories, state="readonly"
        ).pack(fill="x", pady=2)

        # Описание
        ttk.Label(main_frame, text=tr("glossary_description_label", "Описание:")).pack(
            anchor="w", pady=(5, 2)
        )
        ttk.Entry(main_frame, textvariable=self.description_var).pack(fill="x", pady=2)

        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=15)

        ttk.Button(
            btn_frame,
            text=tr("glossary_save", "💾 Сохранить"),
            command=self._save,
            bootstyle="success",
        ).pack(side="right", padx=5)

        ttk.Button(
            btn_frame, text=tr("glossary_cancel", "❌ Отмена"), command=self.dialog.destroy
        ).pack(side="right", padx=5)

    def _save(self):
        """Сохраняет термин"""
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
            # ✅ ИСПРАВЛЕНО: Сначала удаляем старый термин, потом добавляем новый
            if self.is_edit and term != self.original_term:
                self.db.remove_glossary_term(self.original_term)

            # Теперь добавляем (или обновляем) термин
            self.db.add_glossary_term(term, translation, category, description)

            if self.callback:
                self.callback()

            self.dialog.destroy()
