# translation/importer.py
"""
Модуль для импорта переводов из существующих модов RimWorld в базу данных.
Сканирует папки Languages, парсит Keyed XML файлы и сохраняет переводы в БД.
"""

import logging
import os
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any

from translation_db import get_translation_db

logger = logging.getLogger(__name__)


def _load_filters_config() -> dict:
    """Загружает конфигурацию фильтров."""
    import json

    config_path = os.path.join(os.path.dirname(__file__), "..", "filters_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback значения
    return {
        "whitelist_tags": [],  # Пустой = все разрешены
        "blacklist_tags": {"defName", "workerClass", "texture", "sound", "thingClass"},
        "blacklist_patterns": ["internal_", "debug_", "tmp_", "test_"],
        "min_text_length": 2,
    }


class TranslationImporter:
    """
    Импорт переводов из модов RimWorld в базу данных переводов.

    Сканирует структуру:
    ModName/Languages/{Language}/Keyed/*.xml
    и извлекает все пары ключ-значение для сохранения в БД.
    """

    def __init__(self, db: Any | None = None):
        """
        Инициализирует импортер переводов.

        Args:
            db: Экземпляр TranslationDB (если None, используется get_translation_db())
        """
        self.db = db or get_translation_db()
        self.stats = {
            "mods_scanned": 0,
            "files_processed": 0,
            "translations_imported": 0,
            "errors": 0,
        }

    def import_from_mods_folder(
        self,
        mods_folder: str,
        target_lang: str = "Russian",
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        """
        Сканирует папку модов и импортирует все переводы указанного языка.

        Args:
            mods_folder: Путь к папке с модами
            target_lang: Целевой язык для импорта (Russian, English, etc.)
            progress_callback: Функция callback для отображения прогресса (current, total, message)

        Returns:
            Словарь со статистикой импорта
        """
        if not self.db:
            logger.error("База данных переводов не доступна")
            return {"error": "База данных не доступна"}

        if not os.path.exists(mods_folder):
            logger.error(f"Папка модов не найдена: {mods_folder}")
            return {"error": "Папка модов не найдена"}

        # Сброс статистики
        self.stats = {
            "mods_scanned": 0,
            "files_processed": 0,
            "translations_imported": 0,
            "errors": 0,
        }

        # Собираем список модов
        mods = self._scan_mods(mods_folder)
        total_mods = len(mods)

        if progress_callback:
            progress_callback(0, total_mods, "Начало сканирования...")

        logger.info(f"Найдено {total_mods} модов для сканирования")

        # Обрабатываем каждый мод
        for idx, mod_path in enumerate(mods):
            mod_name = os.path.basename(mod_path)

            if progress_callback:
                progress_callback(idx, total_mods, f"Сканирование: {mod_name}")

            try:
                self._import_mod_translations(mod_path, target_lang)
                self.stats["mods_scanned"] += 1
            except Exception as e:
                logger.error(f"Ошибка импорта мода {mod_name}: {e}")
                self.stats["errors"] += 1

        if progress_callback:
            progress_callback(total_mods, total_mods, "Импорт завершён!")

        logger.info(
            f"Импорт завершён: {self.stats['mods_scanned']} модов, "
            f"{self.stats['files_processed']} файлов, "
            f"{self.stats['translations_imported']} переводов"
        )

        return self.stats.copy()

    def _scan_mods(self, mods_folder: str) -> list[str]:
        """
        Сканирует папку модов и возвращает список путей к модам.

        Args:
            mods_folder: Путь к папке с модами

        Returns:
            Список путей к валидным модам
        """
        mods = []

        # Проверяем, не является ли сама папка модом
        if self._is_valid_mod(mods_folder):
            mods.append(mods_folder)
            return mods

        # Сканируем подпапки
        try:
            for item in os.listdir(mods_folder):
                item_path = os.path.join(mods_folder, item)
                if os.path.isdir(item_path) and self._is_valid_mod(item_path):
                    mods.append(item_path)
        except OSError as e:
            logger.error(f"Ошибка сканирования папки: {e}")

        return mods

    def _is_valid_mod(self, mod_path: str) -> bool:
        """
        Проверяет, является ли папка валидным модом.

        Args:
            mod_path: Путь к папке мода

        Returns:
            True если мод валидный, False иначе
        """
        about_path = os.path.join(mod_path, "About", "About.xml")
        return os.path.exists(about_path)

    def _import_mod_translations(self, mod_path: str, target_lang: str) -> None:
        """
        Импортирует переводы из одного мода.

        Args:
            mod_path: Путь к папке мода
            target_lang: Целевой язык для импорта
        """
        mod_name = os.path.basename(mod_path)
        languages_path = os.path.join(mod_path, "Languages")

        if not os.path.exists(languages_path):
            return

        # ✅ ИСПРАВЛЕНО: Сканируем ВСЕ языковые папки, не только target_lang
        for lang_name in os.listdir(languages_path):
            lang_folder_path = os.path.join(languages_path, lang_name)
            if not os.path.isdir(lang_folder_path):
                continue

            # Определяем source_lang из структуры папок
            # Если это English - это оригинал, если другой - перевод
            source_lang = "English" if lang_name == "English" else lang_name

            # Сканируем Keyed папки
            keyed_path = os.path.join(lang_folder_path, "Keyed")
            if not os.path.exists(keyed_path):
                continue

            # Обрабатываем все XML файлы в Keyed
            for filename in os.listdir(keyed_path):
                if filename.endswith(".xml"):
                    file_path = os.path.join(keyed_path, filename)
                    try:
                        self._import_xml_file(file_path, mod_name, source_lang, target_lang)
                        self.stats["files_processed"] += 1
                    except Exception as e:
                        logger.error(f"Ошибка импорта файла {filename}: {e}")
                        self.stats["errors"] += 1

    def _import_xml_file(
        self, file_path: str, mod_name: str, source_lang: str, target_lang: str
    ) -> None:
        """
        Импортирует переводы из одного XML файла.

        Args:
            file_path: Путь к XML файлу
            mod_name: Название мода
            source_lang: Язык оригинала (из пути Languages/{Language}/)
            target_lang: Целевой язык
        """
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML {file_path}: {e}")
            return

        # ✅ ИСПРАВЛЕНО: Загружаем фильтры и применяем их
        filters = _load_filters_config()
        whitelist = filters.get("whitelist_tags", [])
        blacklist = filters.get("blacklist_tags", set())
        blacklist_patterns = filters.get("blacklist_patterns", [])
        min_length = filters.get("min_text_length", 2)

        # Извлекаем все элементы с текстом
        for element in root.iter():
            if element.text and element.text.strip():
                key = element.tag
                translation = element.text.strip()

                # ✅ ИСПРАВЛЕНО: Применяем blacklist_tags
                if key in blacklist:
                    continue

                # ✅ ИСПРАВЛЕНО: Применяем blacklist_patterns
                key_lower = key.lower()
                if any(pat in key_lower for pat in blacklist_patterns):
                    continue

                # ✅ ИСПРАВЛЕНО: Применяем whitelist_tags (если есть)
                if whitelist and key not in whitelist:
                    continue

                # Игнорируем пустые или слишком короткие значения
                if len(translation) < min_length:
                    continue

                # Сохраняем в базу данных
                if self.db:
                    try:
                        self.db.add_translation(
                            key=key,
                            original="",  # Оригинала у нас нет, только перевод
                            translated=translation,
                            file_name=os.path.basename(file_path),
                            mod_name=mod_name,
                            source_lang=source_lang,  # ✅ ИСПРАВЛЕНО: Реальный язык из пути
                            target_lang=target_lang,
                        )
                        self.stats["translations_imported"] += 1
                    except Exception as e:
                        logger.debug(f"Не удалось сохранить перевод {key}: {e}")

    def import_from_xml_files(
        self,
        xml_files: list[str],
        mod_name: str = "",
        source_lang: str = "English",
        target_lang: str = "Russian",
    ) -> dict[str, Any]:
        """
        Импортирует переводы из списка XML файлов.

        Args:
            xml_files: Список путей к XML файлам
            mod_name: Название мода (для метаданных)
            source_lang: Язык оригинала
            target_lang: Целевой язык

        Returns:
            Словарь со статистикой импорта
        """
        if not self.db:
            return {"error": "База данных не доступна"}

        self.stats = {
            "mods_scanned": 1,
            "files_processed": 0,
            "translations_imported": 0,
            "errors": 0,
        }

        for file_path in xml_files:
            if os.path.exists(file_path):
                try:
                    self._import_xml_file(file_path, mod_name, source_lang, target_lang)
                    self.stats["files_processed"] += 1
                except Exception as e:
                    logger.error(f"Ошибка импорта {file_path}: {e}")
                    self.stats["errors"] += 1

        return self.stats.copy()

    def get_database_stats(self) -> dict[str, Any]:
        """
        Возвращает статистику базы данных.

        Returns:
            Словарь со статистикой базы данных
        """
        if not self.db:
            return {"error": "База данных не доступна"}

        return self.db.get_stats()


def get_importer(db: Any | None = None) -> "TranslationImporter":
    """
    Фабричная функция для получения импортера.

    Args:
        db: Экземпляр TranslationDB (опционально)

    Returns:
        Экземпляр TranslationImporter
    """
    return TranslationImporter(db)
