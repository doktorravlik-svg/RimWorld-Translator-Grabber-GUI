# gui/dialogs/glossary_viewer_dialog.py
"""
Диалог просмотра глоссария для редактора переводов.
"""

import tkinter as tk
from tkinter import messagebox, ttk, StringVar

from gui.gui_i18n import tr
from translation_db import get_translation_db


class GlossaryViewerDialog:
    """Диалог просмотра и применения глоссария"""

    def __init__(self, parent, editor=None):
        """
        Args:
            parent: Родительское окно
            editor: Ссылка на TranslationEditorDialog для применения глоссария
        """
        self.parent = parent
        self.editor = editor
        self.db = get_translation_db()

        if self.db is None:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_db_not_connected", "База переводов не подключена"),
            )
            return

        self._create_dialog()
        self._load_glossary()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("editor_glossary", "📖 Глоссарий"))
        self.dialog.geometry("700x500")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Заголовок
        ttk.Label(
            self.dialog,
            text=tr("editor_glossary", "📖 Глоссарий терминов"),
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Поиск
        sf = ttk.Frame(self.dialog)
        sf.pack(fill="x", padx=10, pady=5)
        ttk.Label(sf, text=tr("editor_search", "🔍 Поиск:")).pack(side="left")
        self.search_var = StringVar()
        ge = ttk.Entry(sf, textvariable=self.search_var, width=30)
        ge.pack(side="left", padx=5)

        # Таблица
        cols = ("term", "translation", "category", "description")
        self.gt = ttk.Treeview(self.dialog, columns=cols, show="headings", height=15)
        for c, h in zip(cols, ["Термин", "Перевод", "Категория", "Описание"]):
            self.gt.heading(c, text=h)
            self.gt.column(c, width=150)
        self.gt.pack(fill="both", expand=True, padx=10, pady=5)

        # Кнопки
        bf = ttk.Frame(self.dialog)
        bf.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            bf,
            text=tr("editor_apply_selected", "Применить к выбранным"),
            command=self._apply_glossary,
        ).pack(side="left", padx=2)

        ttk.Button(
            bf, text=tr("editor_close", "✖️ Закрыть"), command=self.dialog.destroy
        ).pack(side="right", padx=2)

        # Привязка поиска
        ge.bind("<KeyRelease>", lambda e: self._load_glossary(self.search_var.get().lower()))

    def _load_glossary(self, filter_text=""):
        """Загружает глоссарий в таблицу"""
        for i in self.gt.get_children():
            self.gt.delete(i)

        items = self.db.search_glossary(filter_text) if filter_text else self.db.get_all_glossary()
        for t in items:
            self.gt.insert(
                "", "end", values=(t["term"], t["translation"], t["category"], t["description"])
            )

    def _apply_glossary(self):
        """Применяет глоссарий к выбранным записям редактора"""
        if not self.editor:
            return

        sel = self.editor.tree.selection()
        if not sel:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_select_entry", "Выберите запись"),
            )
            return

        for iid in sel:
            k = self.editor.tree.item(iid)["values"][0]
            for e in self.editor.entries:
                if e["key"] == k:
                    e["value"] = self.db.apply_glossary_to_text(e["value"])
                    e["status"] = "complete" if e["value"].strip() else "empty"
                    self.editor.modified = True
                    break

        self.editor._update_tree()
        self.editor.history_manager.push_state(self.editor.entries.copy())
        messagebox.showinfo(
            tr("editor_success", "Успех"), tr("editor_glossary_applied", "Глоссарий применён")
        )
