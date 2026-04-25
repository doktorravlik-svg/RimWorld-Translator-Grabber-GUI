# workers/translation_worker.py
"""
Worker для асинхронного перевода модов.
"""

import logging
import os
from typing import Any

# ✅ НОВОЕ: Используем единый модуль для путей
from utils.path_utils import ensure_project_root_in_path

ensure_project_root_in_path()

from translation.translator import AutoTranslator

# ✅ НОВОЕ: Используем единый модуль для путей Languages
from utils.languages_path_resolver import (
    create_source_language_structure,
    find_all_defs_folders,
    find_all_language_folders,
    get_mod_output_path,
    prioritize_language_folders,
    resolve_def_injected_path,
    resolve_target_languages_path,
)
from utils.rimworld_xml import TRANSLATABLE_TAGS

# ✅ НОВОЕ: Используем единый модуль для XML-парсинга
from utils.xml_utils import safe_parse_xml

from .base_worker import BaseWorker


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
        source_lang: str = "English",
        target_lang: str = "Russian",
        output_folder: str | None = None,
        logger: logging.Logger | None = None,
        mode: str = "separate",
        create_backup: bool = True,
        selected_mods: list[str] | None = None,
        force_update: bool = False,
        fuzzy: bool = True,  # ✅ НОВОЕ: Fuzzy поиск переводов
    ):
        super().__init__()
        self.mods_folder = mods_folder
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.output_folder = output_folder or os.path.join(mods_folder, "Translated")
        self.logger = logger or logging.getLogger(__name__)
        self.mode = mode
        self.create_backup = create_backup
        self.selected_mods = selected_mods or []
        self.force_update = force_update
        self.fuzzy = fuzzy  # ✅ НОВОЕ: Fuzzy поиск
        self._auto_translator: AutoTranslator | None = None
        self._mods_processed = 0
        self._translations_count = 0
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def _run(self) -> TranslationResultDTO:
        from utils.log_formatter import LogSection

        self.logger.info("═══════════════════════════════════════════════════════")
        self.logger.info(f"НАЧАЛО ПЕРЕВОДА: {self.source_lang} → {self.target_lang}")
        self.logger.info("═══════════════════════════════════════════════════════")

        self._progress(0, 100, "Инициализация переводчика...")
        try:
            with LogSection(self, "Инициализация", "") as section:
                self._auto_translator = AutoTranslator(
                    enabled=True,
                    logger=self.logger,
                    source_lang=self.source_lang,
                    target_lang=self.target_lang,
                )
                if not self._auto_translator.enabled:
                    section.add_item(
                        "Переводчик отключен - будут использованы только существующие переводы",
                        "warning",
                    )
                    self._warnings.append("Переводчик отключен")
                else:
                    section.add_item("Переводчик инициализирован")

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

                mod_name = os.path.basename(mod_path)
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
        mod_name = os.path.basename(mod_path)
        mode_names = {"separate": "separate", "inplace": "inplace", "merge": "merge"}

        if section:
            section.add_item(f"Режим: {mode_names.get(self.mode, self.mode)}", "info")

        try:
            # 0. Проверяем и создаём Languages для source языка, если нужно
            self._progress(25, 100, f"Подготовка: {mod_name}")
            create_source_language_structure(mod_path, self.source_lang)
            if section:
                section.add_item("✓ Структура Languages проверена", "success")

            # 0.1 Определяем выходную папку
            mod_output = get_mod_output_path(mod_path, self.target_lang, self.output_folder)

            # 0.2 Находим папки для перевода
            all_lang_folders = find_all_language_folders(mod_path, self.source_lang)
            prioritized_lang_folders = prioritize_language_folders(all_lang_folders, mod_path)
            all_defs_folders = find_all_defs_folders(mod_path)

            if section:
                section.add_item(f"Папок Languages: {len(prioritized_lang_folders)}", "info")
                section.add_item(f"Папок Defs: {len(all_defs_folders)}", "info")

            # ВАЖНО: Сохраняем для использования в методах обработки
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
            self._finalize_mod(mod_path, mod_output, translations_count, mod_name)

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
        """Создаёт базовую структуру Languages для target языка через единый модуль."""
        target_lang_base, created = resolve_target_languages_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            mod_output=mod_output,
            mode=self.mode,
            defs_folders_list=defs_folders,
            create_if_missing=True,
        )

        if created:
            self.logger.info(f"✓ Создана папка Languages: {target_lang_base}")
        else:
            self.logger.info(f"✓ Languages уже существует: {target_lang_base}")

    def _get_mod_output_path(self, mod_path: str) -> str:
        """Определяет путь вывода в зависимости от режима."""
        return get_mod_output_path(mod_path, self.target_lang, self.output_folder)

    def _process_languages(self, mod_path: str, mod_output: str, lang_folders: list[str]) -> int:
        """Обрабатывает папки Languages."""
        count = 0
        processed_targets = set()

        for source_lang_folder in lang_folders:
            # Определяем целевую папку через единый модуль
            target_lang_folder = self._get_target_language_folder(
                mod_path, mod_output, source_lang_folder, "", False
            )

            # Пропускаем дубликаты
            if target_lang_folder in processed_targets:
                continue
            processed_targets.add(target_lang_folder)

            # Проверяем бэкап и переводим
            if self.mode in ("inplace", "merge"):
                existing = self._check_existing_translation(target_lang_folder)
                if existing["exists"]:
                    self.logger.info(
                        f"Найден существующий перевод: {existing['files_count']} файлов"
                    )
                    if self.create_backup:
                        self._create_backup(target_lang_folder)

            count += self._translate_folder(
                source_lang_folder, target_lang_folder, self.source_lang
            )

        return count

    def _get_target_language_folder(
        self, mod_path: str, mod_output: str, source_folder: str, base_path: str, has_root: bool
    ) -> str:
        """Вычисляет путь к целевой папке языка через единый модуль."""
        # ✅ ИСПОЛЬЗУЕМ сохранённые defs_folders вместо пустого списка
        target_folder, _ = resolve_target_languages_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            mod_output=self._current_mod_output,
            mode=self.mode,
            defs_folders_list=self._current_defs_folders,
            create_if_missing=True,
        )

        return target_folder

    def _process_defs(self, defs_folders: list[str], mod_path: str, mod_output: str) -> int:
        """Обрабатывает папки Defs."""
        count = 0
        for defs_folder in defs_folders:
            count += self._translate_defs_folder(defs_folder, mod_path, mod_output)
        return count

    def _finalize_mod(
        self, mod_path: str, mod_output: str, translations_count: int, mod_name: str
    ) -> None:
        """Финальные действия после перевода мода."""
        if translations_count > 0 and self.mode == "separate":
            os.makedirs(mod_output, exist_ok=True)
            self._create_translation_mod_about(mod_output, mod_name, mod_path)

    def _create_translation_mod_about(
        self, mod_output: str, original_mod_name: str, original_mod_path: str
    ) -> None:
        about_folder = os.path.join(mod_output, "About")
        os.makedirs(about_folder, exist_ok=True)
        about_path = os.path.join(about_folder, "About.xml")
        original_package_id = original_mod_name
        mod_version = "1.6"  # Версия по умолчанию

        try:
            import lxml.etree as etree

            original_about = os.path.join(original_mod_path, "About", "About.xml")
            if os.path.exists(original_about):
                root = safe_parse_xml(original_about)
                if root is not None:
                    package_id_elem = root.find("packageId")
                    if package_id_elem is not None and package_id_elem.text:
                        original_package_id = package_id_elem.text.strip()

                    # Извлекаем версию из оригинального мода
                    version_elem = root.find("version")
                    if version_elem is not None and version_elem.text:
                        mod_version = version_elem.text.strip()
                    else:
                        # Пробуем найти в supportedVersions
                        supported_versions = root.find("supportedVersions")
                        if supported_versions is not None:
                            version_list = [v.text.strip() for v in supported_versions if v.text]
                            if version_list:
                                mod_version = sorted(version_list, reverse=True)[0]
        except Exception as e:
            self.logger.warning(f"Не удалось прочитать метаданные: {e}")

        about_content = f"""<?xml version="1.0" encoding="utf-8"?>
<ModMetaData>
    <packageId>{original_package_id}.{self.target_lang.lower()}.translation</packageId>
    <name>{original_mod_name} ({self.target_lang})</name>
    <description>Автоматический перевод мода {original_mod_name} на {self.target_lang}.</description>
    <author>Auto-Translated</author>
    <targetMod><packageId>{original_package_id}</packageId></targetMod>
    <supportedVersions><li>{mod_version}</li></supportedVersions>
</ModMetaData>"""
        try:
            with open(about_path, "w", encoding="utf-8") as f:
                f.write(about_content)
        except Exception as e:
            self.logger.warning(f"Не удалось создать About.xml: {e}")

    def _translate_folder(self, source_folder: str, output_folder: str, source_lang: str) -> int:
        translations_count = 0
        for root, dirs, files in os.walk(source_folder):
            for filename in files:
                if filename.endswith(".xml"):
                    source_file = os.path.join(root, filename)
                    relative_path = os.path.relpath(root, source_folder)
                    output_file = os.path.join(output_folder, relative_path, filename)
                    try:
                        translations_count += self._translate_file(
                            source_file, output_file, source_lang
                        )
                    except Exception as e:
                        self._warnings.append(f"Ошибка перевода {filename}: {e}")
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
                import shutil

                shutil.copy2(source_file, output_file)
                return 0

            for elem in root.iter():
                if elem.text and elem.text.strip():
                    original = elem.text.strip()
                    if "{" in original or "$" in original:
                        continue
                    if self._auto_translator and self._auto_translator.enabled:
                        try:
                            translated = self._auto_translator.translate(original)
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
            import lxml.etree as etree

            tree = etree.ElementTree(root)
            tree.write(output_file, encoding="utf-8", xml_declaration=True)
        except Exception as e:
            self._warnings.append(f"Ошибка парсинга XML {source_file}: {e}")
            try:
                import shutil

                shutil.copy2(source_file, output_file)
            except Exception:
                pass
        return translations_count

    def _copy_originals(self) -> None:
        for mod_path in self._scan_mods():
            mod_name = os.path.basename(mod_path)
            if self.mode == "inplace":
                continue
            mod_output = os.path.join(self.output_folder, f"{mod_name}-{self.target_lang}")
            source_langs = os.path.join(mod_path, "Languages")
            if os.path.exists(source_langs):
                target_langs = os.path.join(mod_output, "Languages")
                self._copy_folder(source_langs, target_langs)

    def _copy_folder(self, source: str, destination: str) -> None:
        import shutil

        if not os.path.exists(destination):
            os.makedirs(destination, exist_ok=True)
        for root, dirs, files in os.walk(source):
            rel_path = os.path.relpath(root, source)
            dest_path = os.path.join(destination, rel_path)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path, exist_ok=True)
            for filename in files:
                shutil.copy2(os.path.join(root, filename), os.path.join(dest_path, filename))

    def _check_existing_translation(self, target_lang_folder: str) -> dict:
        result = {"exists": False, "files_count": 0, "entries_count": 0}
        if not os.path.exists(target_lang_folder):
            return result
        result["exists"] = True
        import lxml.etree as etree

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

    def _translate_defs_folder(self, defs_folder: str, mod_path: str, mod_output: str) -> int:
        """
        Обрабатывает папку Defs с использованием НОВЫХ функций:
        - Проверка существующих переводов
        - Обнаружение устаревших тегов
        - Универсальная проверка папок (Ability/ vs AbilityDef/)
        """
        import lxml.etree as etree

        from collectors.collectors import (
            collect_defs_full,
            collect_english_source,
            collect_keyed_entities,
        )
        from translation.per_def import generate_or_update_per_def_files_v2

        # 1. Определяем путь DefInjected
        def_injected_path, target_lang_base, created = resolve_def_injected_path(
            mod_path=mod_path,
            target_lang=self.target_lang,
            mod_output=mod_output,
            mode=self.mode,
            defs_folder=defs_folder,
            create_if_missing=True,
        )

        if created:
            self.logger.info(f"✓ Создана Languages для DefInjected: {target_lang_base}")

        # 2. Собираем Defs с разрешением наследования и обработкой патчей
        self.logger.info(f"  Сбор Defs из: {defs_folder}")
        defs_index, defs_rel, defs_meta = collect_defs_full(
            defs_dir=defs_folder,
            resolve_parents=True,  # Разрешаем ParentName/Name
            process_patches_flag=True,  # Обрабатываем патчи
            logger=self.logger,
        )

        if not defs_index:
            self.logger.info(f"  Defs не найдены в: {defs_folder}")
            return 0

        self.logger.info(f"  Найдено {len(defs_index)} Defs для обработки")

        # 2.5. Собираем source_map и keyed_map из English папки
        # Находим папку English (поднимаясь на уровень от Defs или ищем рядом)
        english_dir = os.path.join(os.path.dirname(defs_folder), "English")
        if not os.path.exists(english_dir):
            # Пробуем найти English на том же уровне
            parent_dir = os.path.dirname(defs_folder)
            for item in os.listdir(parent_dir):
                if item.lower() == "english":
                    english_dir = os.path.join(parent_dir, item)
                    break

        source_map = {}
        keyed_map = {}

        if os.path.exists(english_dir):
            self.logger.info(f"  Сбор source данных из English: {english_dir}")
            source_map = collect_english_source(english_dir, logger=self.logger)
            self.logger.info(f"  Найдено {len(source_map)} source записей")

            self.logger.info("  Сбор keyed данных из English/Keyed")
            keyed_map = collect_keyed_entities(english_dir, logger=self.logger)
            self.logger.info(f"  Найдено {len(keyed_map)} keyed записей")
        else:
            self.logger.debug("  English папка не найдена, source_map и keyed_map будут пустыми")

        # 3. Собираем существующие переводы
        # ✅ УЛУЧШЕНИЕ: Также извлекаем EN: комментарии с оригиналом
        existing_map = {}
        existing_index = {}
        existing_origin = {}  # {tagname: original_text из EN: комментария}

        if os.path.exists(def_injected_path):
            for root_dir, _, files in os.walk(def_injected_path):
                for fn in files:
                    if fn.endswith(".xml"):
                        path = os.path.join(root_dir, fn)
                        try:
                            # Читаем файл как текст для извлечения комментариев
                            with open(path, encoding="utf-8") as f:
                                content = f.read()

                            # Парсим XML для тегов
                            root = safe_parse_xml(path)
                            if root is None:
                                continue

                            # Ищем EN: комментарии в тексте
                            import re

                            en_comments = {}
                            for match in re.finditer(r"<!--\s*EN:\s*(.*?)\s*-->", content):
                                # Находим ближайший тег после комментария
                                after_comment = content[match.end() :]
                                tag_match = re.match(r"\s*<([^>/]+)>", after_comment)
                                if tag_match:
                                    tag_name = tag_match.group(1)
                                    en_comments[tag_name] = match.group(1).strip()

                            for child in root:
                                if child.tag and child.text and child.text.strip():
                                    tag = child.tag

                                    # Пропускаем _OBSOLETE_ теги для existing_map
                                    clean_tag = tag
                                    if tag.startswith("_OBSOLETE_"):
                                        clean_tag = tag[len("_OBSOLETE_") :]

                                    value = child.text.strip()
                                    existing_map[clean_tag] = value
                                    existing_index[clean_tag] = path

                                    # Сохраняем оригинал из EN: комментария
                                    if clean_tag in en_comments:
                                        existing_origin[clean_tag] = en_comments[clean_tag]
                        except Exception as e:
                            self.logger.debug(f"Ошибка чтения {path}: {e}")

        self.logger.info(f"  Найдено {len(existing_map)} существующих переводов")

        # 4. Запускаем генерацию с проверкой устаревших тегов и fuzzy поиском
        created_files = generate_or_update_per_def_files_v2(
            defs_index=defs_index,
            defs_rel=defs_rel,
            defs_source_abs={},
            defs_file_map={},
            defs_meta=defs_meta,
            keyed_map=keyed_map,  # ✅ Теперь передаём keyed_map
            source_map=source_map,  # ✅ Теперь передаём source_map
            existing_map=existing_map,
            existing_index=existing_index,
            existing_origin=existing_origin,  # ✅ Передаём оригиналы из EN: комментариев
            target_lang_dir=target_lang_base,
            logger=self.logger,
            aggressive=False,
            use_api=self._auto_translator.enabled if self._auto_translator else False,
            lang_to=self.target_lang,
            fuzzy=self.fuzzy,  # ✅ Используем настройку из GUI
            cleanup_orphans=True,  # ✅ Включаем очистку осиротевших файлов
            check_obsolete=True,  # ✅ ВКЛЮЧЕНА проверка устаревших тегов
        )

        self.logger.info(f"  Создано/обновлено файлов: {len(created_files)}")
        return len(created_files)

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

        import lxml.etree as etree

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
