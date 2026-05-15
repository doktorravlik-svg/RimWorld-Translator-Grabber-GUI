# workers/separate_worker.py
"""
Worker для перевода модов в отдельную папку (separate mode).

Переопределяет методы для работы с путями:
- Сохраняет файлы в output_folder/ModName/...
- Не изменяет исходные файлы модов
- Создаёт структуру папок в output_folder
"""

import os
from typing import Any

from .translation_worker import TranslationWorker, TranslationResultDTO
from .path_strategy import SeparatePathStrategy
from utils.mod_version import get_mod_name
from utils.languages_path_resolver import (
    create_source_language_structure,
    find_all_defs_folders,
    find_all_language_folders,
    prioritize_language_folders,
)


class SeparateWorker(TranslationWorker):
    """
    Worker для режима separate.
    
    Отличается от TranslationWorker:
    - Все файлы сохраняются в output_folder/ModName/...
    - Исходные файлы модов не изменяются
    - Создаёт About.xml и LoadFolders.xml для translation mod
    """

    def __init__(
        self,
        mods_folder: str,
        source_lang: str = "English",
        source_langs: list[str] | None = None,
        target_lang: str = "Russian",
        output_folder: str | None = None,
        logger: Any | None = None,
        create_backup: bool = False,
        selected_mods: list[str] | None = None,
        force_update: bool = False,
        fuzzy: bool = True,
        engine_names: list[str] | None = None,
        mode: str = "separate",
        auto_detect_source_lang: bool = True,
        auto_split_glossary: bool = True,
    ):
        super().__init__(
            mods_folder=mods_folder,
            source_lang=source_lang,
            source_langs_list=source_langs,
            target_lang=target_lang,
            output_folder=output_folder,
            logger=logger,
            mode=mode,
            create_backup=create_backup,
            selected_mods=selected_mods,
            force_update=force_update,
            fuzzy=fuzzy,
            engine_names=engine_names,
            auto_detect_source_lang=auto_detect_source_lang,
            auto_split_glossary=auto_split_glossary,
        )
        # Переопределяем стратегию на SeparatePathStrategy
        self._path_strategy = SeparatePathStrategy()

    def _prepare_output_structure(self, mod_path: str, mod_name: str) -> tuple[str, str]:
        """
        Создаёт структуру папок в output_folder для мода.
        
        Создаёт:
        - output_folder/ModName/
        - output_folder/ModName/Languages/
        - output_folder/ModName/Languages/TargetLang/
        - output_folder/ModName/Languages/TargetLang/DefInjected/
        - output_folder/ModName/Languages/TargetLang/Keyed/
        
        Args:
            mod_path: Путь к исходному моду
            mod_name: Имя мода
            
        Returns:
            Кортеж (mod_root, mod_output):
            - mod_root: output_folder/ModName/
            - mod_output: output_folder/ModName/Languages/TargetLang/
        """
        mod_root = os.path.join(self.output_folder, mod_name)
        mod_output = os.path.join(mod_root, "Languages", self.target_lang)
        
        # Создаём всю структуру
        os.makedirs(mod_root, exist_ok=True)
        os.makedirs(mod_output, exist_ok=True)
        os.makedirs(os.path.join(mod_output, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(mod_output, "Keyed"), exist_ok=True)
        
        self.logger.info(f"[SeparateWorker] Создана структура: {mod_root}")
        return mod_root, mod_output

    def _get_save_path(self, original_path: str, mod_path: str, mod_name: str) -> str:
        """
        Переопределяет метод для режима separate.
        
        Заменяет префикс папки мода на префикс output_folder/ModName.
        
        Args:
            original_path: Исходный путь к файлу
            mod_path: Путь к папке мода
            mod_name: Имя мода
            
        Returns:
            Новый путь в output_folder
        """
        return self._path_strategy.get_save_path(
            original_path=original_path,
            mod_path=mod_path,
            output_folder=self.output_folder,
            mod_name=mod_name
        )

    def _translate_mod(self, mod_path: str, section=None) -> None:
        """Переводит один мод в separate режиме с подготовкой структуры."""
        mod_name = get_mod_name(mod_path)
        
        # ✅ ОТЛИЧИЕ: Подготавливаем структуру вывода ДО обработки
        mod_root, mod_output = self._prepare_output_structure(mod_path, mod_name)
        
        if section:
            section.add_item(f"Режим: separate", "info")
            section.add_item(f"Корень выходного мода: {mod_root}", "info")
            section.add_item(f"Папка target языка: {mod_output}", "info")
        
        mode_names = {"separate": "separate", "inplace": "inplace", "merge": "merge"}
        
        # ✅ ИСПРАВЛЕНО: Проверяем что mod_path существует, если нет - ищем правильный
        if not os.path.exists(mod_path):
            self.logger.warning(f"mod_path не найден: {mod_path}")
            # Вариант 1: mod_name как папка
            variant1 = os.path.join(self.mods_folder, mod_name)
            if os.path.exists(variant1):
                mod_path = variant1
                self.logger.info(f"✅ Найден путь (вариант1): {mod_path}")
            else:
                # Вариант 2: ищем Steam Workshop папку (числовой ID)
                try:
                    for item in os.listdir(self.mods_folder):
                        possible_mod_path = os.path.join(self.mods_folder, item)
                        if os.path.isdir(possible_mod_path):
                            test_about = os.path.join(possible_mod_path, "About", "About.xml")
                            if os.path.exists(test_about):
                                try:
                                    from utils.xml_utils import safe_parse_xml
                                    root = safe_parse_xml(test_about)
                                    if root is not None:
                                        name_elem = root.find("name")
                                        if name_elem is not None and name_elem.text and name_elem.text.strip() == mod_name:
                                            self.logger.info(f"✅ Найден правильный путь: {possible_mod_path}")
                                            mod_path = possible_mod_path
                                            break
                                except Exception as e:
                                    self.logger.debug(f"Ошибка чтения {test_about}: {e}")
                except Exception as e:
                    self.logger.warning(f"Ошибка поиска мода: {e}")
        
        if not os.path.exists(mod_path):
            self.logger.error(f"❌ mod_path НЕ НАЙДЕН: {mod_path}")
            self.logger.error(f"   Убедитесь что mod_path указывает на правильную папку мода")
            self.logger.error(f"   Для Steam Workshop модов используйте числовой ID (например, 1084452457)")
            self._errors.append(f"Мод не найден: {mod_path}")
            if section:
                section.add_item(f"❌ Мод не найден: {mod_path}", "error")
            return
        
        if section:
            section.add_item(f"Режим: {mode_names.get(self.mode, self.mode)}", "info")
        
        # ✅ ИСПРАВЛЕНО: Вычисляем пути ЯВНО до try: блока
        # ✅ НОВОЕ: Определяем исходные языки для этого мода
        source_langs = self.source_langs_list
        if self.auto_detect_source_lang:
            source_langs = self._detect_best_source_languages(mod_path)
            if section:
                section.add_item(f"Исходные языки: {source_langs}", "info")
        
        # Собираем языковые папки изо всех исходных языков
        all_lang_folders = []
        for lang in source_langs:
            lang_folders = find_all_language_folders(mod_path, lang)
            all_lang_folders.extend(lang_folders)
        prioritized_lang_folders = prioritize_language_folders(all_lang_folders, mod_path)
        all_defs_folders = find_all_defs_folders(mod_path)
        
        if section:
            section.add_item(f"Папок Languages: {len(prioritized_lang_folders)}", "info")
            section.add_item(f"Папок Defs: {len(all_defs_folders)}", "info")
        
        # ✅ ИСПРАВЛЕНО: Обновляем source_lang после автоопределения
        detected_source_lang = source_langs[0] if source_langs else self.source_lang
        
        try:
            # 0. Проверяем и создаём Languages для source языка
            self._progress(25, 100, f"Подготовка: {mod_name}")
            create_source_language_structure(mod_path, detected_source_lang)
            if section:
                section.add_item("✓ Структура Languages проверена", "success")
            
            # ✅ ВАЖНО: Сохраняем для использования в методах обработки
            self._current_mod_output = mod_output
            self._current_defs_folders = all_defs_folders
            
            # ✅ ВАЖНО: Создаём базовую структуру Languages для TARGET языка
            self._progress(30, 100, f"Создание структуры Languages: {mod_name}")
            self._ensure_target_language_structure(
                mod_path, mod_output, prioritized_lang_folders, all_defs_folders
            )
            
            if not prioritized_lang_folders and not all_defs_folders:
                self._warnings.append(f"Мод {mod_name} не содержит Languages или Defs")
                self._mods_processed += 1
                if section:
                    section.add_item("⚠️ Мод не содержит Languages или Defs", "warning")
                return
            
            # 3. Выполняем перевод
            self._progress(40, 100, f"Обработка Keyed файлов: {mod_name}")
            translations_count = self._process_languages(
                mod_path, mod_output, prioritized_lang_folders
            )
            
            if section:
                section.add_item(f"Keyed обработано: {translations_count} записей", "success")
            
            self._progress(60, 100, f"Обработка DefInjected файлов: {mod_name}")
            defs_translations = self._process_defs(all_defs_folders, mod_path, mod_output)
            translations_count += defs_translations
            
            if section:
                section.add_item(f"DefInjected обработано: {defs_translations} файлов", "success")
            
            # 4. Финализация (создание About.xml для separate mode)
            self._progress(85, 100, f"Финализация: {mod_name}")
            
            # ✅ ОТЛАДКА: Показываем пути
            if self.logger:
                self.logger.info(f"  mod_root (корень мода): {mod_root}")
                self.logger.info(f"  mod_output (для обработки): {mod_output}")
                self.logger.info(f"  translations_count: {translations_count}")
            
            os.makedirs(mod_root, exist_ok=True)
            
            self._finalize_mod(mod_path, mod_root, mod_output, translations_count, mod_name)
            
            self._mods_processed += 1
            self._translations_count += translations_count
            
            if section:
                section.add_item(f"✅ Мод завершён: {translations_count} записей", "success")
            
        except Exception as e:
            self._errors.append(f"Ошибка перевода {mod_name}: {e}")
            if section:
                section.add_item(f"❌ Ошибка: {e}", "error")
            raise

    def _should_create_backup(self) -> bool:
        """Для separate режима бэкапы не нужны."""
        return False
