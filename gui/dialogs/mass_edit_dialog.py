# gui/dialogs/mass_edit_dialog.py
"""
Диалог массового редактирования для редактора переводов.
"""

import tkinter as tk
from tkinter import ttk

from gui.dialogs.messagebox_helpers import show_info
from gui.gui_i18n import tr
from gui.components.scrollable_tree import ScrollableTree


class MassEditDialog:
    """Диалог массового редактирования записей"""

    def __init__(self, parent, tree, entries, history_manager):
        """
        Args:
            parent: Родительское окно
            tree: Treeview с записями
            entries: Список записей
            history_manager: Менеджер истории
        """
        self.parent = parent
        self.tree = tree
        self.entries = entries
        self.history_manager = history_manager

        self._selected = self.tree.selection()
        if not self._selected:
            show_info(parent, tr("editor_select_entries_mass", "Выберите записи для массового редактирования"))
            return

        self._create_dialog()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(
            f"{tr('editor_mass_edit', '✏️ Массовое редактирование')} ({len(self._selected)} {tr('editor_entries_count2', 'записей')})"
        )
        self.dialog.geometry("700x500")
        self.dialog.minsize(500, 400)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        mf = ttk.Frame(self.dialog, padding=10)
        mf.pack(fill="both", expand=True)

        # Счётчик выбранных записей
        ttk.Label(
            mf,
            text=f"{tr('editor_selected_entries', 'Выбрано записей')}: {len(self._selected)}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=5)

        # Таблица выбранных записей (используем ScrollableTree)
        tf = ttk.LabelFrame(mf, text=tr("editor_selected_entries", "Выбранные записи"))
        tf.pack(fill="both", expand=True, pady=5)

        st_wrapper = ScrollableTree(
            tf,
            columns=("key", "value"),
            headings={"key": tr("editor_key", "Ключ"), "value": tr("editor_current_value", "Текущее значение")},
            column_widths={"key": 200, "value": 400},
            height=15,
        )
        self.selected_tree = st_wrapper.tree
        st_wrapper.pack(fill="both", expand=True)

        for iid in self._selected:
            v = self.tree.item(iid)["values"]
            display_val = (v[1][:100] + "..." if len(v[1]) > 100 else v[1])
            st_wrapper.insert("", "end", values=(v[0], display_val))

        # Поле нового значения
        vf = ttk.LabelFrame(mf, text=tr("editor_new_value", "Новое значение"))
        vf.pack(fill="x", pady=5)
        nvt = tk.Text(vf, height=4, wrap="word")
        nvt.pack(fill="x", padx=5, pady=5)

        # Режим редактирования
        mv = tk.StringVar(value="replace")
        rbf = ttk.Frame(mf)
        rbf.pack(fill="x", pady=5)
        ttk.Radiobutton(
            rbf, text=tr("editor_replace_all_mode", "Заменить все"), variable=mv, value="replace"
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            rbf, text=tr("editor_append", "Добавить в конец"), variable=mv, value="append"
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            rbf, text=tr("editor_prepend", "Вставить в начало"), variable=mv, value="prepend"
        ).pack(side="left", padx=5)

        # Кнопки
        bf = ttk.Frame(mf)
        bf.pack(fill="x", pady=5)

        def apply():
            new = nvt.get("1.0", tk.END).strip()
            mode = mv.get()
            cnt = 0

            # Создаём быстрый индекс для O(1) поиска
            entries_map = {e["key"]: e for e in self.entries}

            for iid in self._selected:
                k, ov = self.tree.item(iid)["values"]
                fv = new if mode == "replace" else (ov + new if mode == "append" else new + ov)

                if k in entries_map:
                    e = entries_map[k]
                    e["value"] = fv
                    e["status"] = "complete" if fv.strip() else "empty"
                    cnt += 1

                self.tree.item(iid, values=(k, fv))

            self.dialog.destroy()
            return cnt

        ttk.Button(bf, text=tr("editor_apply", "✅ Применить"), command=apply).pack(
            side="left", padx=5
        )
        ttk.Button(bf, text=tr("editor_close", "✖️ Закрыть"), command=self.dialog.destroy).pack(
            side="right", padx=5
        )