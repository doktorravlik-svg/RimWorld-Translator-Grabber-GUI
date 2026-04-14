# gui/dialogs/integrity_results_dialog.py
"""
Диалог результатов проверки целостности.

Отображает:
- Сводку проверки (файлов проверено, ошибок, предупреждений)
- Дерево ошибок с фильтрацией
- Кнопки: Копировать путь, Открыть папку, Экспорт отчёта
"""

import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class IntegrityResultsDialog:
    """Диалог с результатами проверки целостности"""

    def __init__(self, parent, result, log_messages=None):
        """
        Args:
            parent: Родительское окно
            result: IntegrityResultDTO из IntegrityWorker
            log_messages: Список сообщений лога (опционально)
        """
        self.parent = parent
        self.result = result
        self.log_messages = log_messages or []

        self.dialog = ttk.Toplevel(parent)
        self.dialog.title("Результаты проверки целостности")
        self.dialog.geometry("1200x650")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Внешний словарь для хранения данных элементов (tree.insert не поддерживает data=)
        self._item_data = {}
        self._tooltip = None

        # Центрирование
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 1200) // 2
        y = (self.dialog.winfo_screenheight() - 650) // 2
        self.dialog.geometry(f"1200x650+{x}+{y}")

        self._build_ui()
        self._populate_results()

    def _build_ui(self):
        """Построить интерфейс"""
        # ── Сводка ──
        summary_frame = ttk.LabelFrame(self.dialog, text="📊 Сводка")
        summary_frame.pack(fill="x", padx=10, pady=5)

        success = getattr(self.result, "success", True)
        files_checked = getattr(self.result, "files_checked", 0)
        files_valid = getattr(self.result, "files_valid", 0)
        files_invalid = getattr(self.result, "files_invalid", 0)
        warnings = getattr(self.result, "warnings", 0)

        status_icon = "✅" if success else "❌"
        status_text = "Проверка пройдена" if success else "Обнаружены проблемы"
        status_color = "success" if success else "danger"

        ttk.Label(
            summary_frame,
            text=f"{status_icon} {status_text}",
            font=("Segoe UI", 12, "bold"),
            bootstyle=status_color,
        ).pack(anchor="w", padx=10, pady=(5, 0))

        stats_frame = ttk.Frame(summary_frame)
        stats_frame.pack(fill="x", padx=10, pady=5)

        stats = [
            ("Проверено файлов:", str(files_checked), "#3b82f6"),
            ("Корректных:", str(files_valid), "#22c55e"),
            ("С ошибками:", str(files_invalid), "#ef4444"),
            ("Предупреждений:", str(warnings), "#f59e0b"),
        ]

        for label, value, color in stats:
            row = ttk.Frame(stats_frame)
            row.pack(side="left", padx=10)
            ttk.Label(row, text=label, font=("Segoe UI", 9)).pack(side="left")
            ttk.Label(row, text=value, font=("Segoe UI", 9, "bold"), foreground=color).pack(
                side="left", padx=(3, 0)
            )

        # ── Фильтры ──
        filter_frame = ttk.Frame(self.dialog)
        filter_frame.pack(fill="x", padx=10, pady=5)

        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(
            filter_frame,
            text="Все",
            variable=self.filter_var,
            value="all",
            command=self._apply_filter,
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            filter_frame,
            text="❌ Ошибки",
            variable=self.filter_var,
            value="error",
            command=self._apply_filter,
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            filter_frame,
            text="⚠️ Предупреждения",
            variable=self.filter_var,
            value="warning",
            command=self._apply_filter,
        ).pack(side="left", padx=5)

        ttk.Label(
            filter_frame,
            text=f"Показано: {files_invalid + warnings} из {files_invalid + warnings}",
            font=("Segoe UI", 8),
            foreground="gray",
        ).pack(side="right", padx=10)

        self.count_label = filter_frame.winfo_children()[-1]

        # ── Дерево результатов ──
        tree_frame = ttk.LabelFrame(self.dialog, text="Детали")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("type", "file", "description")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.tree.heading("type", text="Тип")
        self.tree.heading("file", text="Файл")
        self.tree.heading("description", text="Описание")

        # ✅ ИСПРАВЛЕНО: Увеличены ширины и включено растягивание колонок
        self.tree.column("type", width=120, minwidth=80, anchor="center", stretch=False)
        self.tree.column("file", width=500, minwidth=250, anchor="w", stretch=True)
        self.tree.column("description", width=550, minwidth=300, anchor="w", stretch=True)

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # grid для корректного размещения
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # ✅ НОВОЕ: Middle Ellipsis — интеллектуальное сокращение длинного текста
        self._max_file_len = 45  # Максимальная длина пути в ячейке
        self._max_desc_len = 65  # Максимальная длина описания в ячейке

        # Цвета
        self.tree.tag_configure("error", foreground="#ef4444")
        self.tree.tag_configure("warning", foreground="#f59e0b")

        # Контекстное меню
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", self._open_selected_file)
        # ✅ НОВОЕ: Тултип при наведении для показа полного текста
        self.tree.bind("<Motion>", self._show_cell_tooltip)
        self.tree.bind("<Leave>", self._hide_tooltip)

        # ── Кнопки ──
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(
            btn_frame, text="📋 Копировать отчёт", command=self._copy_report, bootstyle="info"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame, text="💾 Экспорт в файл", command=self._export_report, bootstyle="secondary"
        ).pack(side="left", padx=2)

        ttk.Button(
            btn_frame, text="📂 Открыть папку", command=self._open_folder, bootstyle="info"
        ).pack(side="left", padx=2)

        ttk.Separator(btn_frame, orient="vertical").pack(side="left", padx=10, fill="y")

        ttk.Button(
            btn_frame, text="✖ Закрыть", command=self.dialog.destroy, bootstyle="danger"
        ).pack(side="right", padx=2)

    def _middle_ellipsis(self, text, max_len):
        """Интеллектуальное сокращение с многоточием в середине"""
        if len(text) <= max_len:
            return text
        # Показываем начало и конец текста с "..." в середине
        # Например: "F:/Games/RimWor...e 3, column 5"
        head_len = max_len // 2 - 2  # Длина начала
        tail_len = max_len - head_len - 3  # Длина конца
        return text[:head_len] + "..." + text[-tail_len:]

    def _populate_results(self):
        """Заполнить дерево результатами"""
        self.all_items = []  # Для фильтрации — храним IID элементов

        errors = getattr(self.result, "errors", [])
        details = getattr(self.result, "details", [])

        # ✅ ИСПРАВЛЕНО: Парсим ошибки с Middle Ellipsis
        for item in errors:
            file_path = self._extract_path(item)
            description = item.strip()
            # ✅ Middle Ellipsis для отображения в ячейках
            display_path = self._middle_ellipsis(file_path, self._max_file_len)
            display_desc = self._middle_ellipsis(description, self._max_desc_len)
            iid = self.tree.insert(
                "",
                "end",
                values=("❌ Ошибка", display_path, display_desc),
                tags=("error",),
            )
            self._item_data[iid] = {"type": "error", "file": file_path, "full_desc": description}
            self.all_items.append(iid)

        # ✅ ИСПРАВЛЕНО: Парсим предупреждения с Middle Ellipsis
        for item in details:
            if "⚠️" in item or "Предупреждение" in item:
                file_path = self._extract_path(item)
                description = item.strip()
                # ✅ Middle Ellipsis для отображения в ячейках
                display_path = self._middle_ellipsis(file_path, self._max_file_len)
                display_desc = self._middle_ellipsis(description, self._max_desc_len)
                iid = self.tree.insert(
                    "",
                    "end",
                    values=("⚠️ Предупр.", display_path, display_desc),
                    tags=("warning",),
                )
                self._item_data[iid] = {
                    "type": "warning",
                    "file": file_path,
                    "full_desc": description,
                }
                self.all_items.append(iid)

        self._update_count()

    def _extract_path(self, text):
        """Извлечь путь из текста ошибки"""
        import re

        # ✅ ИСПРАВЛЕНО: Более точные паттерны для извлечения путей
        # Паттерн 1: "Ошибка XML: F:/Games/.../file.xml - <error>"
        # Паттерн 2: "Нет прав на чтение: F:/Games/.../file.xml"
        # Паттерн 3: "Пустой файл: F:/Games/.../file.xml"

        # Сначала ищем путь после ": " — это общий префикс для всех сообщений
        # Захватываем всё после ": " до " - " или конца строки
        match = re.search(r":\s*([A-Za-z]:[/\\][^\n]+?)(?:\s+-\s+|$)", text)
        if match:
            path = match.group(1).strip()
            # Убираем возможные артефакты в конце (если путь обрезан)
            # Оставляем только путь к XML файлу
            xml_match = re.search(r"([A-Za-z]:[/\\].+\.xml)", path, re.IGNORECASE)
            if xml_match:
                return xml_match.group(1)
            return path

        # Паттерн 4: Windows UNC пути (\\server\share\...)
        match = re.search(r'(\\\\[^\s:]+(?:\\[^\\/:*?"<>|\r\n]+)*\.xml)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Если не нашли — возвращаем сокращённый текст
        return text[:150] + "..." if len(text) > 150 else text

    def _apply_filter(self):
        """Применить фильтр к дереву"""
        filter_type = self.filter_var.get()
        shown = 0

        # ✅ ИСПРАВЛЕНО: Используем detach/reattach вместо delete/insert
        # Это сохраняет IID элементов и их данные в _item_data
        for iid in self.all_items:
            try:
                data = self._item_data.get(iid, {})
                item_type = data.get("type", "")

                if filter_type == "all":
                    self.tree.reattach(iid, "", "end")
                    shown += 1
                elif filter_type == "error" and item_type == "error":
                    self.tree.reattach(iid, "", "end")
                    shown += 1
                elif filter_type == "warning" and item_type == "warning":
                    self.tree.reattach(iid, "", "end")
                    shown += 1
                else:
                    self.tree.detach(iid)
            except tk.TclError:
                # Элемент больше не существует — пропускаем
                continue

        self.count_label.config(text=f"Показано: {shown}")

    def _update_count(self):
        """Обновить счётчик элементов"""
        count = len(self.tree.get_children())
        self.count_label.config(text=f"Показано: {count}")

    # ── Контекстное меню ──

    def _show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        self.tree.selection_set(item)
        data = self._item_data.get(item, {})
        file_path = data.get("file", "")

        menu = tk.Menu(self.dialog, tearoff=0)

        if file_path and os.path.exists(file_path):
            menu.add_command(label="📂 Открыть файл", command=lambda: self._open_file(file_path))
            menu.add_command(
                label="📁 Открыть папку", command=lambda: self._open_file_folder(file_path)
            )

        menu.add_separator()
        menu.add_command(label="📋 Копировать путь", command=lambda: self._copy_path(file_path))

        menu.post(event.x_root, event.y_root)

    def _open_selected_file(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        data = self._item_data.get(sel[0], {})
        file_path = data.get("file", "")
        if file_path and os.path.exists(file_path):
            self._open_file(file_path)

    def _open_file(self, file_path):
        """Открыть файл"""
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", file_path])
        else:
            subprocess.run(["xdg-open", file_path])

    def _open_file_folder(self, file_path):
        """Открыть папку файла"""
        folder = os.path.dirname(file_path)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])

    def _copy_path(self, file_path):
        """Копировать путь в буфер"""
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(file_path)

    def _open_folder(self):
        """Открыть папку из первого результата"""
        for item in self.tree.get_children():
            data = self._item_data.get(item, {})
            file_path = data.get("file", "")
            if file_path and os.path.exists(file_path):
                self._open_file_folder(file_path)
                return

        messagebox.showinfo("Информация", "Нет доступных файлов для открытия")

    # ── Тултипы для ячеек ──

    def _show_cell_tooltip(self, event):
        """Показывает тултип с полным текстом ячейки при наведении"""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            self._hide_tooltip()
            return

        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        if not item or not col:
            self._hide_tooltip()
            return

        # Маппинг колонок: #1 -> type, #2 -> file, #3 -> description
        col_map = {"#1": "type", "#2": "file", "#3": "description"}
        col_id = col_map.get(col)

        if col_id:
            # ✅ НОВОЕ: Для колонки "Описание" берем полный текст из _item_data
            data = self._item_data.get(item, {})
            if col_id == "description":
                text = data.get("full_desc", self.tree.set(item, col_id))
            elif col_id == "file":
                text = data.get("file", self.tree.set(item, col_id))
            else:
                text = self.tree.set(item, col_id)

            # Проверяем, нужно ли показывать тултип (если текст длинный)
            limit = 45 if col_id == "file" else 65
            if len(text) > limit:
                self._show_tooltip(event.x_root, event.y_root + 20, text)
            else:
                self._hide_tooltip()
        else:
            self._hide_tooltip()

    def _show_tooltip(self, x, y, text):
        """Показать всплывающую подсказку"""
        if self._tooltip is None:
            self._tooltip = tk.Toplevel(self.dialog)
            self._tooltip.wm_overrideredirect(True)
            self._tooltip.wm_geometry(f"+{x}+{y}")
            label = ttk.Label(
                self._tooltip,
                text=text,
                background="#ffffe0",
                relief="solid",
                borderwidth=1,
                padding=5,
                wraplength=600,
            )
            label.pack()
        else:
            self._tooltip.wm_geometry(f"+{x}+{y}")
            for child in self._tooltip.winfo_children():
                child.config(text=text)
            if not self._tooltip.winfo_viewable():
                self._tooltip.deiconify()

    def _hide_tooltip(self, event=None):
        """Скрыть всплывающую подсказку"""
        if self._tooltip is not None:
            self._tooltip.withdraw()

    # ── Экспорт ──

    def _copy_report(self):
        """Копировать отчёт в буфер обмена"""
        report = self._generate_report_text()
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(report)
        messagebox.showinfo("Скопировано", "Отчёт скопирован в буфер обмена")

    def _export_report(self):
        """Экспорт отчёта в файл"""
        file_path = filedialog.asksaveasfilename(
            title="Экспорт отчёта",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
            initialfile=f"integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if file_path:
            try:
                report = self._generate_report_text()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report)
                messagebox.showinfo("Успех", f"Отчёт сохранён:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить отчёт:\n{e}")

    def _generate_report_text(self):
        """Сгенерировать текст отчёта"""
        success = getattr(self.result, "success", True)
        files_checked = getattr(self.result, "files_checked", 0)
        files_valid = getattr(self.result, "files_valid", 0)
        files_invalid = getattr(self.result, "files_invalid", 0)
        warnings = getattr(self.result, "warnings", 0)

        lines = [
            "=" * 60,
            "ОТЧЁТ ПРОВЕРКИ ЦЕЛОСТНОСТИ",
            f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            f"Статус: {'✅ Пройдена' if success else '❌ Обнаружены проблемы'}",
            f"Проверено файлов: {files_checked}",
            f"Корректных: {files_valid}",
            f"С ошибками: {files_invalid}",
            f"Предупреждений: {warnings}",
            "",
            "-" * 60,
            "ОШИБКИ:",
            "-" * 60,
        ]

        errors = getattr(self.result, "errors", [])
        if errors:
            for err in errors:
                lines.append(f"  ❌ {err}")
        else:
            lines.append("  Нет ошибок")

        lines.append("")
        lines.append("-" * 60)
        lines.append("ПРЕДУПРЕЖДЕНИЯ:")
        lines.append("-" * 60)

        details = getattr(self.result, "details", [])
        warnings_list = [d for d in details if "⚠️" in d or "Предупреждение" in d]
        if warnings_list:
            for warn in warnings_list:
                lines.append(f"  ⚠️ {warn}")
        else:
            lines.append("  Нет предупреждений")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
