# gui/dialogs/glossary_viewer_dialog.py
"""
Диалог просмотра глоссария для редактора переводов.
"""

import tkinter as tk
from tkinter import messagebox, StringVar

import ttkbootstrap as ttk

from gui.gui_i18n import tr
from translation_db import get_translation_db


class GlossaryViewerDialog:
    """Диалог просмотра и применения глоссария"""

    def __init__(self, parent, editor=None, target_language=None):
        self.parent = parent
        self.editor = editor
        self.target_language = target_language or self._get_target_language(parent)
        self.db = get_translation_db(self.target_language)

        if self.db is None:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_db_not_connected", "База переводов не подключена"),
            )
            return

        self._load_colors_config()
        self._create_dialog()
        self._load_glossary()

    def _get_target_language(self, parent):
        try:
            config = getattr(parent, "config", None)
            if config:
                return config.get("target_language", "Russian")
            from config.config_manager import get_config_manager
            return get_config_manager().get("target_language", "Russian")
        except Exception:
            return "Russian"

    def _load_colors_config(self):
        self.colors = self._get_default_colors()
        try:
            from config.config_manager import get_config_manager
            config_mgr = get_config_manager()
            tree_bg = config_mgr.get("glossary_tree_bg")
            tree_fg = config_mgr.get("glossary_tree_fg")
            tree_heading_bg = config_mgr.get("glossary_tree_heading_bg")
            tree_select_bg = config_mgr.get("glossary_tree_select_bg")
            tree_select_fg = config_mgr.get("glossary_tree_select_fg")
            if all(v for v in [tree_bg, tree_fg, tree_heading_bg, tree_select_bg, tree_select_fg]):
                self.colors = {
                    "tree_bg": tree_bg,
                    "tree_fg": tree_fg,
                    "tree_heading_bg": tree_heading_bg,
                    "tree_select_bg": tree_select_bg,
                    "tree_select_fg": tree_select_fg,
                }
        except Exception:
            pass

    def _get_default_colors(self):
        return {
            "tree_bg": "#FFFFFF",
            "tree_fg": "#000000",
            "tree_heading_bg": "#F0F0F0",
            "tree_select_bg": "#0078D4",
            "tree_select_fg": "#FFFFFF",
        }

    def _apply_colors_to_tree(self):
        style = ttk.Style()
        style.configure("Treeview",
            background=self.colors["tree_bg"],
            foreground=self.colors["tree_fg"],
        )
        style.map("Treeview",
            background=[("selected", self.colors["tree_select_bg"])],
            foreground=[("selected", self.colors["tree_select_fg"])],
        )
        style.configure("Treeview.Heading",
            background=self.colors["tree_heading_bg"],
            relief="flat",
        )

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("editor_glossary", "📖 Глоссарий"))
        self.dialog.geometry("700x500")
        self.dialog.minsize(500, 300)
        self.dialog.transient(self.parent)
        
        #  ИСПРАВЛЕНО: Обработчик закрытия для предотвращения зависания
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        # Заголовок
        ttk.Label(
            self.dialog,
            text=tr("editor_glossary", "📖 Глоссарий терминов"),
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=10)

        # Поиск и фильтр по категории
        sf = ttk.Frame(self.dialog)
        sf.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(sf, text=tr("editor_search", "🔍 Поиск:")).pack(side="left")
        self.search_var = StringVar()
        ge = ttk.Entry(sf, textvariable=self.search_var, width=30)
        ge.pack(side="left", padx=5)
        
        #  ОБНОВЛЕНО: Фильтр по категории
        ttk.Label(sf, text=tr("glossary_viewer_category", "Категория:")).pack(side="left", padx=(20, 5))
        self.category_var = StringVar(value="Все")
        category_values = ["Все"]
        try:
            if self.db:
                categories = self.db.get_all_categories()
                category_values.extend(sorted(categories))
        except Exception:
            pass
        self.category_combo = ttk.Combobox(
            sf, textvariable=self.category_var, values=category_values, width=15, state="readonly"
        )
        self.category_combo.pack(side="left", padx=5)
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self._load_glossary(self.search_var.get().lower(), self.category_var.get()))
        
        # Таблица
        cols = ("term", "translation", "category", "mod_name", "description")
        self.gt = ttk.Treeview(self.dialog, columns=cols, show="headings", height=15)
        for c, h in zip(cols, ["Термин", "Перевод", "Категория", "Мод", "Описание"]):
            self.gt.heading(c, text=h)
            self.gt.column(c, width=150)
        self.gt.pack(fill="both", expand=True, padx=10, pady=5)

        self._apply_colors_to_tree()

        # Кнопки
        bf = ttk.Frame(self.dialog)
        bf.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            bf,
            text=tr("editor_apply_selected", "Применить к выбранным"),
            command=self._apply_glossary,
        ).pack(side="left", padx=2)

        ttk.Button(
            bf, text=tr("editor_close", "✖️ Закрыть"), command=self._on_dialog_close
        ).pack(side="right", padx=2)

        # Привязка поиска
        ge.bind("<KeyRelease>", lambda e: self._load_glossary(self.search_var.get().lower(), self.category_var.get()))
        
        #  ИСПРАВЛЕНО: Настройка видимости и grab_set в конце инициализации
        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.deiconify()  #  Убедимся, что окно показано
        self.dialog.grab_set()

    def _load_glossary(self, filter_text="", category_filter=""):
        """Загружает глоссарий в таблицу"""
        for i in self.gt.get_children():
            self.gt.delete(i)

        category_names = self._get_category_names()
        if filter_text:
            items = self.db.search_glossary(filter_text, self.target_language, category=category_filter if category_filter and category_filter != "Все" else None)
        else:
            items = self.db.get_all_glossary(target_language=self.target_language)
            if category_filter and category_filter != "Все":
                items = [i for i in items if self._get_item_category(i) == category_filter]
        for t in items:
            if hasattr(t, "keys"):
                category = t["category"]
                display_category = category_names.get(category, category)
                mod_name = t["mod_name"] if "mod_name" in t.keys() else ""
                description = t["description"] if "description" in t.keys() else ""
                self.gt.insert(
                    "", "end", values=(t["term"], t["translation"], display_category, mod_name, description)
                )
            else:
                category = t.category if hasattr(t, "category") else "general"
                display_category = category_names.get(category, category)
                mod_name = t.mod_name if hasattr(t, "mod_name") else ""
                description = t.description if hasattr(t, "description") else ""
                self.gt.insert(
                    "", "end", values=(t.term, t.translation, display_category, mod_name, description)
                )

    def _get_item_category(self, item):
        """Возвращает категорию из объекта (поддержка dict и Row)"""
        if hasattr(item, "keys"):
            return item["category"]
        return getattr(item, "category", "general")

    def _get_category_names(self):
        try:
            from config.config_manager import get_config_manager
            config_mgr = get_config_manager()
            return config_mgr.get("glossary_category_names", {
                "game": "Игра",
                "user": "Пользователь",
                "auto": "Авто",
                "seed": "Семя",
                "general": "Общий",
            })
        except Exception:
            return {
                "game": "Игра",
                "user": "Пользователь",
                "auto": "Авто",
                "seed": "Семя",
                "general": "Общий",
            }

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

        #  ИСПРАВЛЕНО: Предупреждение о перезаписи ручных правок
        if messagebox.askyesno(
            tr("editor_warning", "Предупреждение"),
            tr("editor_glossary_overwrite", 
                "Применение глоссария заменит текущий текст записей.\n"
                "Если вы вручную редактировали текст, изменения могут быть перезаписаны.\n"
                "Продолжить?")
        ):
            applied_count = 0
            error_count = 0
            for iid in sel:
                k = self.editor.tree.item(iid)["values"][0]
                for e in self.editor.entries:
                    if e["key"] == k:
                        try:
                            e["value"] = self.db.apply_glossary_to_text(e["value"], self.target_language)
                            e["status"] = "complete" if e["value"].strip() else "empty"
                            self.editor.modified = True
                            applied_count += 1
                        except Exception as ex:
                            error_count += 1
                            print(f"[WARNING] Failed to apply glossary to entry {k}: {ex}")
                        break

            self.editor._update_tree()
            self.editor.history_manager.push_state(self.editor.entries.copy())
            
            # Показываем статистику
            msg = tr("editor_glossary_applied", f"Применено к {applied_count} записям")
            if error_count > 0:
                msg += tr("editor_glossary_errors", f"\nОшибок: {error_count}")
            messagebox.showinfo(tr("editor_success", "Готово"), msg)

    def _on_dialog_close(self):
        """Обработчик закрытия диалога (предотвращает зависание grab_set)"""
        try:
            self.dialog.grab_release()
        except Exception:
            pass
        self.dialog.destroy()
