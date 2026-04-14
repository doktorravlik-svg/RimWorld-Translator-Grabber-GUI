# gui/dialogs/file_history_dialog.py
"""
Диалог истории версий файла для редактора переводов.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from gui.gui_i18n import tr
from translation_db import get_translation_db


class FileHistoryDialog:
    """Диалог просмотра и восстановления истории версий файла"""

    def __init__(self, parent, file_path, editor=None):
        """
        Args:
            parent: Родительское окно
            file_path: Путь к файлу
            editor: Ссылка на TranslationEditorDialog для восстановления версий
        """
        self.parent = parent
        self.file_path = file_path
        self.editor = editor
        self.db = get_translation_db()

        if not self.file_path:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_file_not_loaded", "Файл не загружен"),
            )
            return

        if self.db is None:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_db_not_connected", "База переводов не подключена"),
            )
            return

        self._create_dialog()
        self._load_history()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("editor_history_btn", "📜 История версий"))
        self.dialog.geometry("600x400")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Заголовок
        ttk.Label(
            self.dialog,
            text=tr("editor_history_title", "История версий файла"),
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        ttk.Label(self.dialog, text=os.path.basename(self.file_path), font=("Segoe UI", 10)).pack()

        # Таблица истории
        cols = ("version", "entries", "translated", "date")
        self.ht = ttk.Treeview(self.dialog, columns=cols, show="headings", height=12)
        for c, h in zip(cols, ["Версия", "Записей", "Переведено", "Дата"]):
            self.ht.heading(c, text=h)
            self.ht.column(c, width=80)
        self.ht.column("date", width=250)
        self.ht.pack(fill="both", expand=True, padx=10, pady=10)

        # Кнопки
        bf = ttk.Frame(self.dialog)
        bf.pack(fill="x", padx=10, pady=5)

        ttk.Button(bf, text="💾 Сохранить версию", command=self._save_version).pack(
            side="left", padx=2
        )
        ttk.Button(bf, text="↩️ Восстановить", command=self._restore_version).pack(
            side="left", padx=2
        )
        ttk.Button(
            bf, text=tr("editor_close", "✖️ Закрыть"), command=self.dialog.destroy
        ).pack(side="right", padx=2)

    def _load_history(self):
        """Загружает историю версий"""
        for i in self.ht.get_children():
            self.ht.delete(i)

        for v in self.db.get_file_versions(self.file_path):
            self.ht.insert(
                "",
                "end",
                values=(v["version"], v["entries_count"], v["translated_count"], v["created_at"]),
            )

    def _save_version(self):
        """Сохраняет текущую версию"""
        if not self.editor:
            return

        v = self.db.save_file_version(self.file_path, self.editor.entries)
        messagebox.showinfo(
            tr("editor_success", "Успех"),
            tr("editor_version_saved", "Версия {v} сохранена").format(v=v),
        )
        self._load_history()

    def _restore_version(self):
        """Восстанавливает выбранную версию"""
        if not self.editor:
            return

        sel = self.ht.selection()
        if not sel:
            return

        ver = self.ht.item(sel[0])["values"][0]
        if messagebox.askyesno(
            tr("editor_restore", "Восстановить"),
            tr("editor_restore_version", "Восстановить версию {ver}?").format(ver=ver),
        ):
            # Сначала сохраняем текущее состояние
            self.db.save_file_version(self.file_path, self.editor.entries)

            # Загружаем выбранную версию
            data = self.db.get_file_version(self.file_path, ver)
            if data:
                self.editor.entries = data["entries"]
                self.editor.modified = True
                self.editor._update_tree()
                self.editor.history_manager.push_state(self.editor.entries.copy())
                messagebox.showinfo(
                    tr("editor_success", "Успех"),
                    tr("editor_version_restored", "Версия {ver} восстановлена").format(ver=ver),
                )
                self.dialog.destroy()
