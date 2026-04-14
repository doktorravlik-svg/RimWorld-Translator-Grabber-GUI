# gui/dialogs/import_translations_dialog.py
"""
Диалог для импорта переводов из существующих модов в базу данных.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from config.paths_config import get_paths_config
from gui.gui_i18n import tr
from translation.importer import get_importer


class ImportTranslationsDialog:
    """Диалог импорта переводов из модов в базу данных"""

    def __init__(self, parent):
        self.parent = parent
        self.mods_folder = get_paths_config().get_mods_path()
        self.target_lang = tk.StringVar(value="Russian")
        self.is_importing = False

        self._create_dialog()

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("import_dialog_title", "📥 Импорт переводов"))
        self.dialog.geometry("600x550")
        self.dialog.minsize(500, 450)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        self._build_content()
        self._build_buttons()

        # Центрируем диалог
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 600) // 2
        y = (self.dialog.winfo_screenheight() - 550) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _build_content(self):
        """Создаёт содержимое диалога"""
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text=tr("import_title", "📥 Импорт переводов из модов"),
            font=("Segoe UI", 14, "bold"),
        )
        title_label.pack(pady=(0, 10))

        # Описание
        desc_label = ttk.Label(
            main_frame,
            text=tr(
                "import_description",
                "Сканирует папки Languages в модах и импортирует все переводы\n"
                "в базу данных для повторного использования при автопереводе.",
            ),
            font=("Segoe UI", 9),
            justify="center",
        )
        desc_label.pack(pady=(0, 15))

        # Настройки импорта
        settings_frame = ttk.LabelFrame(
            main_frame, text=tr("import_settings", "⚙️ Настройки импорта"), padding=10
        )
        settings_frame.pack(fill="x", pady=5)

        # Папка модов
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.pack(fill="x", pady=5)

        ttk.Label(folder_frame, text=tr("import_mods_folder", "Папка модов:")).pack(side="left")

        self.folder_var = tk.StringVar(value=self.mods_folder)
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=40)
        folder_entry.pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(folder_frame, text="📂", command=self._browse_folder, width=4).pack(side="left")

        # Целевой язык
        lang_frame = ttk.Frame(settings_frame)
        lang_frame.pack(fill="x", pady=5)

        ttk.Label(lang_frame, text=tr("import_target_lang", "Целевой язык:")).pack(
            side="left", padx=(0, 5)
        )

        languages = ["Russian", "English", "German", "French", "Spanish", "Chinese", "Japanese"]
        lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.target_lang, values=languages, width=15, state="readonly"
        )
        lang_combo.pack(side="left")

        # Прогресс
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=10)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, mode="determinate"
        )
        self.progress_bar.pack(fill="x", pady=2)

        self.status_label = ttk.Label(
            progress_frame, text=tr("import_ready", "✅ Готов к импорту"), font=("Segoe UI", 9)
        )
        self.status_label.pack(anchor="w")

        # Статистика
        stats_frame = ttk.LabelFrame(
            main_frame, text=tr("import_stats", "📊 Статистика"), padding=10
        )
        stats_frame.pack(fill="both", expand=True, pady=5)

        self.stats_text = tk.Text(stats_frame, height=5, state="disabled", font=("Consolas", 9))
        self.stats_text.pack(fill="both", expand=True)

    def _build_buttons(self):
        """Создаёт кнопки внизу диалога"""
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill="x", side="bottom", pady=10, padx=15)

        self.import_btn = ttk.Button(
            btn_frame,
            text=tr("import_start", "🚀 Начать импорт"),
            command=self._start_import,
            bootstyle="success",
        )
        self.import_btn.pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text=tr("import_close", "❌ Закрыть"),
            command=self.dialog.destroy,
            bootstyle="secondary",
        ).pack(side="right", padx=5)

    def _browse_folder(self):
        """Открывает диалог выбора папки"""
        folder = filedialog.askdirectory(
            title=tr("import_select_folder", "Выберите папку модов"), initialdir=self.mods_folder
        )
        if folder:
            self.folder_var.set(folder)
            # Debug: логируем выбор папки
            if hasattr(self, "_log_callback") and self._log_callback:
                self._log_callback(f"[DEBUG] Выбрана папка для импорта: {folder}")

    def _start_import(self):
        """Запускает процесс импорта"""
        if self.is_importing:
            return

        mods_folder = self.folder_var.get()
        if not os.path.exists(mods_folder):
            messagebox.showerror(
                tr("import_error", "Ошибка"),
                tr("import_folder_not_found", "Папка модов не найдена!"),
            )
            return

        # Debug: логируем запуск импорта
        if hasattr(self, "_log_callback") and self._log_callback:
            self._log_callback(f"[DEBUG] Запуск импорта переводов из: {mods_folder}")

        self.is_importing = True
        self.import_btn.config(state="disabled", text=tr("import_importing", "⏳ Импорт..."))
        self.progress_var.set(0)
        self._update_stats_text("Начало импорта...\n")

        # Запускаем импорт в отдельном потоке
        import threading

        thread = threading.Thread(
            target=self._run_import, args=(mods_folder, self.target_lang.get()), daemon=True
        )
        thread.start()

    def _run_import(self, mods_folder, target_lang):
        """Выполняет импорт (в отдельном потоке)"""
        try:
            importer = get_importer()

            def progress_callback(current, total, message):
                if total > 0:
                    percentage = (current / total) * 100
                    self.progress_var.set(percentage)
                    self.status_label.config(text=f"{message} ({current}/{total})")

            stats = importer.import_from_mods_folder(
                mods_folder, target_lang, progress_callback=progress_callback
            )

            # Обновляем статистику
            self._update_stats_text(
                f"✅ Импорт завершён!\n\n"
                f"📦 Модов просканировано: {stats.get('mods_scanned', 0)}\n"
                f"📄 Файлов обработано: {stats.get('files_processed', 0)}\n"
                f"🌐 Переводов импортировано: {stats.get('translations_imported', 0)}\n"
                f"❌ Ошибок: {stats.get('errors', 0)}\n\n"
                f"База данных статистика:\n"
            )

            # Добавляем статистику БД
            db_stats = importer.get_database_stats()
            self._update_stats_text(
                f"  📝 Записей переводов: {db_stats.get('translation_entries', 0)}\n"
                f"  📖 Терминов глоссария: {db_stats.get('glossary_terms', 0)}\n",
                append=True,
            )

            self.dialog.after(
                0,
                lambda: messagebox.showinfo(
                    tr("import_success", "Успех"),
                    tr("import_completed", "Импорт завершён успешно!"),
                ),
            )

        except Exception as e:
            self._update_stats_text(f"\n❌ Ошибка импорта: {e}\n")
            self.dialog.after(0, lambda: messagebox.showerror(tr("import_error", "Ошибка"), str(e)))
        finally:
            self.dialog.after(0, self._finish_import)

    def _finish_import(self):
        """Завершает импорт и разблокирует интерфейс"""
        self.is_importing = False
        self.import_btn.config(state="normal", text=tr("import_start", "🚀 Начать импорт"))
        self.status_label.config(text=tr("import_done", "✅ Импорт завершён"))

    def _update_stats_text(self, text, append=False):
        """Обновляет текст статистики (безопасно для вызова из любого потока)"""

        def update():
            self.stats_text.config(state="normal")
            if append:
                self.stats_text.insert("end", text)
            else:
                self.stats_text.delete("1.0", "end")
                self.stats_text.insert("1.0", text)
            self.stats_text.config(state="disabled")
            self.stats_text.see("end")

        self.dialog.after(0, update)
