# gui/dialogs/suggestions_dialog.py
"""
Диалог подсказок перевода для редактора переводов.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from gui.gui_i18n import tr
from translation_db import get_translation_db


class SuggestionsDialog:
    """Диалог просмотра и применения предложений перевода"""

    def __init__(self, parent, entries, file_path="", editor=None, target_language=None):
        """
        Args:
            parent: Родительское окно
            entries: Список записей редактора
            file_path: Путь к файлу
            editor: Ссылка на TranslationEditorDialog
            target_language: Целевой язык
        """
        self.parent = parent
        self.entries = entries
        self.file_path = file_path
        self.editor = editor
        self.target_language = target_language
        self.db = get_translation_db(target_language)

        if self.db is None:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_db_not_connected", "База переводов не подключена"),
            )
            return

        self._create_dialog()
        self._load_suggestions()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("editor_suggestions", "💡 Подсказки перевода"))
        self.dialog.geometry("700x500")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Заголовок
        ttk.Label(
            self.dialog,
            text=tr("editor_suggestions", "💡 Подсказки перевода"),
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Таблица предложений
        cols = ("key", "suggestion", "confidence", "source", "current")
        self.st = ttk.Treeview(self.dialog, columns=cols, show="headings", height=15)
        for c, h in zip(
            cols,
            [
                tr("editor_suggestions_key_col", "Ключ"),
                tr("editor_suggestions_suggestion_col", "Предложение"),
                tr("editor_suggestions_confidence_col", "Уверенность"),
                tr("editor_suggestions_source_col", "Источник"),
                tr("editor_suggestions_current_col", "Текущее"),
            ],
        ):
            self.st.heading(c, text=h)
            self.st.column(c, width=180)
        self.st.pack(fill="both", expand=True, padx=10, pady=5)

        # Кнопки
        bf = ttk.Frame(self.dialog)
        bf.pack(fill="x", padx=10, pady=5)

        ttk.Button(bf, text=tr("suggestions_refresh", "🔄 Обновить"), command=self._refresh_suggestions).pack(
            side="left", padx=2
        )
        ttk.Button(
            bf, text=tr("editor_apply_selected", "Применить выбранные"), command=self._apply
        ).pack(side="left", padx=2)
        ttk.Button(
            bf, text=tr("editor_close", "✖️ Закрыть"), command=self.dialog.destroy
        ).pack(side="right", padx=2)

    def _load_suggestions(self):
        """Загружает предложения в таблицу"""
        for i in self.st.get_children():
            self.st.delete(i)

        suggs = self.db.get_suggestions_for_entries(self.entries)
        for e in self.entries:
            k = e["key"]
            if k in suggs:
                s = suggs[k]
                self.st.insert(
                    "",
                    "end",
                    values=(
                        k,
                        s["value"],
                        f"{s['confidence'] * 100:.0f}%",
                        s["source"],
                        e.get("value", ""),
                    ),
                )

    def _apply(self):
        """Применяет выбранные предложения"""
        if not self.editor:
            return

        sel = self.st.selection()
        if not sel:
            return

        for iid in sel:
            k, sv = self.st.item(iid)["values"][0], self.st.item(iid)["values"][1]
            for e in self.editor.entries:
                if e["key"] == k:
                    e["value"] = sv
                    e["status"] = "complete" if sv.strip() else "empty"
                    self.editor.modified = True
                    self.db.add_translation(
                        k,
                        e.get("original_value", ""),
                        sv,
                        os.path.basename(self.file_path) if self.file_path else "",
                    )
                    break

        self.editor._update_tree()
        self.editor.history_manager.push_state(self.editor.entries.copy())
        messagebox.showinfo(
            tr("editor_success", "Успех"),
            tr("editor_suggestion_applied", "Предложение применено"),
        )
        self.dialog.destroy()

    def _refresh_suggestions(self):
        """Обновляет предложения"""
        self.db.generate_suggestions()
        self._load_suggestions()
