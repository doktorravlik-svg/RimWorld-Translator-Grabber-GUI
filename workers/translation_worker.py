# workers/translation_worker.py
"""
Worker для асинхронного перевода модов.
"""

from loguru import logger
_default_logger = logger  # Save reference to module-level logger
import os
import re
import shutil
import time
from typing import Any
import lxml.etree as etree

from utils.fs_utils import safe_walk
from utils.rimworld_xml import TRANSLATABLE_TAGS


# ✅ НОВОЕ: Используем единый модуль для путей
from utils.path_utils import ensure_project_root_in_path

from translation.translator import AutoTranslator

# ✅ НОВОЕ: Используем единый модуль для путей Languages
from utils.languages_path_resolver import (
    create_source_language_structure,
    find_all_defs_folders,
    find_all_language_folders,
    prioritize_language_folders,
)
from utils.mod_version import get_mod_name

# ✅ НОВОЕ: Используем единый модуль для XML-парсинга
from utils.xml_utils import safe_parse_xml

# ✅ НОВОЕ: Импортируем generate_or_update_per_def_files_v2 ОДИН РАЗ в начале файла
from translation.per_def_generator import generate_or_update_per_def_files_v2 as gen_def_files

from .base_worker import BaseWorker
from .path_strategy import InplacePathStrategy, SeparatePathStrategy, PathStrategy

# Call ensure_project_root_in_path after all imports
ensure_project_root_in_path()


def _safe_read_file(filepath: str, encoding: str = "utf-8", max_retries: int = 3) -> str | None:
    """
    Безопасно читает файл с повторными попытками при WinError 32.

    Args:
        filepath: Путь к файлу
        encoding: Кодировка (по умолчанию utf-8)
        max_retries: Максимальное количество попыток

    Returns:
        Содержимое файла или None при ошибке
    """
    for attempt in range(max_retries):
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except OSError as e:
            if e.winerror == 32 and attempt < max_retries - 1:
                # Файл заблокирован - ждем и пробуем снова
                time.sleep(0.1 * (attempt + 1))
            else:
                raise
    return None


def _safe_write_file(filepath: str, content: str, encoding: str = "utf-8", max_retries: int = 3) -> None:
    """
    Безопасно записывает файл с повторными попытками при WinError 32.

    На Windows файлы могут быть временно заблокированы (антивирус, задержка ОС).
    Эта функция повторяет попытку записи после небольшой задержки.

    Args:
        filepath: Путь к файлу
        content: Содержимое для записи
        encoding: Кодировка (по умолчанию utf-8)
        max_retries: Максимальное количество попыток

    Raises:
        OSError: Если после всех попыток записи не удалась
    """
    for attempt in range(max_retries):
        try:
            with open(filepath, "w", encoding=encoding) as f:
                f.write(content)
            return
        except OSError as e:
            if e.winerror == 32 and attempt < max_retries - 1:
                # Файл заблокирован - ждем и пробуем снова
                time.sleep(0.1 * (attempt + 1))
            else:
                raise


def _safe_copy_file(src: str, dst: str, max_retries: int = 15) -> None:
    """
    Безопасно копирует файл с повторными попытками при WinError 32.
    Использует прямое чтение/запись для избежания проблем на Windows.

    Args:
        src: Исходный файл
        dst: Целевой файл
        max_retries: Максимальное количество попыток
    """
    import time
    # Читаем содержимое файла в память
    content = None
    for attempt in range(max_retries):
        try:
            with open(src, 'rb') as f:
                content = f.read()
            break
        except OSError as e:
            if getattr(e, 'winerror', None) == 32 and attempt < max_retries - 1:
                delay = 0.5 * (2 ** attempt)
                time.sleep(min(delay, 10))
            else:
                raise

    if content is None:
        raise OSError(f"Не удалось прочитать файл: {src}")

    # Записываем в целевой файл
    for attempt in range(max_retries):
        try:
            with open(dst, 'wb') as f:
                f.write(content)
            return
        except OSError as e:
            if getattr(e, 'winerror', None) == 32 and attempt < max_retries - 1:
                delay = 0.5 * (2 ** attempt)
                time.sleep(min(delay, 10))
            else:
                raise


