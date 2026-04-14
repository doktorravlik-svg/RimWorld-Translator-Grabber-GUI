import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as ttk
from config.language_constants import SUPPORTED_LANGUAGES
from gui.constants import (
    PAD_BTN_X,
    PAD_ENTRY_X,
    PAD_FRAME_X,
    PAD_FRAME_Y,
    PAD_LABEL_X,
    PAD_TREE_X,
    PAD_TREE_Y,
    PAD_X,
    PAD_Y,
    PROGRESS_BOOTSTYLES,
)
from gui.gui_i18n import tr
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip


class VerificationTab(ttk.Frame):
    def __init__(self, parent, on_verify_callback=None, on_full_verify_callback=None):
        super().__init__(parent)
        self.on_verify_callback = on_verify_callback
        self.on_full_verify_callback = on_full_verify_callback
        self.report_format_var = tk.StringVar(value="text")
        self.verify_translations_var = tk.BooleanVar(value=True)
        self.verify_dependencies_var = tk.BooleanVar(value=True)
        self.verify_conflicts_var = tk.BooleanVar(value=True)
        self.verification_results = []
        self.show_errors_var = tk.BooleanVar(value=True)
        self.show_warnings_var = tk.BooleanVar(value=True)
        self.show_info_var = tk.BooleanVar(value=False)
        # ✅ НОВОЕ: Фильтр по языку верификации
        self.verification_language_var = tk.StringVar(value="Все языки")
        self._verify_filter_debounce_timer = None  # Debounce таймер
        self._all_result_items = []  # Все элементы дерева для фильтрации
        self._setup_ui()

    def _setup_ui(self):
        options_frame = ttk.LabelFrame(
            self, text=tr("verification_settings", "Настройки верификации")
        )
        options_frame.grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )
        ttk.Label(options_frame, text=tr("report_format", "Формат отчёта:")).grid(
            row=0, column=0, sticky="w", padx=PAD_X, pady=PAD_Y
        )
        self.report_format_combo = ttk.Combobox(
            options_frame,
            textvariable=self.report_format_var,
            values=["text", "json", "html"],
            width=15,
        )
        self.report_format_combo.grid(row=0, column=1, sticky="w", padx=PAD_X, pady=PAD_Y)
        ToolTip(self.report_format_combo, "Выберите формат экспорта отчёта")

        checks_frame = ttk.Frame(options_frame)
        checks_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=PAD_X, pady=PAD_Y)
        chk_trans = ttk.Checkbutton(
            checks_frame,
            text=tr("check_translations", "✅ Проверка переводов"),
            variable=self.verify_translations_var,
        )
        chk_trans.pack(anchor="w", side="left", padx=PAD_X)
        ToolTip(chk_trans, "Проверить качество переводов модов")

        chk_deps = ttk.Checkbutton(
            checks_frame,
            text=tr("check_dependencies", "🔗 Проверка зависимостей"),
            variable=self.verify_dependencies_var,
        )
        chk_deps.pack(anchor="w", side="left", padx=PAD_X)
        ToolTip(chk_deps, "Проверить отсутствие зависимостей модов")

        chk_conflicts = ttk.Checkbutton(
            checks_frame,
            text=tr("check_conflicts", "⚠️ Обнаружение конфликтов"),
            variable=self.verify_conflicts_var,
        )
        chk_conflicts.pack(anchor="w", side="left", padx=PAD_X)
        ToolTip(chk_conflicts, "Найти конфликтующие моды")

        # ✅ НОВОЕ: Фильтр по языку верификации
        lang_frame = ttk.Frame(options_frame)
        lang_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=PAD_X, pady=PAD_Y)
        ttk.Label(lang_frame, text=tr("verify_language", "🌐 Язык верификации:")).pack(
            side="left", padx=PAD_LABEL_X
        )
        # Список языков: "Все языки" + все поддерживаемые
        lang_values = ["Все языки"] + list(SUPPORTED_LANGUAGES)
        self.verification_language_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.verification_language_var,
            values=lang_values,
            width=20,
            state="readonly",
        )
        self.verification_language_combo.pack(side="left", padx=PAD_X)
        ToolTip(
            self.verification_language_combo,
            "Выберите язык для проверки переводов. 'Все языки' — проверять все.",
        )

        # ✅ НОВОЕ: Checkbox для фильтрации переводов по языку при проверке целостности
        self.filter_integrity_by_lang_var = tk.BooleanVar(value=False)
        chk_filter_integrity = ttk.Checkbutton(
            options_frame,
            text=tr("filter_integrity_by_lang", "🌐 Фильтровать проверку целостности по языку"),
            variable=self.filter_integrity_by_lang_var,
        )
        chk_filter_integrity.grid(row=3, column=0, columnspan=3, sticky="w", padx=PAD_X, pady=PAD_Y)
        ToolTip(
            chk_filter_integrity,
            "Если отмечено, проверка целостности будет проверять только файлы выбранного языка",
        )

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=PAD_FRAME_Y)
        self.verify_btn = ttk.Button(
            btn_frame,
            text=tr("verify_mods", "✅ Верификация модов"),
            command=self._on_verify,
            bootstyle="success",
        )
        self.verify_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(self.verify_btn, "Быстрая проверка выбранных модов")

        self.full_verify_btn = ttk.Button(
            btn_frame,
            text=tr("full_check", "🔍 Полная проверка"),
            command=self._on_full_verify,
            bootstyle="info",
        )
        self.full_verify_btn.pack(side="left", padx=PAD_BTN_X)
        ToolTip(self.full_verify_btn, "Полная проверка всех модов")

        # Прогресс верификации — нативный Progressbar с bootstyle
        progress_frame = ttk.Frame(self)
        progress_frame.grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            bootstyle=PROGRESS_BOOTSTYLES["verification"],
        )
        self.progress_bar.pack(fill="x", padx=PAD_X, pady=3)
        self.progress_label = ttk.Label(
            progress_frame, text=tr("ready_to_check", "✅ Готов к проверке")
        )
        self.progress_label.pack(anchor="w", padx=PAD_X, pady=(0, 3))

        # Поиск по результатам
        search_frame = ttk.Frame(self)
        search_frame.grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=PAD_FRAME_X, pady=PAD_FRAME_Y
        )
        ttk.Label(search_frame, text="🔍 Поиск:").pack(side="left", padx=PAD_LABEL_X)
        self.verify_search_var = tk.StringVar()
        self.verify_search_entry = ttk.Entry(
            search_frame, textvariable=self.verify_search_var, bootstyle="info"
        )
        self.verify_search_entry.pack(side="left", fill="x", expand=True, padx=PAD_ENTRY_X)
        # ✅ ИСПРАВЛЕНО: Debounce для поиска (300мс задержка)
        self._verify_filter_debounce_timer = None
        self.verify_search_entry.bind("<KeyRelease>", self._on_verify_filter_debounced)
        ToolTip(self.verify_search_entry, "Введите текст для фильтрации результатов")
        ttk.Button(
            search_frame,
            text="✕",
            width=3,
            command=self._clear_verify_search,
            bootstyle="secondary",
        ).pack(side="left", padx=(0, 5))

        filter_frame = ttk.Frame(self)
        filter_frame.grid(row=4, column=0, columnspan=3, sticky="w", padx=PAD_FRAME_X, pady=PAD_Y)
        ttk.Label(filter_frame, text=tr("show", "Показать:")).pack(side="left", padx=PAD_LABEL_X)
        chk_err = ttk.Checkbutton(
            filter_frame,
            text=tr("errors", "❌ Ошибки"),
            variable=self.show_errors_var,
            command=self._apply_filters,
        )
        chk_err.pack(side="left", padx=PAD_X)
        ToolTip(chk_err, "Показать только ошибки")

        chk_warn = ttk.Checkbutton(
            filter_frame,
            text=tr("warnings", "⚠️ Предупреждения"),
            variable=self.show_warnings_var,
            command=self._apply_filters,
        )
        chk_warn.pack(side="left", padx=PAD_X)
        ToolTip(chk_warn, "Показать только предупреждения")

        chk_info = ttk.Checkbutton(
            filter_frame,
            text=tr("info_filter", "ℹ️ Информация"),
            variable=self.show_info_var,
            command=self._apply_filters,
        )
        chk_info.pack(side="left", padx=PAD_X)
        ToolTip(chk_info, "Показать информационные сообщения")

        export_frame = ttk.Frame(self)
        export_frame.grid(row=5, column=0, columnspan=3, sticky="e", padx=PAD_FRAME_X, pady=PAD_Y)
        btn_export_txt = ttk.Button(
            export_frame,
            text=tr("export_txt", "💾 Экспорт TXT"),
            command=lambda: self._export_report("txt"),
            bootstyle="info",
        )
        btn_export_txt.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_export_txt, "Экспортировать отчёт в TXT")

        btn_export_json = ttk.Button(
            export_frame,
            text=tr("export_json", "📊 Экспорт JSON"),
            command=lambda: self._export_report("json"),
            bootstyle="info",
        )
        btn_export_json.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_export_json, "Экспортировать отчёт в JSON")

        btn_export_html = ttk.Button(
            export_frame,
            text=tr("export_html", "🌐 Экспорт HTML"),
            command=lambda: self._export_report("html"),
            bootstyle="info",
        )
        btn_export_html.pack(side="left", padx=PAD_BTN_X)
        ToolTip(btn_export_html, "Экспортировать отчёт в HTML")

        tree_frame = ttk.LabelFrame(self, text=tr("verification_results", "📋 Результаты проверки"))
        tree_frame.grid(
            row=6, column=0, columnspan=3, padx=PAD_TREE_X, pady=PAD_TREE_Y, sticky="nsew"
        )

        # ✅ ИСПОЛЬЗУЕМ переиспользуемый компонент ScrollableTree
        from gui.components.scrollable_tree import ScrollableTree

        columns = ("type", "mod", "message")
        # ✅ УВЕЛИЧЕНО height с 12 до 25 для большего окна результатов
        self.result_tree_widget = ScrollableTree(
            tree_frame,
            columns=columns,
            headings={
                "type": tr("type", "Тип"),
                "mod": tr("mod", "Мод"),
                "message": tr("message", "Сообщение"),
            },
            column_widths={"type": 80, "mod": 150, "message": 500},
            height=25,
        )
        # ✅ Упаковываем ScrollableTree
        self.result_tree_widget.pack(fill="both", expand=True)
        self.result_tree_widget.tree.tag_configure(
            "error", background="#ff4444", foreground="white"
        )
        self.result_tree_widget.tree.tag_configure(
            "warning", background="#ffaa00", foreground="black"
        )
        self.result_tree_widget.tree.tag_configure("info", background="#4444ff", foreground="white")
        self.result_tree_widget.tree.tag_configure(
            "success", background="#44aa44", foreground="white"
        )
        # ✅ НОВОЕ: Цвет для DLC зависимостей
        self.result_tree_widget.tree.tag_configure("dlc", background="#9b59b6", foreground="white")

        # Контекстное меню для результатов
        self.result_tree_widget.tree.bind("<Button-3>", self._show_context_menu)

        # Псевдоним для обратной совместимости
        self.result_tree = self.result_tree_widget.tree

        # ✅ НОВОЕ: Статистика без LabelFrame — экономия места
        self.stats_label = ttk.Label(
            self,
            text=tr("check_not_performed", "Проверка не проводилась"),
            bootstyle="secondary",
        )
        self.stats_label.grid(row=7, column=0, columnspan=3, sticky="w", padx=PAD_FRAME_X, pady=2)

        # ✅ УДАЛЕНО: result_text и "Детальный отчёт" — дублировали дерево
        # self.result_text = scrolledtext.ScrolledText(...)
        # ttk.Label(self, text=tr("detailed_report", "Детальный отчёт:"))

        # ✅ НОВОЕ: rowconfigure только для дерева
        self.rowconfigure(6, weight=1)  # Дерево забирает всё пространство
        self.rowconfigure(7, weight=0)  # Статистика фиксированная
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

    def _on_verify_filter_debounced(self, event=None):
        """Debounce для фильтрации результатов (300мс задержка)"""
        if self._verify_filter_debounce_timer:
            self.after_cancel(self._verify_filter_debounce_timer)
        self._verify_filter_debounce_timer = self.after(300, self._filter_results)

    def _filter_results(self, event=None):
        """Фильтрация результатов верификации по поисковому запросу"""
        try:
            if not hasattr(self, "result_tree") or self.result_tree is None:
                return
            search_text = self.verify_search_var.get().lower()

            # Итерируемся по ВСЕМ элементам (не только видимым)
            for item in self._all_result_items:
                values = self.result_tree.item(item, "values")
                if not values:
                    continue
                # Ищем во всех колонках
                match = any(search_text in str(v).lower() for v in values)
                if not search_text or match:
                    self.result_tree.reattach(item, "", "end")
                else:
                    self.result_tree.detach(item)
        except Exception:
            # Тихо игнорируем ошибки фильтрации — не ломаем UI
            pass

    def _clear_verify_search(self):
        """Очистить поиск и показать все результаты"""
        try:
            if not hasattr(self, "result_tree") or self.result_tree is None:
                return
            self.verify_search_var.set("")
            for item in self._all_result_items:
                self.result_tree.reattach(item, "", "end")
        except Exception:
            pass

    def _on_verify(self):
        if self.on_verify_callback:
            from utils.ui_helpers import create_debounced_progress

            root = self.winfo_toplevel()
            self._progress_updater = create_debounced_progress(self, root=root, delay_ms=150)
            self.progress_var.set(0)
            self.progress_label.config(text=tr("starting_verification", "Запуск верификации..."))
            self._clear_results()
            self.on_verify_callback(self.get_options())

    def _on_full_verify(self):
        if self.on_full_verify_callback:
            from utils.ui_helpers import create_debounced_progress

            root = self.winfo_toplevel()
            self._progress_updater = create_debounced_progress(self, root=root, delay_ms=150)
            self.progress_var.set(0)
            self.progress_label.config(text=tr("starting_full_check", "Запуск полной проверки..."))
            self._clear_results()
            self.on_full_verify_callback(self.get_options())

    def update_progress(self, value, message=""):
        """Обновить прогресс верификации с debounce."""
        if hasattr(self, "_progress_updater") and self._progress_updater:
            self._progress_updater.update(value, message)
        else:
            self.progress_var.set(value)
            if message:
                self.progress_label.config(text=message)

    def finish_verification(self, success=True):
        """Завершить верификацию с очисткой debounced updater."""
        if hasattr(self, "_progress_updater") and self._progress_updater:
            self._progress_updater.finish(success)
            self._progress_updater = None
        elif success:
            self.progress_var.set(100)
            self.progress_label.config(
                text=tr("verification_completed", "✅ Верификация завершена")
            )
        else:
            self.progress_label.config(
                text=tr("verification_completed_with_errors", "❌ Верификация завершена с ошибками")
            )

    def get_options(self):
        return {
            "format": self.report_format_var.get(),
            "verify_translations": self.verify_translations_var.get(),
            "verify_dependencies": self.verify_dependencies_var.get(),
            "verify_conflicts": self.verify_conflicts_var.get(),
            # ✅ НОВОЕ: Язык верификации
            "verification_language": self.verification_language_var.get(),
            # ✅ НОВОЕ: Фильтровать проверку целостности по языку
            "filter_integrity_by_language": self.filter_integrity_by_lang_var.get(),
        }

    def log(self, message):
        """Одно сообщение в лог (обратная совместимость)"""
        # ✅ НОВОЕ: result_text удалён, log больше не используется
        self._parse_and_add_result(message)

    def log_batch(self, messages):
        """Пакетная вставка результатов — БЕЗ подвисания.

        Вставляет все сообщения за один проход:
        - Treeview — пакетная вставка
        - _apply_filters — один раз в конце
        """
        if not messages:
            return

        # 1. Treeview — пакетная вставка
        results_to_add = []
        for message in messages:
            if message.startswith("❌") or "ERROR" in message.upper():
                result_type = "error"
                icon = "❌"
            elif message.startswith("⚠️") or "WARNING" in message.upper():
                result_type = "warning"
                icon = "⚠️"
            elif message.startswith("✅"):
                result_type = "success"
                icon = "✅"
            else:
                result_type = "info"
                icon = "ℹ️"

            mod_name = tr("system", "Система")
            if ":" in message:
                parts = message.split(":", 1)
                if len(parts) == 2:
                    mod_name = parts[0].strip()
                    message = parts[1].strip()

            result = {
                "type": result_type,
                "mod": mod_name,
                "message": message,
                "icon": icon,
            }
            results_to_add.append(result)
            self.verification_results.append(result)
            item_id = self.result_tree.insert(
                "",
                "end",
                values=(f"{icon} {result_type.upper()}", mod_name, message),
                tags=(result_type,),
            )
            self._all_result_items.append(item_id)  # Сохраняем для фильтрации

        # 3. Статистика и фильтры — ОДИН раз в конце
        self._update_stats()
        self._apply_filters()

    def _parse_and_add_result(self, message):
        if message.startswith("❌") or "ERROR" in message.upper():
            result_type = "error"
            icon = "❌"
        elif message.startswith("⚠️") or "WARNING" in message.upper():
            result_type = "warning"
            icon = "⚠️"
        elif message.startswith("✅"):
            result_type = "success"
            icon = "✅"
        else:
            result_type = "info"
            icon = "ℹ️"
        mod_name = tr("system", "Система")
        if ":" in message:
            parts = message.split(":", 1)
            if len(parts) == 2:
                mod_name = parts[0].strip()
                message = parts[1].strip()
        result = {
            "type": result_type,
            "mod": mod_name,
            "message": message,
            "icon": icon,
        }
        self.verification_results.append(result)
        item_id = self.result_tree.insert(
            "",
            "end",
            values=(f"{icon} {result_type.upper()}", mod_name, message),
            tags=(result_type,),
        )
        self._all_result_items.append(item_id)  # Сохраняем для фильтрации
        # Обновляем статистику
        self._update_stats()
        # Применяем фильтры
        self._apply_filters()

    def _clear_results(self):
        """Очистить все результаты"""
        self.verification_results.clear()
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self._all_result_items.clear()  # Очищаем список всех элементов
        # ✅ УДАЛЕНО: result_text больше не существует
        # self.result_text.delete(1.0, tk.END)
        self.stats_label.config(text=tr("check_not_performed", "Проверка не проводилась"))

    def clear(self):
        self._clear_results()

    def _apply_filters(self):
        """Применить фильтры к результатам верификации"""
        # Итерируемся по ВСЕМ элементам (не только видимым)
        for item in self._all_result_items:
            values = self.result_tree.item(item, "values")
            if not values:
                continue
            result_type = values[0].lower()
            show = False
            if "error" in result_type and self.show_errors_var.get():
                show = True
            elif "warning" in result_type and self.show_warnings_var.get():
                show = True
            elif "info" in result_type and self.show_info_var.get():
                show = True
            elif "success" in result_type:
                show = True
            if show:
                self.result_tree.reattach(item, "", "end")
            else:
                self.result_tree.detach(item)

    def _update_stats(self):
        total = len(self.verification_results)
        errors = sum(1 for r in self.verification_results if r["type"] == "error")
        warnings = sum(1 for r in self.verification_results if r["type"] == "warning")
        successes = sum(1 for r in self.verification_results if r["type"] == "success")
        self.stats_label.config(
            text=f"{tr('stats_total', 'Всего')}: {total} | {tr('stats_success', '✅ Успешно')}: {successes} | "
            f"{tr('stats_warnings', '⚠️ Предупреждения')}: {warnings} | {tr('stats_errors', '❌ Ошибки')}: {errors}"
        )

    def _export_report(self, format_type):
        """Экспортировать отчёт в файл"""
        if not self.verification_results:
            from tkinter import messagebox

            messagebox.showwarning(
                tr("warning", "Предупреждение"),
                tr("no_results_to_export", "Нет результатов для экспорта"),
            )
            return
        if format_type == "txt":
            filetypes = [("Text files", "*.txt")]
            default_ext = ".txt"
        elif format_type == "json":
            filetypes = [("JSON files", "*.json")]
            default_ext = ".json"
        elif format_type == "html":
            filetypes = [("HTML files", "*.html")]
            default_ext = ".html"
        else:
            return
        file_path = filedialog.asksaveasfilename(
            title=tr("save_report", "Сохранить отчёт"),
            defaultextension=default_ext,
            filetypes=filetypes,
        )
        if not file_path:
            return

        # Debug: логируем экспорт отчёта
        if self.log_callback:
            self.log_callback(f"[DEBUG] Экспорт отчёта верификации: {format_type} -> {file_path}")

        try:
            if format_type == "txt":
                self._export_txt(file_path)
            elif format_type == "json":
                self._export_json(file_path)
            elif format_type == "html":
                self._export_html(file_path)
            from tkinter import messagebox

            messagebox.showinfo(
                tr("success", "Успех"), f"{tr('report_saved', 'Отчёт сохранён')}\n{file_path}"
            )
        except Exception as e:
            from tkinter import messagebox

            messagebox.showerror(
                tr("error", "Ошибка"), f"{tr('report_save_error', 'Ошибка сохранения отчёта')}\n{e}"
            )

    def _export_txt(self, file_path):
        self._get_exporter().export_txt(file_path)

    def _export_json(self, file_path):
        self._get_exporter().export_json(file_path)

    def _export_html(self, file_path):
        self._get_exporter().export_html(file_path)

    def _get_exporter(self):
        """Получить экземпляр ReportExporter"""
        from gui.components.report_exporter import ReportExporter

        return ReportExporter(
            data=self.verification_results,
            title=tr("verification_report", "Отчёт верификации RimWorld Translator Grabber"),
            columns=("Тип", "Мод", "Сообщение"),
        )

    def _show_context_menu(self, event):
        """Показать контекстное меню для дерева результатов"""
        item = self.result_tree.identify_row(event.y)
        if not item:
            return

        self.result_tree.selection_set(item)
        values = self.result_tree.item(item, "values")
        if not values:
            return

        mod_name = values[1] if len(values) > 1 else ""
        message = values[2] if len(values) > 2 else ""

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="📋 Копировать сообщение", command=lambda: self._copy_to_clipboard(message)
        )
        if mod_name:
            menu.add_command(
                label="📋 Копировать имя мода", command=lambda: self._copy_to_clipboard(mod_name)
            )

        menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text: str):
        """Копировать текст в буфер обмена"""
        self.clipboard_clear()
        self.clipboard_append(text)

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
        pass
