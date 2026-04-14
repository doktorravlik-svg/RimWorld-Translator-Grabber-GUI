# gui/dialogs/mass_edit_dialog.py
"""
Диалог массового редактирования для редактора переводов.
"""

import tkinter as tk
from tkinter import StringVar, messagebox, ttk

from gui.gui_i18n import tr


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
            messagebox.showinfo(
                tr("editor_info", "Инфо"),
                tr("editor_select_entries_mass", "Выберите записи для массового редактирования"),
            )
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

        # Таблица выбранных записей
        tf = ttk.LabelFrame(mf, text=tr("editor_selected_entries", "Выбранные записи"))
        tf.pack(fill="both", expand=True, pady=5)
        mt = ttk.Treeview(tf, columns=("key", "value"), show="headings", height=15)
        mt.heading("key", text=tr("editor_key", "Ключ"))
        mt.heading("value", text=tr("editor_current_value", "Текущее значение"))
        mt.column("key", width=200)
        mt.column("value", width=400)

        for iid in self._selected:
            v = self.tree.item(iid)["values"]
            mt.insert(
                "",
                "end",
                values=(
                    v[0],
                    (v[1][:100] + "..." if len(v[1]) > 100 else v[1]),
                ),  # ✅ Увеличен лимит с 50 до 100
            )
        vsb = ttk.Scrollbar(tf, orient="vertical", command=mt.yview)
        mt.configure(yscrollcommand=vsb.set)

        # grid для корректного размещения
        mt.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        # Поле нового значения
        vf = ttk.LabelFrame(mf, text=tr("editor_new_value", "Новое значение"))
        vf.pack(fill="x", pady=5)
        nvt = tk.Text(vf, height=4, wrap="word")
        nvt.pack(fill="x", padx=5, pady=5)

        # Режим редактирования
        mv = StringVar(value="replace")
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

            for iid in self._selected:
                k, ov = self.tree.item(iid)["values"]
                fv = new if mode == "replace" else (ov + new if mode == "append" else new + ov)
                for e in self.entries:
                    if e["key"] == k:
                        e["value"] = fv
                        e["status"] = "complete" if fv.strip() else "empty"
                        cnt += 1
                        break
                self.tree.item(iid, values=(k, fv, e["status"]))

            self.dialog.destroy()
            return cnt

        ttk.Button(bf, text=tr("editor_apply", "✅ Применить"), command=apply).pack(
            side="left", padx=5
        )
        ttk.Button(bf, text=tr("editor_close", "✖️ Закрыть"), command=self.dialog.destroy).pack(
            side="right", padx=5
        )