class TranslationResultDTO:
    """DTO для результата перевода"""

    def __init__(
        self,
        success: bool,
        mods_processed: int = 0,
        translations_count: int = 0,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.success = success
        self.mods_processed = mods_processed
        self.translations_count = translations_count
        self.errors = errors or []
        self.warnings = warnings or []
        self.details = details or {}

    def __repr__(self):
        return f"<TranslationResultDTO success={self.success} mods={self.mods_processed} translations={self.translations_count}>"


class TranslationWorker(BaseWorker):
    """Worker для асинхронного перевода модов."""

    def __init__(
        self,
        mods_folder: str,
        source_lang: str | list[str] = "English",
        target_lang: str = "Russian",
        output_folder: str | None = None,
        logger: Any | None = None,
        mode: str = "separate",
        create_backup: bool = True,
        selected_mods: list[str] | None = None,
        force_update: bool = False,
        fuzzy: bool = True,
        engine_names: list[str] | None = None,
        auto_detect_source_lang: bool = True,
        source_langs_list: list[str] | None = None,
        auto_split_glossary: bool = True,
    ):
        super().__init__()
        self.mods_folder = mods_folder
        self.target_lang = target_lang
        self.output_folder = output_folder or os.path.join(mods_folder, "Translated")
        self.logger = logger or _default_logger
        self.mode = mode
        self.create_backup = create_backup
        self.selected_mods = selected_mods or []
        self.force_update = force_update
        self.fuzzy = fuzzy
        self._engine_names = engine_names
        self.auto_detect_source_lang = auto_detect_source_lang
        self._auto_split_glossary = auto_split_glossary
        self._auto_translator: AutoTranslator | None = None
        self._mods_processed = 0
        self._translations_count = 0
        self._errors: list[str] = []
        self._warnings: list[str] = []

        if source_langs_list is not None:
            self.source_langs_list = source_langs_list
        elif isinstance(source_lang, list):
            self.source_langs_list = source_lang
        else:
            self.source_langs_list = [source_lang]

        self.source_lang = self.source_langs_list[0]

        self._path_strategy: PathStrategy = self._create_path_strategy(mode)

        if self.logger:
            self.logger.info(f"[TranslationWorker] source_langs_list: {self.source_langs_list}")
            self.logger.info(f"[TranslationWorker] Режим: {mode}, стратегия: {self._path_strategy.__class__.__name__}")

    def _create_path_strategy(self, mode: str) -> PathStrategy:
        """
        Создает стратегию путей на основе режима.

        Args:
            mode: Режим перевода ('inplace', 'separate', 'merge')

        Returns:
            Экземпляр PathStrategy
        """
        if mode == "separate":
            return SeparatePathStrategy()
        else:
            return InplacePathStrategy()

    def _detect_best_source_languages(self, mod_path: str) -> list[str]:
        """
        Определяет исходные языки для мода.

        При auto_detect_source_lang=True:
        1. Проверяет доступные языки в моде (по Languages папкам и Defs содержимому)
        2. Возвращает все подходящие языки из source_langs_list
        3. Или English как эталон
        4. Или первый найденный (fallback)

        При auto_detect_source_lang=False:
        Возвращает сконфигурированный source_langs_list

        Args:
            mod_path: Путь к папке мода

        Returns:
            Список названий языков (например ['English', 'Russian'])
        """
        from scanner.mod_scanner import detect_mod_languages
        from utils.loadfolders_parser import find_all_defs_folders_with_loadfolders

        if not self.auto_detect_source_lang:
            return self.source_langs_list

        available_langs = detect_mod_languages(mod_path, self.logger)

        defs_folders = find_all_defs_folders_with_loadfolders(mod_path)
        if defs_folders:
            from scanner.mod_scanner import _scan_defs_for_languages
            defs_langs = _scan_defs_for_languages(mod_path, defs_folders, self.logger)
            if defs_langs:
                available_langs = list(set(available_langs) | defs_langs)
                if self.logger:
                    self.logger.debug(f"Дополнительные языки из Defs: {defs_langs}")

        if not available_langs:
            self.logger.debug(f"Не найдено языков в моде {mod_path}, используем default: {self.source_langs_list}")
            return self.source_langs_list

        result_langs = []

        for configured_lang in self.source_langs_list:
            if configured_lang in available_langs:
                result_langs.append(configured_lang)
                self.logger.info(f"Исходный язык найден в моде: {configured_lang}")

        if result_langs:
            return result_langs

        if "English" in available_langs:
            self.logger.info(f"English найден в моде, используем как исходный")
            return ["English"]

        fallback = available_langs[0]
        self.logger.info(f"Используем первый найденный язык: {fallback}")
        return [fallback]

    def _get_save_path(self, original_path: str, mod_path: str, mod_name: str) -> str:
        """
        Определяет путь для сохранения файла на основе стратегии.

        Args:
            original_path: Исходный путь к файлу
            mod_path: Путь к папке мода
            mod_name: Имя мода

        Returns:
            Путь для сохранения файла
        """
        return self._path_strategy.get_save_path(
            original_path=original_path,
            mod_path=mod_path,
            output_folder=self.output_folder,
            mod_name=mod_name
        )

    def _get_mod_output_path(self, mod_path: str, defs_folders_list: list[str] | None = None) -> str:
        """Определяет путь вывода в зависимости от режима."""
        return self._path_strategy.get_mod_output_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            output_folder=self.output_folder,
            defs_folders_list=defs_folders_list
        )

    def _should_create_backup(self) -> bool:
        """Определяет, нужно ли создавать резервные копии."""
        return self._path_strategy.should_create_backup()

    def _run(self) -> TranslationResultDTO:
        from utils.log_formatter import LogSection

        self.logger.info("═══════════════════════════════════════════════════════")
        self.logger.info(f"НАЧАЛО ПЕРЕВОДА: {self.source_langs_list} → {self.target_lang}")
        self.logger.info("═══════════════════════════════════════════════════════")

        self._progress(0, 100, "Инициализация переводчика...")
        try:
            with LogSection(self, "Инициализация", "") as section:
                self._auto_translator = AutoTranslator(
                    enabled=True,
                    logger=self.logger,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                    engine_names=self._engine_names,
                    config={"auto_split_glossary": self._auto_split_glossary},
                )
                if not self._auto_translator.enabled:
                    section.add_item(
                        "Переводчик отключен - будут использованы только существующие переводы",
                        "warning",
                    )
                    self._warnings.append("Переводчик отключен")
                else:
                    section.add_item("Переводчик инициализирован")
                    # ✅ НОВОЕ: Предзагружаем общие термины в кэш
                    preloaded = self._auto_translator.preload_common_terms(max_terms=500)
                    if preloaded > 0 and self.logger:
                        self.logger.info(f"Предзагружено {preloaded} терминов в кэш")

                os.makedirs(self.output_folder, exist_ok=True)
                section.add_item(f"Папка вывода: {self.output_folder}")

            mods = self._scan_mods()
            if not mods:
                self.logger.info("Моды для обработки не найдены")
                return TranslationResultDTO(success=True, warnings=self._warnings)

            self.logger.info(f"\nНайдено модов: {len(mods)}")
            self.logger.info("━" * 60)

            for idx, mod_path in enumerate(mods):
                if self._stop_requested:
                    break

                mod_name = get_mod_name(mod_path)
                self.logger.info(f"\n[{idx + 1}/{len(mods)}] Обработка мода: {mod_name}")
                self.logger.info("─" * 60)

                self._progress(
                    20 + int((idx / len(mods)) * 70), 100, f"Перевод {idx + 1}/{len(mods)}"
                )

                with LogSection(self, f"Мод: {mod_name}", "") as section:
                    self._translate_mod(mod_path, section)

            if not self._auto_translator or not self._auto_translator.enabled:
                self._copy_originals()

            self._progress(100, 100, "Перевод завершён")

            self.logger.info(f"\n{'=' * 60}")
            self.logger.info("ПЕРЕВОД ЗАВЕРШЁН")
            self.logger.info(f"{'=' * 60}")
            self.logger.info(f"   Модов обработано: {self._mods_processed}")
            self.logger.info(f"   Переведено записей: {self._translations_count}")
            if self._errors:
                self.logger.info(f"   Ошибок: {len(self._errors)}")
            if self._warnings:
                self.logger.info(f"   Предупреждений: {len(self._warnings)}")
            self.logger.info(f"{'=' * 60}\n")

            return TranslationResultDTO(
                success=len(self._errors) == 0,
                mods_processed=self._mods_processed,
                translations_count=self._translations_count,
                errors=self._errors,
                warnings=self._warnings,
            )
        except Exception as e:
            self._errors.append(str(e))
            self.logger.error(f"\nКРИТИЧЕСКАЯ ОШИБКА: {e}")
            raise

    def _scan_mods(self) -> list[str]:
        """Сканирует папку модов и возвращает список модов для обработки."""
        mods = []
        try:
            # Если есть выбранные моды, используем только их
            if self.selected_mods:
                self.logger.info(f"Используются выбранные моды: {len(self.selected_mods)}")
                for mod_name in self.selected_mods:
                    # Проверяем разные варианты пути к моду
                    possible_paths = [
                        os.path.join(self.mods_folder, mod_name),
                        self.mods_folder
                        if os.path.basename(self.mods_folder) == mod_name
                        else None,
                    ]

                    for mod_path in possible_paths:
                        if mod_path and os.path.exists(mod_path):
                            if os.path.exists(os.path.join(mod_path, "About")) or os.path.exists(
                                os.path.join(mod_path, "Defs")
                            ):
                                mods.append(mod_path)
                                break
                    else:
                        self._warnings.append(
                            f"Мод '{mod_name}' не найден в папке {self.mods_folder}"
                        )

                return mods

            # Если нет выбранных модов, сканируем все моды в папке
            if os.path.exists(os.path.join(self.mods_folder, "About")) or os.path.exists(
                os.path.join(self.mods_folder, "Defs")
            ):
                mods.append(self.mods_folder)
            else:
                for item in os.listdir(self.mods_folder):
                    mod_path = os.path.join(self.mods_folder, item)
                    if os.path.isdir(mod_path) and (
                        os.path.exists(os.path.join(mod_path, "About"))
                        or os.path.exists(os.path.join(mod_path, "Defs"))
                    ):
                        mods.append(mod_path)
        except Exception as e:
            self._errors.append(f"Ошибка сканирования: {e}")

        self.logger.info(f"Найдено модов для обработки: {len(mods)}")
        return mods

    def _translate_mod(self, mod_path: str, section=None) -> None:
        """Переводит один мод, обрабатывая Languages и Defs."""
        mod_name = get_mod_name(mod_path)
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

        # ✅ НОВОЕ: Определяем исходные языки для этого мода
        source_langs = self.source_langs_list
        if self.auto_detect_source_lang:
            source_langs = self._detect_best_source_languages(mod_path)
            if section:
                section.add_item(f"Исходные языки: {source_langs}", "info")

        current_source_lang = source_langs[0]

        all_lang_folders = []
        for lang in source_langs:
            lang_folders = find_all_language_folders(mod_path, lang)
            all_lang_folders.extend(lang_folders)
        prioritized_lang_folders = prioritize_language_folders(all_lang_folders, mod_path)
        all_defs_folders = find_all_defs_folders(mod_path)

        # ✅ ИСПРАВЛЕНО: Вычисляем пути ЯВНО до try: блока
        # ✅ НОВОЕ: Используем стратегию путей вместо ручного вычисления
        mod_output = self._get_mod_output_path(mod_path, all_defs_folders)
        mod_root = os.path.dirname(os.path.dirname(mod_output))  # Languages/../.. = mod_root

        if section:
            section.add_item(f"Корень выходного мода: {mod_root}", "info")
            section.add_item(f"Папка target языка: {mod_output}", "info")
            section.add_item(f"Папок Languages: {len(prioritized_lang_folders)}", "info")
            section.add_item(f"Папок Defs: {len(all_defs_folders)}", "info")

        try:
            # 0. Проверяем и создаём Languages для source языка
            self._progress(25, 100, f"Подготовка: {mod_name}")
            create_source_language_structure(mod_path, current_source_lang)
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

            # ✅ ИСПРАВЛЕНО: Пути рассчитываем явно, без хрупких os.path.dirname()
            # mod_root = output_folder/mod_name/ (корень выходного мода)
            # mod_output = output_folder/mod_name/Languages/target_lang (для обработки DefInjected/Keyed)

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

    def _ensure_target_language_structure(self, mod_path, mod_output, lang_folders, defs_folders):
        """Создаёт базовую структуру Languages для target языка через стратегию."""
        target_lang_base = self._path_strategy.get_mod_output_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            output_folder=self.output_folder,
            defs_folders_list=defs_folders
        )

        # Создаём папку если нужно
        created = False
        if not os.path.exists(target_lang_base):
            os.makedirs(target_lang_base, exist_ok=True)
            created = True

        if created:
            self.logger.info(f"✓ Создана папка Languages: {target_lang_base}")
        else:
            self.logger.info(f"✓ Languages уже существует: {target_lang_base}")

        # Создаём подпапки (DefInjected, Keyed)
        os.makedirs(os.path.join(target_lang_base, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(target_lang_base, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(target_lang_base, "Strings"), exist_ok=True)

    def _process_languages(self, mod_path: str, mod_output: str, lang_folders: list[str]) -> int:
        """Обрабатывает папки Languages (только Keyed XML файлы). Strings копируются отдельно."""
        count = 0
        # ✅ ИСПРАВЛЕНО: Собираем ВСЕ исходные папки Languages, не пропуская дубликаты целевой
        target_lang_folder = None  # Запоминаем целевую папку (Russian)

        for source_lang_folder in lang_folders:
            # ✅ ИСПРАВЛЕНО: Используем стратегию для вычисления целевой папки
            mod_name = get_mod_name(mod_path)
            current_target = self._path_strategy.get_save_path(
                original_path=source_lang_folder,
                mod_path=mod_path,
                output_folder=self.output_folder,
                mod_name=mod_name,
                target_lang=self.target_lang,
                source_lang=self.source_lang
            )

            # Запоминаем целевую папку (для backup и Morphy)
            if target_lang_folder is None:
                target_lang_folder = current_target

            # ✅ ВСЕГДА обрабатываем Strings (copy + translate)
            # Если папки нет в English, _copy_strings_folder выйдет сам
            self._copy_strings_folder(source_lang_folder, current_target)

            # Переводим только XML файлы из Keyed/
            keyed_source = os.path.join(source_lang_folder, "Keyed")
            keyed_target = os.path.join(current_target, "Keyed")
            if os.path.isdir(keyed_source):
                count += self._translate_folder(keyed_source, keyed_target, self.source_lang)

        # ✅ ИСПРАВЛЕНО: Backup создаём ОДИН РАЗ в конце, а не для каждой папки
        if target_lang_folder and self._should_create_backup():
            existing = self._check_existing_translation(target_lang_folder)
            if existing["exists"] and self.create_backup:
                self._create_backup(target_lang_folder)
                # ✅ Задержка для освобождения файловых дескрипторов Windows
                import time
                time.sleep(5)

        return count

    def _get_target_language_folder(
        self, mod_path: str, mod_output: str, source_folder: str, base_path: str, has_root: bool
    ) -> str:
        """Вычисляет путь к целевой папке языка через стратегию."""
        # ✅ ИСПРАВЛЕНО: Используем стратегию вместо старых функций
        mod_name = get_mod_name(mod_path)
        return self._path_strategy.get_save_path(
            original_path=source_folder,
            mod_path=mod_path,
            output_folder=self.output_folder,
            mod_name=mod_name,
            target_lang=self.target_lang,
            source_lang=self.source_lang
        )

    def _process_defs(self, defs_folders: list[str], mod_path: str, mod_output: str) -> int:
        """Обрабатывает папки Defs."""
        count =0
        all_defs_index = {}  # COMBINED index from ALL folders
        all_defs_rel = {}
        all_defs_meta = {}

        # Шаг1: Собираем ВСЕ defs_index из ВСЕХ папок
        from collectors.collectors import collect_defs_full

        for defs_folder in defs_folders:
            self.logger.info(f"  Сбор Defs из: {defs_folder}")
            defs_index, defs_rel, defs_meta = collect_defs_full(
                defs_dir=defs_folder,
                resolve_parents=True,
                process_patches_flag=True,
                logger=self.logger,
            )
            # ОБЪЕДИНЯЕМ с общим индексом
            all_defs_index.update(defs_index)
            all_defs_rel.update(defs_rel)
            all_defs_meta.update(defs_meta)

        if not all_defs_index:
            self.logger.info(f"  Defs не найдены ни в одной папке")
            return 0

        self.logger.info(f"  Всего собрано {len(all_defs_index)} Defs из {len(defs_folders)} папок")

        # Шаг2: Определяем путь DefInjected через стратегию
        # ✅ ИСПРАВЛЕНО: Используем стратегию вместо resolve_def_injected_path
        target_lang_base = self._path_strategy.get_mod_output_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            output_folder=self.output_folder,
            defs_folders_list=defs_folders
        )
        def_injected_path = os.path.join(target_lang_base, "DefInjected")

        # Создаём папку если нужно
        created = False
        if not os.path.exists(def_injected_path):
            os.makedirs(def_injected_path, exist_ok=True)
            created = True

        if created:
            self.logger.info(f"✓ Создана папка DefInjected: {def_injected_path}")

        # ✅ ОТЛАДКА: Показываем пути
        if self.logger:
            self.logger.info(f"[DEBUG] def_injected_path = {def_injected_path}")
            self.logger.info(f"[DEBUG] target_lang_base = {target_lang_base}")
            self.logger.info(f"[DEBUG] mod_output = {mod_output}")

        # Собираем source_map и keyed_map из всех исходных языков
        from collectors.collectors import collect_english_source, collect_keyed_entities

        source_map = {}
        keyed_map = {}

        for source_lang in self.source_langs_list:
            parent_dir = os.path.dirname(defs_folders[0])
            source_dir = os.path.join(parent_dir, "Languages", source_lang)
            if not os.path.exists(source_dir):
                source_dir = os.path.join(mod_path, "Common", "Languages", source_lang)
            if not os.path.exists(source_dir):
                source_dir = os.path.join(mod_path, "Languages", source_lang)

            if os.path.exists(source_dir):
                self.logger.info(f"Собираем исходные данные из: {source_lang}")
                source_map.update(collect_english_source(source_dir, logger=self.logger))
                keyed_map.update(collect_keyed_entities(source_dir, logger=self.logger))

        # Собираем существующие переводы
        existing_map = {}
        existing_index = {}
        existing_origin = {}
        if os.path.exists(def_injected_path):
            for root_dir, _, files in os.walk(def_injected_path):
                for fn in files:
                    if fn.endswith(".xml"):
                        path = os.path.join(root_dir, fn)
                        try:
                            with open(path, encoding="utf-8") as f:
                                content = f.read()
                            root = safe_parse_xml(path)
                            if root is None:
                                continue
                            en_comments = {}
                            for match in re.finditer(r"<!--\s*EN:\s*(.*?)\s*-->", content):
                                after_comment = content[match.end():]
                                tag_match = re.match(r"\s*<([^>/]+)>", after_comment)
                                if tag_match:
                                    en_comments[tag_match.group(1)] = match.group(1).strip()
                            for child in root:
                                if child.tag and child.text and child.text.strip():
                                    tag = child.tag
                                    clean_tag = tag
                                    if tag.startswith("_OBSOLETE_"):
                                        clean_tag = tag[len("_OBSOLETE_"):]
                                    existing_map[clean_tag] = child.text.strip()
                                    existing_index[clean_tag] = path
                                    if clean_tag in en_comments:
                                        existing_origin[clean_tag] = en_comments[clean_tag]
                        except Exception as e:
                            self.logger.debug(f"Ошибка чтения {path}: {e}")

        # Вызываем генерацию с проверкой устаревших тегов
        # ✅ Доверяем внутренней логике gen_def_files (check_obsolete=True по умолчанию)
        # Это обеспечивает консистентность данных
        created_files = gen_def_files(
            defs_index=all_defs_index,
            defs_rel=all_defs_rel,
            defs_source_abs={},
            defs_file_map={},
            defs_meta=all_defs_meta,
            keyed_map=keyed_map,
            source_map=source_map,
            existing_map=existing_map,
            existing_index=existing_index,
            existing_origin=existing_origin,
            target_lang_dir=target_lang_base,
            logger=self.logger,
            aggressive=False,
            use_api=self._auto_translator.enabled if self._auto_translator else False,
            lang_to=self.target_lang,
            cleanup_orphans=True,
            fuzzy=self.fuzzy,
            engine_names=self._engine_names,  # ✅ НОВОЕ: передаём список движков
            glossary_manager=self._auto_translator.glossary_manager if self._auto_translator else None,  # ✅ НОВОЕ: кэшированный glossary_manager
        )

        count = len(created_files)

        # ✅ УБРАНО: Ручной вызов process_obsolete_tags
        # Теперь это делает gen_def_files внутри (check_obsolete=True)
        return count

    def _finalize_mod(
        self, mod_path: str, mod_root: str, mod_output: str, translations_count: int, mod_name: str
    ) -> None:
        """Финальные действия после перевода мода."""
        if translations_count >0 and self.mode == "separate":
            os.makedirs(mod_root, exist_ok=True)
            self._create_translation_mod_about(mod_root, mod_name, mod_path)

            # ✅ НОВОЕ: Копируем LoadFolders.xml для совместимости с RimWorld 2026
            self._copy_loadfolders_xml(mod_path, mod_root)

    def _create_translation_mod_about(
        self, mod_output: str, original_mod_name: str, original_mod_path: str
    ) -> None:
        about_folder = os.path.join(mod_output, "About")
        os.makedirs(about_folder, exist_ok=True)
        about_path = os.path.join(about_folder, "About.xml")

        # Значения по умолчанию
        original_package_id = "Unknown"
        supported_versions = ["1.6"]  # Список версий по умолчанию для 2026

        try:
            original_about = os.path.join(original_mod_path, "About", "About.xml")
            if os.path.exists(original_about):
                root = safe_parse_xml(original_about)
                if root is not None:
                    # Получаем packageId исходного мода
                    package_id_elem = root.find("packageId")
                    if package_id_elem is not None and package_id_elem.text:
                        original_package_id = package_id_elem.text.strip()

                    # ✅ ИСПРАВЛЕНО: Извлекаем ВСЕ поддерживаемые версии
                    supported_versions_elem = root.find("supportedVersions")
                    if supported_versions_elem is not None:
                        versions = [v.text.strip() for v in supported_versions_elem.findall("li") if v.text]
                        if versions:
                            supported_versions = versions
                    else:
                        # Если нет supportedVersions, пробуем version
                        version_elem = root.find("version")
                        if version_elem is not None and version_elem.text:
                            supported_versions = [version_elem.text.strip()]

        except Exception as e:
            self.logger.warning(f"Не удалось прочитать метаданные: {e}")

        # ✅ ИСПРАВЛЕНО: Формируем правильный XML для RimWorld 2026
        versions_xml = "\n".join([f"    <li>{v}</li>" for v in supported_versions])

        # ✅ ИСПРАВЛЕНО: Берём самую свежую версию для targetVersion
        target_version = sorted(supported_versions, reverse=True)[0]

        about_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
    <packageId>{original_package_id}.{self.target_lang.lower()}.translation</packageId>
    <name>{original_mod_name} ({self.target_lang})</name>
    <description>Автоматический перевод мода {original_mod_name} на {self.target_lang}.</description>
    <author>Auto-Translated</author>
    <targetMod>
        <packageId>{original_package_id}</packageId>
    </targetMod>
    <supportedVersions>
{versions_xml}
    </supportedVersions>
    <targetVersion>{target_version}</targetVersion>
</ModMetaData>"""

        try:
            with open(about_path, "w", encoding="utf-8") as f:
                f.write(about_content)
            self.logger.info(f"✅ About.xml создан: {about_path}")
        except Exception as e:
            self.logger.warning(f"Не удалось создать About.xml: {e}")

    def _copy_loadfolders_xml(self, original_mod_path: str, mod_root: str) -> None:
        """Создаёт минимальный LoadFolders.xml для translation mod (RimWorld 2026)."""
        if self.mode != "separate":
            return

        loadfolders_path = os.path.join(mod_root, "LoadFolders.xml")

        # ✅ ИСПРАВЛЕНО: ВСЕГДА создаём минимальный LoadFolders.xml для translation mod
        # НЕ копируем из оригинального мода, так как там могут быть DLC-специфичные папки
        version = "1.6"
        try:
            original_about = os.path.join(original_mod_path, "About", "About.xml")
            if os.path.exists(original_about):
                root = safe_parse_xml(original_about)
                if root is not None:
                    supported = root.find("supportedVersions")
                    if supported is not None:
                        versions = [v.text.strip() for v in supported.findall("li") if v.text]
                        if versions:
                            version = sorted(versions, reverse=True)[0]
        except Exception:
            pass

        # ✅ Минимальная структура для translation mod (RimWorld 2026)
        loadfolders_content = f'''<?xml version="1.0" encoding="utf-8"?>
<loadFolders>
  <v{version.replace(".", "")}>
    <li>Common</li>
    <li>{version}</li>
  </v{version.replace(".", "")}>
</loadFolders>'''

        try:
            with open(loadfolders_path, "w", encoding="utf-8") as f:
                f.write(loadfolders_content)
            self.logger.info(f"✅ LoadFolders.xml создан: {loadfolders_path}")
        except Exception as e:
            self.logger.warning(f"Не удалось создать LoadFolders.xml: {e}")

    def _translate_folder(self, source_folder: str, output_folder: str, source_lang: str) -> int:
        """Переводит XML файлы в папке (Keyed или DefInjected). TXT файлы игнорируются."""
        translations_count = 0
        for root, dirs, files in os.walk(source_folder):
            for filename in files:
                if filename.endswith(".xml"):
                    source_file = os.path.join(root, filename)
                    relative_path = os.path.relpath(root, source_folder)
                    output_file = os.path.join(output_folder, relative_path, filename)
                    try:
                        translations_count += self._translate_xml_file(
                            source_file, output_file, source_lang
                        )
                    except Exception as e:
                        self._warnings.append(f"Ошибка перевода {filename}: {e}")
        return translations_count

    def _translate_xml_file(self, source_file: str, output_file: str, source_lang: str) -> int:
        """Переводит один XML файл (DefInjected/Keyed).
        
        Поддерживает плейсхолдеры RimWorld: {0}, {1}, {name}, $ и т.д.
        Перевод текста выполняется с сохранением плейсхолдеров.
        """
        translations_count = 0

        if os.path.exists(output_file) and not self.force_update:
            return 0

        try:
            root = safe_parse_xml(source_file)
            if root is None:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                shutil.copy2(source_file, output_file)
                return 0

            for elem in root.iter():
                if elem.text and elem.text.strip():
                    original = elem.text.strip()
                    
                    if self._auto_translator and self._auto_translator.enabled:
                        try:
                            # Сохраняем плейсхолдеры перед переводом
                            placeholders = []
                            
                            def save_placeholder(match):
                                placeholders.append(match.group(0))
                                return f"__PLACEHOLDER_{len(placeholders)-1}__"
                            
                            # Сохраняем фигурные скобки {0}, {name}, и т.п.
                            text_to_translate = re.sub(r'\{[a-zA-Z0-9_]+\}', save_placeholder, original)
                            # Сохраняем $ переменные
                            text_to_translate = re.sub(r'\$[a-zA-Z0-9_]+', save_placeholder, text_to_translate)
                            
                            translated = self._auto_translator.translate(text_to_translate)
                            
                            if translated:
                                # Восстанавливаем плейсхолдеры
                                for i, placeholder in enumerate(placeholders):
                                    translated = translated.replace(f"__PLACEHOLDER_{i}__", placeholder)
                                
                                elem.text = translated
                                translations_count += 1
                        except Exception as e:
                            self.logger.warning(f"Ошибка перевода: {e}")
                    else:
                        translations_count += 1

            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            tree = etree.ElementTree(root)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            self._warnings.append(f"Ошибка парсинга XML {source_file}: {e}")
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                shutil.copy2(source_file, output_file)
            except Exception:
                pass

        return translations_count

    def _translate_txt_file(self, source_file: str, output_file: str, source_lang: str) -> int:
        """Переводит текстовый файл (Strings/*.txt) построчно.
        
        Поддерживает плейсхолдеры RimWorld: {0}, {1}, {name}, $ и т.д.
        Перевод текста выполняется с сохранением плейсхолдеров.
        """
        translations_count = 0

        if os.path.exists(output_file) and not self.force_update:
            return 0

        try:
            # ✅ ИСПРАВЛЕНО: Используем безопасное чтение файла
            content = _safe_read_file(source_file, encoding="utf-8")
            if content is None:
                raise OSError(f"Не удалось прочитать файл: {source_file}")

            lines = content.splitlines(keepends=True)

            translated_lines = []
            for line in lines:
                stripped = line.rstrip("\r\n")
                # Пропускаем пустые строки и комментарии (начинающиеся с #)
                if stripped and not stripped.startswith("#"):
                    if self._auto_translator and self._auto_translator.enabled:
                        try:
                            # Сохраняем плейсхолдеры перед переводом
                            placeholders = []
                            
                            def save_placeholder(match):
                                placeholders.append(match.group(0))
                                return f"__PLACEHOLDER_{len(placeholders)-1}__"
                            
                            # Сохраняем фигурные скобки {0}, {name}, и т.п.
                            text_to_translate = re.sub(r'\{[a-zA-Z0-9_]+\}', save_placeholder, stripped)
                            # Сохраняем $ переменные
                            text_to_translate = re.sub(r'\$[a-zA-Z0-9_]+', save_placeholder, text_to_translate)
                            
                            translated = self._auto_translator.translate(text_to_translate, stripped)
                            
                            if translated:
                                # Восстанавливаем плейсхолдеры
                                for i, placeholder in enumerate(placeholders):
                                    translated = translated.replace(f"__PLACEHOLDER_{i}__", placeholder)
                                
                                translated_lines.append(translated + "\n")
                                translations_count += 1
                                continue
                        except Exception as e:
                            self.logger.warning(f"Ошибка перевода строки '{stripped[:30]}...': {e}")
                    # Если переводчик отключён или ошибка — оставляем оригинал
                    translated_lines.append(line)
                else:
                    translated_lines.append(line)

            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # ✅ ИСПРАВЛЕНО: Если исходный и целевой файлы совпадают (inplace режим),
            # записываем временный файл, затем переименовываем (атомарно)
            if os.path.normpath(source_file) == os.path.normpath(output_file):
                import tempfile
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding="utf-8",
                    dir=os.path.dirname(output_file),
                    suffix='.tmp',
                    delete=False
                ) as f:
                    f.write("".join(translated_lines))
                    temp_path = f.name
                os.replace(temp_path, output_file)
            else:
                # ✅ ИСПРАВЛЕНО: Используем безопасную запись файла
                _safe_write_file(output_file, "".join(translated_lines), encoding="utf-8")

            self.logger.debug(f"Переведён txt файл: {os.path.relpath(output_file, self.mods_folder)} ({translations_count} строк)")

        except Exception as e:
            self._warnings.append(f"Ошибка обработки txt {source_file}: {e}")
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                # ✅ ИСПРАВЛЕНО: Используем безопасное копирование
                _safe_copy_file(source_file, output_file)
            except Exception:
                pass

        return translations_count

    def _translate_file(self, source_file: str, output_file: str, source_lang: str) -> int:
        """Переводит один XML файл."""
        translations_count = 0

        # ✅ ПРОВЕРКА: Если файл уже существует и НЕ включено принудительное обновление — пропускаем
        if os.path.exists(output_file) and not self.force_update:
            self.logger.debug(
                f"Пропускаем уже существующий: {os.path.relpath(output_file, self.mods_folder)}"
            )
            return 0  # Ничего не переводим

        try:
            root = safe_parse_xml(source_file)
            if root is None:
                # Не удалось распарсить - копируем как есть

                shutil.copy2(source_file, output_file)
                return 0

            for elem in root.iter():
                if elem.text and elem.text.strip():
                    original = elem.text.strip()
                    if "{" in original or "$" in original:
                        continue
                    if self._auto_translator and self._auto_translator.enabled:
                        try:
                            translated = self._auto_translator.translate(original, original)
                            if translated:
                                elem.text = translated
                                translations_count += 1
                        except Exception as e:
                            self.logger.warning(f"Ошибка перевода: {e}")
                    else:
                        translations_count += 1

            # Создаем папку перед записью файла
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Записываем XML

            tree = etree.ElementTree(root)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            self._warnings.append(f"Ошибка парсинга XML {source_file}: {e}")
            try:

                shutil.copy2(source_file, output_file)
            except Exception:
                pass
        return translations_count

    def _copy_originals(self) -> None:
        for mod_path in self._scan_mods():
            mod_name = get_mod_name(mod_path)
            if self.mode == "inplace":
                continue
            mod_output = os.path.join(self.output_folder, mod_name)
            source_langs = os.path.join(mod_path, "Languages")
            if os.path.exists(source_langs):
                target_langs = os.path.join(mod_output, "Languages")
                self._copy_folder(source_langs, target_langs)

    def _copy_folder(self, source: str, destination: str) -> None:

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)
        for root, dirs, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            dest_path = os.path.join(destination, rel_path)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path, exist_ok=True)
            for filename in files:
                shutil.copy2(os.path.join(root, filename), os.path.join(dest_path, filename))

    def _copy_strings_folder(self, source_lang_folder: str, target_lang_folder: str) -> None:
        """Копирует и переводит папку Strings из исходного языка в целевой."""
        source_strings = os.path.join(source_lang_folder, "Strings")
        if not os.path.isdir(source_strings):
            self.logger.debug(f"[Strings] Нет папки в {source_lang_folder}")
            return

        target_strings = os.path.join(target_lang_folder, "Strings")

        # ✅ ИСПРАВЛЕНО: Собираем все файлы сначала, затем обрабатываем
        # Это избегает проблем с os.walk() и одновременным изменением файлов на Windows
        files_to_process = []
        for root, dirs, files in os.walk(source_strings):
            rel_path = os.path.relpath(root, source_strings)
            target_dir = os.path.join(target_strings, rel_path)
            os.makedirs(target_dir, exist_ok=True)

            for filename in files:
                source_file = os.path.join(root, filename)
                target_file = os.path.join(target_dir, filename)
                files_to_process.append((source_file, target_file, rel_path, filename))

        # Теперь обрабатываем файлы (не находясь внутри os.walk())
        for source_file, target_file, rel_path, filename in files_to_process:
            if filename.endswith(".txt"):
                # ✅ ИСКЛЮЧЕНИЕ: Файлы грамматики (Grammar/) не переводим
                full_rel_path = os.path.join(rel_path, filename)
                grammar_marker = os.path.join("Grammar", "")
                if grammar_marker in full_rel_path or "Grammar/" in full_rel_path:
                    # Копируем как есть - это грамматические мета-данные
                    try:
                        _safe_copy_file(source_file, target_file)
                        self.logger.debug(f"[Strings] Скопирован (мета-данные): {full_rel_path}")
                    except Exception as e:
                        self.logger.warning(f"[Strings] Ошибка копирования {filename}: {e}")
                else:
                    # ✅ Проверяем, существует ли уже переведённый файл
                    if os.path.exists(target_file) and not self.force_update:
                        # Проверяем, есть ли в файле перевод (не просто копия English)
                        try:
                            with open(target_file, "r", encoding="utf-8") as f:
                                content = f.read()
                            # Если файл не пустой и содержит кириллицу - пропускаем
                            if content.strip() and any(ord(c) > 127 for c in content):
                                self.logger.debug(f"[Strings] Пропуск (уже переведён): {filename}")
                                continue
                        except Exception:
                            pass

                    # ✅ Переводим .txt файлы (списки слов)
                    try:
                        count = self._translate_txt_file(source_file, target_file, "English")
                        if count > 0:
                            self.logger.info(f"[Strings] Переведён: {filename} ({count} строк)")
                        else:
                            # Если перевод не удался - копируем как есть
                            try:
                                _safe_copy_file(source_file, target_file)
                            except Exception as e:
                                self.logger.warning(f"[Strings] Ошибка копирования {filename}: {e}")
                    except Exception as e:
                        self.logger.warning(f"[Strings] Ошибка перевода {filename}: {e}")
                        try:
                            _safe_copy_file(source_file, target_file)
                        except Exception as e:
                            self.logger.warning(f"[Strings] Ошибка копирования {filename}: {e}")
            else:
                # Нетекстовые файлы просто копируем
                try:
                    _safe_copy_file(source_file, target_file)
                except Exception as e:
                    self.logger.warning(f"[Strings] Ошибка копирования {filename}: {e}")


        self.logger.info(f"[Strings] Обработана: {os.path.relpath(source_strings, self.mods_folder)}")


        # ✅ НОВОЕ: Запускаем Morphy.py для генерации правильных грамматических форм
        # ✅ ИСПРАВЛЕНО: Вызываем Morphy.py в конце перевода
        if self.target_lang.lower() in ['russian', 'ru']:
            target_strings = os.path.join(self._current_mod_output, "Strings")
            self._run_morphy_for_strings(target_strings, self._current_mod_output)
    def _run_morphy_for_strings(self, target_strings: str, mod_output: str) -> None:
        """Запускает Morphy.py для генерации правильных грамматических форм."""
        if not os.path.isdir(target_strings):
            return

        try:
            from utils.Morphy import RimWorldUniversalParser

            self.logger.info(f"[Morphy] Обработка {target_strings}")

            parser = RimWorldUniversalParser(lang=self.target_lang.lower())

            # Собираем все .txt файлы (кроме Grammar/)
            txt_files = []
            for root, dirs, files in os.walk(target_strings):
                if 'Grammar' in root:
                    continue
                for filename in files:
                    if filename.endswith('.txt') and not filename.startswith('.'):
                        txt_files.append(os.path.join(root, filename))

            if not txt_files:
                self.logger.debug("[Morphy] Нет .txt файлов")
                return

            self.logger.info(f"[Morphy] Найдено {len(txt_files)} .txt файлов")

            # Определяем папку для выходных XML
            def_injected_path = os.path.join(mod_output, "DefInjected", "RulePackDef")
            os.makedirs(def_injected_path, exist_ok=True)

            # Обрабатываем каждый файл
            for txt_file in txt_files:
                rel_path = os.path.relpath(txt_file, target_strings)
                base_name = os.path.splitext(rel_path)[0].replace(os.sep, '_')
                # ✅ ИСПРАВЛЕНО: Правильный регистр (RulePack_ единственное число)
                def_name = base_name
                output_path = os.path.join(def_injected_path, f"RulePack_{base_name}.xml")

                try:
                    result = parser.generate_balanced_xml(txt_file, def_name, output_path)
                    if result and os.path.exists(result):
                        self.logger.debug(f"[Morphy] {rel_path} -> {os.path.basename(result)}")
                except Exception as e:
                    self.logger.debug(f"[Morphy] Ошибка {rel_path}: {e}")

            self.logger.info(f"[Morphy] ✓ Обработка завершена")

        except ImportError:
            self.logger.debug("[Morphy] Morphy.py недоступен (pymorphy3 не установлен?)")
        except Exception as e:
            self.logger.warning(f"[Morphy] Ошибка: {e}")

    def _check_existing_translation(self, target_lang_folder: str) -> dict:
        result = {"exists": False, "files_count": 0, "entries_count": 0}
        if not os.path.exists(target_lang_folder):
            return result
        result["exists"] = True

        for root, _, files in os.walk(target_lang_folder):
            for f in files:
                if f.endswith(".xml"):
                    result["files_count"] += 1
                    try:
                        xml_root = safe_parse_xml(os.path.join(root, f))
                        if xml_root is not None:
                            for elem in xml_root.iter():
                                if elem.text and elem.text.strip():
                                    result["entries_count"] += 1
                    except Exception:
                        pass
        return result

    def _create_backup(self, folder_path: str) -> str | None:
        """Создать резервную копию через централизованный менеджер."""
        from utils.backup_manager import get_backup_manager

        backup_manager = get_backup_manager()
        return backup_manager.create_backup(folder_path, logger=self.logger)

    def _extract_and_translate_to_def_injected(self, source_file: str, output_file: str) -> int:
        """Извлекает DefInjected переводы из Defs файла."""
        translations_count = 0
        extracted_entries = []

        # ✅ ПРОВЕРКА: Если DefInjected файл уже существует и НЕ включено принудительное обновление — пропускаем
        if os.path.exists(output_file) and not self.force_update:
            self.logger.debug(
                f"Пропускаем уже существующий DefInjected: {os.path.relpath(output_file, self.mods_folder)}"
            )
            return 0


        try:
            root = safe_parse_xml(source_file)
            if root is not None:
                for def_elem in root:
                    if not isinstance(def_elem, etree._Element):
                        continue
                    if def_elem.get("Abstract", "false").lower() == "true":
                        continue
                    def_name_elem = def_elem.find("defName")
                    if def_name_elem is None or not def_name_elem.text:
                        continue
                    def_name = def_name_elem.text.strip().replace(" ", "_")
                    def_type = def_elem.tag
                    entries = self._extract_translatable_strings(
                        def_elem, def_type, def_name, {t.lower() for t in TRANSLATABLE_TAGS}
                    )
                    extracted_entries.extend(entries)
            translated_entries = []
            for def_type, def_name, path, original_text in extracted_entries:
                if self._auto_translator and self._auto_translator.enabled:
                    try:
                        translated = self._auto_translator.translate(original_text)
                        if translated:
                            translated_entries.append((def_type, def_name, path, translated))
                            translations_count += 1
                        else:
                            translated_entries.append((def_type, def_name, path, original_text))
                            translations_count += 1
                    except Exception as e:
                        self.logger.warning(f"Ошибка перевода: {e}")
                        translated_entries.append((def_type, def_name, path, original_text))
                else:
                    translated_entries.append((def_type, def_name, path, original_text))
                    translations_count += 1
            if translated_entries:
                self._write_def_injected_file(output_file, translated_entries)
        except etree.XMLSyntaxError as e:
            self._warnings.append(f"Ошибка парсинга XML {source_file}: {e}")
        return translations_count

    def _extract_translatable_strings(
        self, element, def_type: str, def_name: str, translatable_tags: set, path: str = ""
    ) -> list:
        entries = []
        list_counters = {}
        for child in element:
            if not hasattr(child, "tag"):
                continue
            tag = child.tag
            if tag == "li":
                idx = list_counters.get("li", 0)
                list_counters["li"] = idx + 1
                current_path = f"{path}.{idx}" if path else str(idx)
            else:
                current_path = f"{path}.{tag}" if path else tag
            if tag.lower() in translatable_tags and child.text and child.text.strip():
                text = child.text.strip()
                if "{" not in text and not text.startswith("$") and not text.startswith("RGB"):
                    full_key = f"{def_type}_{def_name}.{current_path}"
                    entries.append((def_type, def_name, current_path, text))
            if len(list(child)) > 0:
                entries.extend(
                    self._extract_translatable_strings(
                        child, def_type, def_name, translatable_tags, current_path
                    )
                )
        return entries

    def _write_def_injected_file(self, output_file: str, entries: list) -> None:
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        lines = ['<?xml version="1.0" encoding="utf-8"?>', "<LanguageData>"]
        for def_type, def_name, path, translated_text in entries:
            tag_name = f"{def_name}.{path}".replace(" ", "_")
            lines.append(f"\t<{tag_name}>{translated_text}</{tag_name}>")
        lines.append("</LanguageData>")
        with open(output_file, "w", encoding="utf-8", newline="\r\n") as f:
            f.write("\n".join(lines))
