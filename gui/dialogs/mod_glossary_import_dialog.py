# gui/dialogs/mod_glossary_import_dialog.py
"""
Диалог импорта глоссаря из файла мода.
Позволяет загрузить глоссарий из JSON файла или создать из папки мода.
"""

import json
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from loguru import logger
from ttkbootstrap.constants import *

from gui.gui_i18n import tr
from translation_db import get_translation_db
from collectors.collectors import collect_translatable_strings


class ModGlossaryImportDialog:
    """Диалог импорта глоссаря из файла мода"""

    def __init__(self, parent, target_language=None, callback=None):
        self.parent = parent
        self.target_language = target_language or self._get_default_target_language()
        self.db = get_translation_db(self.target_language)
        self.callback = callback

        if self.db is None:
            messagebox.showwarning(
                tr("editor_warning", "Предупреждение"),
                tr("editor_db_not_connected", "База переводов не подключена"),
            )
            return

        self._create_dialog()

    def _get_default_target_language(self):
        try:
            from config.config_manager import get_config_manager
            return get_config_manager().get("target_language", "Russian")
        except Exception:
            return "Russian"

    def _create_dialog(self):
        """Создаёт диалоговое окно"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(tr("glossary_import_mod", "Импорт глоссаря из мода"))
        self.dialog.geometry("500x450")
        self.dialog.minsize(400, 300)
        self.dialog.transient(self.parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        self._build_content()

        self.dialog.update_idletasks()
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.grab_set()

    def _infer_language_from_glossary_data(self, data):
        """Определяет язык глоссария по данным"""
        entries = data.get('entries', {})
        if not entries:
            logger.info("No entries in glossary data, cannot infer language")
            return None
        
        russian_count = 0
        ukrainian_count = 0
        english_count = 0
        total_valid = 0
        
        for term, translation in entries.items():
            if not term:
                continue
            
            if isinstance(term, list):
                continue
            
            term_str = str(term)
            trans_str = str(translation) if translation and not isinstance(translation, list) else ""
            
            if len(term_str) < 3:
                term_is_en = True
                term_has_ukr = False
                term_has_rus = False
            else:
                term_has_ukr = self._is_ukrainian(term_str)
                term_has_rus = self._is_russian(term_str)
                term_is_en = self._is_english(term_str)
            
            trans_has_ukr = self._is_ukrainian(trans_str) if trans_str else False
            trans_has_rus = self._is_russian(trans_str) if trans_str else False
            trans_is_en = self._is_english(trans_str) if trans_str else False
            
            total_valid += 1
            
            if trans_has_ukr:
                ukrainian_count += 1
            elif trans_has_rus:
                russian_count += 1
            elif trans_is_en:
                english_count += 1
            elif term_is_en:
                english_count += 1
            elif term_has_ukr:
                ukrainian_count += 1
            elif term_has_rus:
                russian_count += 1
        
        logger.info(f"Language inference: total={total_valid}, uk={ukrainian_count}, ru={russian_count}, en={english_count}")
        
        if total_valid > 0:
            if ukrainian_count > russian_count and ukrainian_count > english_count:
                return "Ukrainian"
            elif russian_count > ukrainian_count and russian_count > english_count:
                return "Russian"
            elif english_count > ukrainian_count and english_count > russian_count:
                return "English"
        
        return None

    def _is_english(self, text):
        """Проверяет, является ли текст английским (только латинские буквы и основные знаки)"""
        if not text:
            return False
        text_str = str(text)
        cyrillic_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїґє')
        if any(c in cyrillic_chars for c in text_str.lower()):
            return False
        
        has_korean = any('\uac00' <= c <= '\ud7af' for c in text_str)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text_str)
        has_japanese = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_str)
        
        if has_korean or has_chinese or has_japanese:
            return False
        
        english_letters = set('abcdefghijklmnopqrstuvwxyz')
        letter_count = sum(1 for c in text_str.lower() if c in english_letters)
        if letter_count == 0:
            return False
        
        return letter_count / len(text_str) > 0.8

    def _is_ukrainian(self, text):
        """Проверяет, содержит ли текст украинские символы (и только украинские)"""
        if not text:
            return False
        text_str = str(text)
        ukrainian_chars = set('іїґє')
        cyrillic_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїґє')
        
        text_lower = text_str.lower()
        has_ukrainian = any(c in ukrainian_chars for c in text_lower)
        has_other_cyrillic = any(c in cyrillic_chars for c in text_lower)
        
        if not has_ukrainian:
            return False
        
        has_korean = any('\uac00' <= c <= '\ud7af' for c in text_lower)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text_lower)
        has_japanese = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_lower)
        
        if has_korean or has_chinese or has_japanese:
            return False
        
        return True
    
    def _is_russian(self, text):
        """Проверяет, содержит ли текст русские символы (без украинских)"""
        if not text:
            return False
        text_str = str(text)
        russian_chars = set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя')
        ukrainian_chars = set('іїґє')
        
        text_lower = text_str.lower()
        has_russian = any(c in russian_chars for c in text_lower)
        has_ukrainian = any(c in ukrainian_chars for c in text_lower)
        
        if not has_russian or has_ukrainian:
            return False
        
        has_korean = any('\uac00' <= c <= '\ud7af' for c in text_lower)
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text_lower)
        has_japanese = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text_lower)
        has_latin = any(c.isalpha() and c.isascii() for c in text_lower)
        
        if has_korean or has_chinese or has_japanese or has_latin:
            return False
        
        return True

    def _build_content(self):
        """Создаёт содержимое диалога"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        ttk.Label(
            main_frame,
            text=tr("glossary_import_mod", "📂 Импорт глоссаря из мода"),
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(0, 15))

        ttk.Label(
            main_frame,
            text=tr("glossary_import_mod_desc", "Выберите файл глоссаря мода (JSON) или папку мода:"),
            font=("Segoe UI", 10),
        ).pack(pady=(0, 15))

        self.mode_var = tk.StringVar(value="file")

        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            file_frame,
            text=tr("glossary_import_file", "Из файла глоссаря"),
            variable=self.mode_var,
            value="file",
            command=self._on_mode_change,
        ).pack(anchor="w")

        self.file_path_var = tk.StringVar()
        file_select_frame = ttk.Frame(main_frame)
        file_select_frame.pack(fill="x", pady=5)

        ttk.Entry(
            file_select_frame,
            textvariable=self.file_path_var,
            width=40,
            state="readonly",
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            file_select_frame,
            text="...",
            width=5,
            command=self._select_file,
        ).pack(side="right", padx=(5, 0))

        mod_frame = ttk.Frame(main_frame)
        mod_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            mod_frame,
            text=tr("glossary_import_folder", "Из папки мода"),
            variable=self.mode_var,
            value="folder",
            command=self._on_mode_change,
        ).pack(anchor="w")

        self.folder_path_var = tk.StringVar()
        folder_select_frame = ttk.Frame(main_frame)
        folder_select_frame.pack(fill="x", pady=5)

        ttk.Entry(
            folder_select_frame,
            textvariable=self.folder_path_var,
            width=40,
            state="readonly",
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            folder_select_frame,
            text="...",
            width=5,
            command=self._select_folder,
        ).pack(side="right", padx=(5, 0))

        ttk.Separator(main_frame).pack(fill="x", pady=15)

        self.status_var = tk.StringVar(value=tr("glossary_ready", "Готов"))
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, bootstyle="info")
        self.status_label.pack(pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(15, 0))

        ttk.Button(
            btn_frame,
            text=tr("editor_import", "📥 Импорт"),
            command=self._import,
            bootstyle="success",
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame,
            text=tr("editor_close", "Отмена"),
            command=self._on_dialog_close,
        ).pack(side="right", padx=5)

        self._on_mode_change()

    def _on_mode_change(self):
        """Обрабатывает изменение режима импорта"""
        mode = self.mode_var.get()
        self.file_path_var.set("")
        self.folder_path_var.set("")
        self.status_var.set(tr("glossary_ready", "Готов"))

    def _select_file(self):
        """Выбирает файл глоссаря"""
        file_path = filedialog.askopenfilename(
            title=tr("glossary_import_file", "Выберите файл глоссаря"),
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.file_path_var.set(file_path)

    def _select_folder(self):
        """Выбирает папку мода"""
        folder_path = filedialog.askdirectory(
            title=tr("glossary_import_folder", "Выберите папку мода")
        )
        if folder_path:
            self.folder_path_var.set(folder_path)

    def _import(self):
        """Выполняет импорт"""
        mode = self.mode_var.get()

        if mode == "file":
            path = self.file_path_var.get()
            if not path:
                messagebox.showwarning(
                    tr("editor_warning", "Внимание"),
                    tr("glossary_import_file", "Выберите файл глоссаря")
                )
                return
            self._import_from_file(path)
        else:
            path = self.folder_path_var.get()
            if not path:
                messagebox.showwarning(
                    tr("editor_warning", "Внимание"),
                    tr("glossary_import_folder", "Выберите папку мода")
                )
                return
            self._import_from_folder(path)

    def _import_from_file(self, file_path):
        """Импортирует глоссарий из файла"""
        try:
            logger.info(f"_import_from_file called: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            count = self._process_glossary_data(data)
            logger.info(f"_process_glossary_data returned: {count}")

            if count == 0:
                logger.info("Count is 0, returning early")
                return

            if self.callback:
                self.callback()

            messagebox.showinfo(
                tr("editor_success", "Готово"),
                tr("glossary_import_mod_success", f"Импортировано {count} терминов"),
                parent=self.dialog
            )
            self._on_dialog_close()

        except Exception as e:
            logger.error(f"Ошибка импорта глоссария: {e}")
            messagebox.showerror(
                tr("glossary_error", "Ошибка"),
                tr("glossary_import_failed", f"Не удалось импортировать: {e}"),
                parent=self.dialog
            )

    def _import_from_folder(self, folder_path):
        """Импортирует глоссарий из папки мода"""
        glossary_file = os.path.join(folder_path, "glossary.json")
        if not os.path.exists(glossary_file):
            glossary_file = os.path.join(folder_path, "Glossary.json")

        if os.path.exists(glossary_file):
            self._import_from_file(glossary_file)
            return

        self._create_glossary_from_mod(folder_path)

    def _create_glossary_from_mod(self, folder_path):
        """Создаёт глоссарий из файлов мода"""
        logger.info(f"_create_glossary_from_mod called with folder_path: {folder_path}")
        self.status_var.set(tr("glossary_importing", "Создание глоссария из файлов мода..."))
        self.dialog.update_idletasks()

        try:
            from config.paths_config import get_paths_config

            mods_path = get_paths_config().get_mods_path()
            if not mods_path:
                messagebox.showwarning(
                    tr("editor_warning", "Внимание"),
                    tr("glossary_select_mods_folder", "Сначала укажите папку с модами в настройках")
                )
                return

            detected_languages = self._detect_language_from_mod_folder(folder_path)
            logger.info(f"Languages detected from folder: {detected_languages}")
            
            if not detected_languages:
                sample_translation = self._get_sample_translation(folder_path)
                logger.info(f"Sample translation for language detection: {sample_translation[:100] if sample_translation else None}...")
                if sample_translation:
                    inferred = self._infer_language_from_glossary_data({'entries': {'sample': sample_translation}})
                    logger.info(f"Inferred language from sample: {inferred}")
                    if inferred:
                        detected_languages = [inferred]
            
            is_from_languages_folder = os.path.exists(os.path.join(folder_path, "Languages"))
            if not detected_languages and not is_from_languages_folder:
                detected_languages = ["English"]
                logger.info("Defaulting to English for root-level import (Defs/Patches)")
            
            if not detected_languages:
                detected_languages = [self.target_language]
            
            if len(detected_languages) > 1:
                detected_languages.sort()
                selected_language = self._show_language_selection_dialog(detected_languages)
                if not selected_language:
                    return
                detected_languages = [selected_language]
            
            detected_language = detected_languages[0]
            use_separate_db = False
            
            if detected_language != self.target_language:
                result = messagebox.askyesno(
                    tr("glossary_import", "Импорт"),
                    f"Обнаружен язык мода: {detected_language}\nТекущий язык: {self.target_language}\nЗаменить?",
                    parent=self.dialog
                )
                if result:
                    self.target_language = detected_language
                    try:
                        from config.config_manager import get_config_manager
                        get_config_manager().set("target_language", self.target_language)
                    except Exception as e:
                        logger.warning(f"Failed to save target_language: {e}")
                    self.db = get_translation_db(self.target_language)
                else:
                    use_separate_db = True

            import_db = self.db if self.db else get_translation_db(self.target_language)
            if use_separate_db and detected_language:
                import_db = get_translation_db(detected_language)
            elif use_separate_db:
                import_db = get_translation_db(self.target_language)
            
            if not import_db:
                logger.error("Failed to get translation database")
                messagebox.showerror(
                    tr("glossary_error", "Ошибка"),
                    tr("glossary_import_failed", "Не удалось подключиться к базе данных"),
                    parent=self.dialog
                )
                return

            db_language = detected_language if use_separate_db and detected_language else self.target_language
            self._start_import_thread(folder_path, db_language)

        except Exception as e:
            logger.error(f"Ошибка создания глоссария: {e}")
            messagebox.showerror(
                tr("glossary_error", "Ошибка"),
                tr("glossary_import_failed", f"Не удалось создать глоссарий: {e}")
            )

    def _start_import_thread(self, folder_path, db_language):
        """Запускает импорт в фоновом потоке"""
        def worker():
            from translation_db import get_translation_db
            import_db = get_translation_db(db_language)
            terms = {}
            count = 0

            for root, dirs, files in os.walk(folder_path):
                rel_path = os.path.relpath(root, folder_path)
                rel_path_lower = rel_path.lower()
                
                parts = rel_path_lower.split(os.sep)
                in_languages_folder = "languages" in parts
                
                if in_languages_folder:
                    lang_idx = parts.index("languages")
                    if lang_idx + 1 < len(parts):
                        lang_folder_name = parts[lang_idx + 1]
                        if not self._is_language_folder_for_target(lang_folder_name):
                            continue
                    else:
                        continue
                
                dirs[:] = [d for d in dirs if d.lower() != "about"]
                
                for file in files:
                    if file.endswith('.xml'):
                        file_path = os.path.join(root, file)
                        try:
                            strings = collect_translatable_strings(file_path)
                            for key, value in strings.items():
                                if value and not isinstance(value, list):
                                    term = str(value).strip()
                                    if len(term) > 1 and term not in terms:
                                        if db_language == "English":
                                            if self._is_english(term):
                                                terms[term] = term
                                        elif db_language == "Russian":
                                            if self._is_russian(term):
                                                terms[term] = term
                                        elif db_language == "Ukrainian":
                                            if self._is_ukrainian(term):
                                                terms[term] = term
                                        else:
                                            terms[term] = term
                        except Exception as e:
                            logger.debug(f"Не удалось прочитать {file_path}: {e}")

            for term in terms.values():
                if import_db:
                    try:
                        import_db.add_glossary_term(
                            term,
                            term,
                            "imported",
                            "",
                            db_language
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Не удалось добавить термин '{term}': {e}")

            def on_complete():
                if self.callback:
                    self.callback()
                messagebox.showinfo(
                    tr("editor_success", "Готово"),
                    tr("glossary_import_mod_success", f"Создано {count} терминов из файлов мода"),
                    parent=self.dialog
                )
                self._on_dialog_close()

            self.dialog.after(0, on_complete)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _detect_language_from_mod_folder(self, folder_path):
        """Определяет языки мода по структуре папок (возвращает список)"""
        from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders
        
        detected_set = set()
        languages_folders = find_all_languages_folders_with_loadfolders(folder_path)
        
        for languages_path in languages_folders:
            if not os.path.exists(languages_path):
                continue
            
            for lang_folder in os.listdir(languages_path):
                lang_lower = lang_folder.lower()
                if "russian" in lang_lower or "русский" in lang_lower:
                    detected_set.add("Russian")
                elif "ukrainian" in lang_lower or "українська" in lang_lower or "украинский" in lang_lower:
                    detected_set.add("Ukrainian")
                elif "english" in lang_lower:
                    detected_set.add("English")
                elif "german" in lang_lower or "deutsch" in lang_lower:
                    detected_set.add("German")
                elif "french" in lang_lower or "français" in lang_lower:
                    detected_set.add("French")
                elif "spanish" in lang_lower or "español" in lang_lower:
                    detected_set.add("Spanish")
                elif "japanese" in lang_lower:
                    detected_set.add("Japanese")
                elif "chinese" in lang_lower:
                    detected_set.add("Chinese")
                elif "korean" in lang_lower:
                    detected_set.add("Korean")
                elif "polish" in lang_lower:
                    detected_set.add("Polish")
                elif "portuguese" in lang_lower:
                    detected_set.add("Portuguese")
                elif "italian" in lang_lower:
                    detected_set.add("Italian")
        
        return list(detected_set)
    
    def _show_language_selection_dialog(self, languages):
        """Показывает диалог выбора языка при наличии нескольких языков в моде"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title(tr("glossary_import", "Выбор языка"))
        dialog.geometry("350x200")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        ttk.Label(
            dialog,
            text=tr("glossary_import", "Обнаружены несколько языков в моде. Выберите:"),
            font=("Segoe UI", 10),
        ).pack(pady=(15, 10))
        
        selected = tk.StringVar(value=languages[0])
        
        for lang in languages:
            ttk.Radiobutton(
                dialog,
                text=lang,
                variable=selected,
                value=lang,
            ).pack(anchor="w", padx=40)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(20, 15))
        
        result = [None]
        
        def on_ok():
            result[0] = selected.get()
            dialog.destroy()
        
        def on_cancel():
            result[0] = None
            dialog.destroy()
        
        ttk.Button(btn_frame, text=tr("editor_import", "ОК"), command=on_ok, width=10).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("editor_close", "Отмена"), command=on_cancel, width=10).pack(side="left", padx=5)
        
        dialog.wait_window()
        return result[0]
    
    def _is_language_folder_for_target(self, lang_folder_name: str) -> bool:
        """Проверяет, соответствует ли папка языка целевому языку"""
        lang_lower = lang_folder_name.lower()
        target_lower = self.target_language.lower()
        
        if target_lower == "russian":
            return "russian" in lang_lower or "русский" in lang_lower
        elif target_lower == "ukrainian":
            return "ukrainian" in lang_lower or "українська" in lang_lower or "украинский" in lang_lower
        elif target_lower == "english":
            return "english" in lang_lower
        elif target_lower == "german":
            return "german" in lang_lower or "deutsch" in lang_lower
        elif target_lower == "french":
            return "french" in lang_lower or "français" in lang_lower
        elif target_lower == "japanese":
            return "japanese" in lang_lower
        
        return target_lower in lang_lower
    
    def _get_sample_translation(self, folder_path):
        """Получает样本 текста из XML файлов мода для определения языка"""
        sample_texts = []
        max_samples = 50
        
        for root, dirs, files in os.walk(folder_path):
            rel_path = os.path.relpath(root, folder_path)
            rel_path_lower = rel_path.lower()
            
            if "about" in rel_path_lower.split(os.sep):
                continue
            if "languages" in rel_path_lower.split(os.sep):
                continue
            
            for file in files:
                if file.endswith('.xml') and len(sample_texts) < max_samples:
                    file_path = os.path.join(root, file)
                    try:
                        strings = collect_translatable_strings(file_path)
                        for value in strings.values():
                            if value and not isinstance(value, list):
                                val_str = str(value).strip()
                                if len(val_str) > 2:
                                    sample_texts.append(val_str)
                                    if len(sample_texts) >= max_samples:
                                        break
                    except Exception:
                        pass
        
        return ' '.join(sample_texts[:10]) if sample_texts else None

    def _process_glossary_data(self, data):
        """Обрабатывает данные глоссария и сохраняет в БД"""
        count = 0
        entries = data.get('entries', {})
        file_target_language = data.get('target_language')
        
        logger.info(f"_process_glossary_data: file_lang={file_target_language}, current_lang={self.target_language}, entries_count={len(entries)}")
        
        if file_target_language is None:
            file_target_language = self._infer_language_from_glossary_data(data)
            logger.info(f"Inferred language from data: {file_target_language}")
        
        if file_target_language is None:
            file_target_language = self.target_language
            logger.info(f"No target_language in file, using current: {file_target_language}")

        if file_target_language and file_target_language != self.target_language:
            try:
                dialog_exists = self.dialog.winfo_exists() if hasattr(self, 'dialog') else False
                logger.info(f"Dialog exists: {dialog_exists}")
                
                if dialog_exists:
                    result = messagebox.askyesno(
                        tr("glossary_import", "Импорт"),
                        tr("glossary_language_mismatch", f"Язык глоссария: {file_target_language}\nТекущий язык: {self.target_language}\nЗаменить?"),
                        parent=self.dialog
                    )
                    logger.info(f"User result: {result}")
                else:
                    logger.warning("Dialog does not exist, auto-accepting")
                    result = True
            except Exception as e:
                logger.warning(f"Не удалось показать диалог: {e}")
                result = True
            
            if not result:
                logger.info("User declined language change")
                return 0
            self.target_language = file_target_language
            try:
                from config.config_manager import get_config_manager
                get_config_manager().set("target_language", self.target_language)
            except Exception as e:
                logger.warning(f"Failed to save target_language: {e}")
            old_db_id = id(self.db)
            self.db = get_translation_db(self.target_language)
            logger.info(f"DB changed: old_id={old_db_id}, new_id={id(self.db)}, lang={self.target_language}")

        if isinstance(entries, dict):
            for term, translation in entries.items():
                if self.db:
                    try:
                        self.db.add_glossary_term(
                            term,
                            translation,
                            "imported",
                            "",
                            self.target_language
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(f"Не удалось добавить термин '{term}': {e}")

        return count

    def _on_dialog_close(self):
        """Обработчик закрытия диалога"""
        try:
            self.dialog.grab_release()
        except:
            pass
        self.dialog.destroy()