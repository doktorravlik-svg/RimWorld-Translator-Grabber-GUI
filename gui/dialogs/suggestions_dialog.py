# gui/dialogs/suggestions_dialog.py
"""
Диалог подсказок перевода для редактора переводов.
"""

import os
import tkinter as tk
from tkinter import ttk

from gui.dialogs.messagebox_helpers import show_ok, show_warning
from gui.gui_i18n import tr
from gui.components.scrollable_tree import ScrollableTree
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
            show_warning(parent, tr("editor_db_not_connected", "База переводов не подключена"))
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

        # Таблица предложений (используем ScrollableTree)
        cols = ("key", "suggestion", "confidence", "source", "current")
        headings = {
            "key": tr("editor_suggestions_key_col", "Ключ"),
            "suggestion": tr("editor_suggestions_suggestion_col", "Предложение"),
            "confidence": tr("editor_suggestions_confidence_col", "Уверенность"),
            "source": tr("editor_suggestions_source_col", "Источник"),
            "current": tr("editor_suggestions_current_col", "Текущее"),
        }
        column_widths = {"key": 150, "suggestion": 200, "confidence": 80, "source": 100, "current": 150}

        self.st_wrapper = ScrollableTree(
            self.dialog,
            columns=cols,
            headings=headings,
            column_widths=column_widths,
            height=15,
            selectmode="extended",
        )
        self.st = self.st_wrapper.tree
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
        """Применяет выбранные предложения (оптимизировано с использованием словаря)"""
        if not self.editor:
            return

        sel = self.st.selection()
        if not sel:
            return

        # Создаём быстрый индекс для O(1) поиска
        entries_map = {e["key"]: e for e in self.editor.entries}

        for iid in sel:
            k = self.st.item(iid)["values"][0]
            sv = self.st.item(iid)["values"][1]

            if k in entries_map:
                e = entries_map[k]
                e["value"] = sv
                e["status"] = "complete" if sv.strip() else "empty"
                self.editor.modified = True
                self.db.add_translation(
                    k,
                    e.get("original_value", ""),
                    sv,
                    os.path.basename(self.file_path) if self.file_path else "",
                )

        self.editor._update_tree()
        self.editor.history_manager.push_state(self.editor.entries.copy())
        show_ok(self.dialog, tr("editor_suggestion_applied", "Предложение применено"))
        self.dialog.destroy()

    def _refresh_suggestions(self):
        """Обновляет предложения"""
        self.db.generate_suggestions()
        self._load_suggestions()