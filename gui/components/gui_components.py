# gui_components.py - Оптимизированные компоненты GUI
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import ttkbootstrap as ttk

# ✅ Импорт для централизованного управления путями
from config.paths_config import get_paths_config
from gui.gui_i18n import tr

# ✅ Импорт для поддержки иконок в статус-баре
from ttkbootstrap.constants import *


class FolderSelector(ttk.Frame):
    """Компонент выбора папки с кнопкой обзора"""

    def __init__(
        self,
        parent,
        label_text=tr("folder", "Папка:"),
        button_text=tr("browse", "Обзор..."),
        initial_value="",
        width=50,
        command=None,
    ):
        super().__init__(parent)

        self.command = command
        self.folder_var = tk.StringVar(value=initial_value)

        ttk.Label(self, text=label_text).pack(side="left", padx=(0, 5))

        self.entry = ttk.Entry(self, width=width, textvariable=self.folder_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(self, text=button_text, command=self.browse).pack(side="left", padx=5)

    def browse(self):
        folder = filedialog.askdirectory(title=tr("select_folder", "Выберите папку"))
        if folder:
            self.folder_var.set(folder)
            if self.command:
                self.command(folder)

    def get(self):
        return self.folder_var.get()

    def set(self, value):
        self.folder_var.set(value)


class LanguageSelector(ttk.Frame):
    """Компонент выбора языка"""

    def __init__(
        self,
        parent,
        label_text=tr("language", "Язык:"),
        languages=None,
        initial_value="",
    ):
        super().__init__(parent)

        from config.language_constants import SUPPORTED_LANGUAGES

        if languages is None:
            languages = SUPPORTED_LANGUAGES

        self.language_var = tk.StringVar(value=initial_value)

        ttk.Label(self, text=label_text).pack(side="left", padx=(0, 5))

        self.combo = ttk.Combobox(self, textvariable=self.language_var, values=languages, width=20)
        self.combo.pack(side="left", padx=5)

    def get(self):
        return self.language_var.get()

    def set(self, value):
        self.language_var.set(value)


class ModsPathSelector(ttk.Frame):
    """
    ✅ НОВЫЙ: Компонент выбора папки модов с поддержкой пресетов.

    Позволяет выбрать путь из предустановленных пресетов или указать свой.
    Решает проблему: "Модуль фильтров не подхватывает папку модов"
    """

    def __init__(self, parent, initial_value="", width=50, command=None):
        super().__init__(parent)

        self.command = command
        self.paths_config = get_paths_config()
        self.folder_var = tk.StringVar(value=initial_value)

        # Фрейм первой строки (метка + поле + кнопка)
        line1_frame = ttk.Frame(self)
        line1_frame.pack(fill="x", pady=2)

        ttk.Label(line1_frame, text=tr("mods_folder", "Папка с модами:")).pack(
            side="left", padx=(0, 5)
        )

        self.entry = ttk.Entry(line1_frame, width=width, textvariable=self.folder_var)
        self.entry.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(line1_frame, text=tr("browse_icon", "📂 Обзор..."), command=self.browse).pack(
            side="left", padx=5
        )

        # Фрейм второй строки (пресеты)
        line2_frame = ttk.Frame(self)
        line2_frame.pack(fill="x", pady=2)

        ttk.Label(line2_frame, text=tr("preset", "📁 Пресет:")).pack(side="left", padx=(0, 5))

        # Выпадающий список пресетов
        presets = self.paths_config.get_available_presets()
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(
            line2_frame, textvariable=self.preset_var, values=presets, width=30, state="readonly"
        )
        self.preset_combo.pack(side="left", padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        # Кнопка "Применить для всех"
        ttk.Button(
            line2_frame,
            text=tr("apply_to_all", "🔄 Применить для всех модулей"),
            command=self._apply_to_all_modules,
            bootstyle="info",
        ).pack(side="left", padx=5)

    def browse(self):
        """Выбор папки через диалог"""
        folder = filedialog.askdirectory(
            title=tr("select_mods_folder_dialog", "Выберите папку с модами")
        )
        if folder:
            self.folder_var.set(folder)
            self.preset_var.set("")  # Сбрасываем пресет
            if self.command:
                self.command(folder)

    def _on_preset_selected(self, event=None):
        """Выбор пресета из списка"""
        preset_name = self.preset_var.get()
        if preset_name:
            preset_path = self.paths_config.get_preset_path(preset_name)
            if preset_path:
                self.folder_var.set(preset_path)
                if self.command:
                    self.command(preset_path)

    def _apply_to_all_modules(self):
        """Применяет текущий путь для всех модулей"""
        path = self.folder_var.get()
        if path:
            self.paths_config.set_mods_path(path, module="default", save=True)
            if self.command:
                self.command(path)

    def get(self):
        return self.folder_var.get()

    def set(self, value):
        self.folder_var.set(value)


# ============================================================
# УДАЛЕНО: StatusBar (дубликат — есть gui/components/statusbar.py)
# УДАЛЕНО: TranslationTab (дубликат — есть gui/tabs/gui_tab_translation.py)
# ============================================================


class LogPanel(ttk.LabelFrame):
    """Оптимизированная панель логирования с фильтрацией и сохранением"""

    MAX_LINES = 5000  # Максимум строк в логе

    def __init__(self, parent, title=None, height=10):
        from gui.gui_i18n import tr

        if title is None:
            title = tr("log_panel_title", "Лог")
        super().__init__(parent, text=title)

        # ✅ НОВОЕ: Переменные для фильтрации
        self.show_info_var = tk.BooleanVar(value=True)
        self.show_warning_var = tk.BooleanVar(value=True)
        self.show_error_var = tk.BooleanVar(value=True)
        self.show_success_var = tk.BooleanVar(value=True)
        self.auto_scroll_var = tk.BooleanVar(value=True)

        # ✅ НОВОЕ: Поиск
        self.search_var = tk.StringVar()

        # Фрейм для кнопок и фильтрации
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=5, pady=2)

        # Кнопки
        ttk.Button(btn_frame, text=tr("copy_all", "📋 Копировать всё"), command=self.copy_all).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text=tr("clear", "🗑️ Очистить"), command=self.clear).pack(
            side="left", padx=2
        )
        ttk.Button(
            btn_frame,
            text=tr("save_to_file", "💾 Сохранить в файл"),
            command=self.save_to_file,
        ).pack(side="left", padx=2)

        # ✅ НОВОЕ: Поиск
        ttk.Label(btn_frame, text=tr("search_icon", "🔍")).pack(side="left", padx=(10, 2))
        search_entry = ttk.Entry(btn_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side="left", padx=2)
        search_entry.bind("<KeyRelease>", lambda e: self._highlight_search())
        ttk.Button(
            btn_frame, text=tr("log_search_next_btn", "➡️"), width=3, command=self._find_next
        ).pack(side="left", padx=1)

        # ✅ НОВОЕ: Фильтры
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(filter_frame, text=tr("show_filter", "Показать:")).pack(side="left", padx=5)
        ttk.Checkbutton(
            filter_frame,
            text=tr("filter_info", "ℹ️ Инфо"),
            variable=self.show_info_var,
            command=self._apply_filters,
        ).pack(side="left", padx=2)
        ttk.Checkbutton(
            filter_frame,
            text=tr("filter_warnings", "⚠️ Предупреждения"),
            variable=self.show_warning_var,
            command=self._apply_filters,
        ).pack(side="left", padx=2)
        ttk.Checkbutton(
            filter_frame,
            text=tr("filter_errors", "❌ Ошибки"),
            variable=self.show_error_var,
            command=self._apply_filters,
        ).pack(side="left", padx=2)
        ttk.Checkbutton(
            filter_frame,
            text=tr("filter_success", "✅ Успех"),
            variable=self.show_success_var,
            command=self._apply_filters,
        ).pack(side="left", padx=2)
        ttk.Checkbutton(
            filter_frame,
            text=tr("auto_scroll", "📜 Автоскролл"),
            variable=self.auto_scroll_var,
        ).pack(side="left", padx=5)

        self.log_text = scrolledtext.ScrolledText(self, height=height, wrap="word", state="normal")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ✅ НОВОЕ: Настройка тегов для цветовой маркировки (улучшенные цвета)
        self.log_text.tag_config("info", foreground="#4fc3f7")
        self.log_text.tag_config("warning", foreground="#ffb74d")
        self.log_text.tag_config("error", foreground="#ef5350")
        self.log_text.tag_config("success", foreground="#66bb6a")
        self.log_text.tag_config("search", background="yellow", foreground="black")

        # Буфер для пакетного обновления
        self._pending_lines = []
        self._update_scheduled = False

        # ✅ НОВОЕ: Хранение всех строк для фильтрации
        self.all_lines = []
        self.current_line_index = 0

        # Контекстное меню для копирования выделенного
        self.context_menu = tk.Menu(self.log_text, tearoff=0)
        self.context_menu.add_command(
            label=tr("copy_selected", "📋 Копировать выделенное"),
            command=self.copy_selected,
        )
        self.context_menu.add_command(
            label=tr("copy_all", "📋 Копировать всё"), command=self.copy_all
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(label=tr("clear_log", "🗑️ Очистить лог"), command=self.clear)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label=tr("save_to_file", "💾 Сохранить в файл"), command=self.save_to_file
        )

        self.log_text.bind("<Button-3>", self._show_context_menu)
        # Горячие клавиши
        self.log_text.bind("<Control-c>", lambda e: self.copy_selected())
        self.log_text.bind("<Control-C>", lambda e: self.copy_selected())
        self.log_text.bind("<Control-a>", lambda e: self._select_all())
        self.log_text.bind("<Control-A>", lambda e: self._select_all())
        self.log_text.bind("<Control-f>", lambda e: search_entry.focus_set())

    def _show_context_menu(self, event):
        """Показать контекстное меню"""
        self.context_menu.post(event.x_root, event.y_root)

    def copy_selected(self):
        """Копировать выделенный текст"""
        try:
            selected = self.log_text.selection_get()
            if selected:
                self.clipboard_clear()
                self.clipboard_append(selected)
        except tk.TclError:
            pass  # Нет выделения

    def copy_all(self):
        """Копировать весь лог"""
        content = self.log_text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(content)

    def _select_all(self):
        """Выделить весь текст"""
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return "break"

    def log(self, message):
        """Добавление сообщения в лог с цветовой маркировкой"""
        level = self._determine_level(message)

        # Сохраняем в историю
        self.all_lines.append({"message": message, "level": level})

        # Проверяем, показывать ли сообщение
        show = (
            (level == "info" and self.show_info_var.get())
            or (level == "warning" and self.show_warning_var.get())
            or (level == "error" and self.show_error_var.get())
            or (level == "success" and self.show_success_var.get())
            or level == "unknown"
        )

        if show:
            self.log_text.insert(tk.END, message + "\n", level)

            # Ограничиваем количество строк
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > self.MAX_LINES:
                excess = line_count - self.MAX_LINES
                self.log_text.delete("1.0", f"{excess}.0")

            # Прокрутка вниз
            if self.auto_scroll_var.get():
                self.log_text.see(tk.END)

    def log_batch(self, messages):
        """Пакетное добавление сообщений (для производительности)"""
        for message in messages:
            level = self._determine_level(message)
            self.all_lines.append({"message": message, "level": level})

            show = (
                (level == "info" and self.show_info_var.get())
                or (level == "warning" and self.show_warning_var.get())
                or (level == "error" and self.show_error_var.get())
                or (level == "success" and self.show_success_var.get())
                or level == "unknown"
            )

            if show:
                self.log_text.insert(tk.END, message + "\n", level)

        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > self.MAX_LINES:
            excess = line_count - self.MAX_LINES
            self.log_text.delete("1.0", f"{excess}.0")

        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)

    def clear(self):
        """Очистить лог с корректной прокруткой"""
        self.log_text.delete("1.0", tk.END)
        self.log_text.see(tk.END)
        self.all_lines.clear()

    def save_to_file(self):
        """Сохранить лог в файл"""
        from datetime import datetime

        file_path = filedialog.asksaveasfilename(
            title=tr("save_log", "Сохранить лог"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log")],
            initialfile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )

        if not file_path:
            return

        try:
            content = self.log_text.get("1.0", tk.END)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo(
                tr("success_title", "Успех"),
                tr("log_saved", "Лог сохранён:\n{path}").format(path=file_path),
            )
        except Exception as e:
            messagebox.showerror(
                tr("error_title", "Ошибка"),
                tr("log_save_error", "Ошибка сохранения лога:\n{e}").format(e=e),
            )

    def _apply_filters(self):
        """Применить фильтры к логу"""
        self.log_text.delete("1.0", tk.END)

        for line_data in self.all_lines:
            message = line_data["message"]
            level = line_data["level"]

            show = (
                (level == "info" and self.show_info_var.get())
                or (level == "warning" and self.show_warning_var.get())
                or (level == "error" and self.show_error_var.get())
                or (level == "success" and self.show_success_var.get())
                or level == "unknown"
            )

            if show:
                tag = level if level in ["info", "warning", "error", "success"] else "info"
                self.log_text.insert(tk.END, message + "\n", tag)

        # Ограничиваем количество строк
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > self.MAX_LINES:
            excess = line_count - self.MAX_LINES
            self.log_text.delete("1.0", f"{excess}.0")

        self.log_text.see(tk.END)

    def _determine_level(self, message):
        """Определить уровень сообщения"""
        msg_lower = message.lower()
        if msg_lower.startswith("❌") or "error" in msg_lower or "ошибка" in msg_lower:
            return "error"
        elif msg_lower.startswith("⚠️") or "warning" in msg_lower or "предупреждение" in msg_lower:
            return "warning"
        elif msg_lower.startswith("✅") or "success" in msg_lower or "успех" in msg_lower:
            return "success"
        else:
            return "info"

    def _highlight_search(self):
        """Подсветить найденный текст"""
        search_text = self.search_var.get()
        if not search_text:
            self.log_text.tag_remove("search", "1.0", tk.END)
            return

        self.log_text.tag_remove("search", "1.0", tk.END)

        start_pos = "1.0"
        while True:
            start_pos = self.log_text.search(search_text, start_pos, tk.END)
            if not start_pos:
                break
            end_pos = f"{start_pos}+{len(search_text)}c"
            self.log_text.tag_add("search", start_pos, end_pos)
            start_pos = end_pos

    def _find_next(self):
        """Найти следующее вхождение"""
        search_text = self.search_var.get()
        if not search_text:
            return

        try:
            sel_start = self.log_text.index(tk.SEL_FIRST)
        except tk.TclError:
            sel_start = self.log_text.index(tk.INSERT)

        pos = self.log_text.search(search_text, sel_start, tk.END)
        if not pos:
            pos = self.log_text.search(search_text, "1.0", tk.END)
            if not pos:
                messagebox.showinfo(
                    tr("search_title", "Поиск"),
                    tr("not_found", "Не найдено: {text}").format(text=search_text),
                )
                return

        end_pos = f"{pos}+{len(search_text)}c"
        self.log_text.tag_remove(tk.SEL, "1.0", tk.END)
        self.log_text.tag_add(tk.SEL, pos, end_pos)
        self.log_text.mark_set(tk.INSERT, pos)
        self.log_text.see(pos)

    def flush(self):
        """Принудительное обновление отображения"""
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()
