# translation_merger.py
"""
Модуль для объединения и анализа переводов из нескольких модов.

Сканирует моды, собирает все переводы в глобальную карту,
выявляет дубликаты и предоставляет статистику.
"""

import os
from typing import Any

from collectors.collectors import collect_existing_translations
from core.core_models import TranslationEntry
from scanner.mod_scanner import parse_about_xml as parse_detailed_about
from utils.fs_utils import safe_walk


class TranslationMerger:
    """
    Анализатор и объединитель переводов из нескольких модов.

    Сканирует указанные моды, собирает все переводы в единую карту
    и предоставляет инструменты для анализа дубликатов.

    Args:
        mods_path: Путь к папке с модами
        target_lang: Целевой язык для поиска переводов
        logger: Логгер для записи сообщений
    """

    def __init__(
        self,
        mods_path: str,
        target_lang: str = "Russian",
        logger: Any | None = None,
    ):
        """
        Инициализирует анализатор переводов.

        Args:
            mods_path: Путь к папке с модами
            target_lang: Целевой язык для поиска переводов
            logger: Логгер для записи сообщений
        """
        self.mods_path = mods_path
        self.target_lang = target_lang
        self.logger = logger
        self.global_map: dict[str, list[TranslationEntry]] = {}  # key -> list[TranslationEntry]

    def scan_mods(self, target_mods: list[str] | None = None) -> None:
        """
        Сканирует папку модов и собирает все переводы.

        Args:
            target_mods: Список папок модов для сканирования (если None - сканирует всё)
        """
        self.global_map = {}

        # Получаем список папок модов
        mod_dirs = target_mods if target_mods else os.listdir(self.mods_path)

        for mod_dirname in mod_dirs:
            full_mod_path = os.path.join(self.mods_path, mod_dirname)
            if not os.path.isdir(full_mod_path):
                continue

            # 1. Собираем метаданные мода
            about_path = os.path.join(full_mod_path, "About", "About.xml")
            mod_meta = parse_detailed_about(about_path)

            # 2. Ищем папку с нужным языком
            # Проверяем стандартный путь и пути с версиями (1.5/Languages/...)
            lang_paths = self._find_language_folders(full_mod_path)

            for lang_dir in lang_paths:
                # 3. Собираем все переводы из этой папки
                # Используем нашу функцию collect_existing_translations
                translations, _ = collect_existing_translations(lang_dir, self.logger)

                for key, value in translations.items():
                    # Создаем запись с метаданными
                    entry = TranslationEntry(
                        key=key,
                        value=value,
                        file_path=lang_dir,
                        mod_name=mod_meta["name"],
                        author=mod_meta["author"],
                        mod_version=mod_meta["version"],
                        dependencies=mod_meta["dependencies"],
                    )

                    if key not in self.global_map:
                        self.global_map[key] = []
                    self.global_map[key].append(entry)

        if self.logger:
            self.logger.info(
                f"Сканирование завершено. Собрано уникальных ключей: {len(self.global_map)}"
            )

    def _find_language_folders(self, mod_path: str) -> list[str]:
        """
        Вспомогательный метод для поиска всех папок с целевым языком в моде.

        Args:
            mod_path: Путь к папке мода

        Returns:
            Список путей к папкам с целевым языком
        """
        found = []
        # Ищем во всех подпапках (для поддержки 1.4, 1.5 и т.д.)
        for root, dirs, _ in safe_walk(mod_path, max_depth=3):
            if self.target_lang in dirs:
                found.append(os.path.join(root, self.target_lang))
        return found

    def run_full_analysis(self, target_mods: list[str] | None = None) -> dict[str, Any]:
        """
        Запускает полный анализ переводов и возвращает результаты.

        Args:
            target_mods: Список папок модов для анализа (если None - сканирует всё)

        Returns:
            Словарь с результатами анализа, включающий:
                - total_keys: Общее количество ключей
                - unique_keys: Количество уникальных ключей
                - duplicate_keys: Количество ключей с дубликатами
                - mods_analyzed: Количество проанализированных модов
                - mod_stats: Статистика по каждому моду
        """
        # Сканируем моды
        self.scan_mods(target_mods)

        # Анализируем результаты
        total_keys = len(self.global_map)
        duplicate_keys = sum(1 for entries in self.global_map.values() if len(entries) > 1)
        unique_keys = total_keys - duplicate_keys

        # Собираем статистику по модам
        mod_stats = {}
        for key, entries in self.global_map.items():
            for entry in entries:
                mod_name = entry.mod_name
                if mod_name not in mod_stats:
                    mod_stats[mod_name] = {"keys": 0, "files": set()}
                mod_stats[mod_name]["keys"] += 1
                mod_stats[mod_name]["files"].add(entry.file_path)

        # Преобразуем set в count для сериализации
        for mod_name in mod_stats:
            mod_stats[mod_name]["files"] = len(mod_stats[mod_name]["files"])

        results = {
            "total_keys": total_keys,
            "unique_keys": unique_keys,
            "duplicate_keys": duplicate_keys,
            "mods_analyzed": len(mod_stats),
            "mod_stats": mod_stats,
        }

        if self.logger:
            self.logger.info("Анализ завершён:")
            self.logger.info(f"  Всего ключей: {total_keys}")
            self.logger.info(f"  Уникальных: {unique_keys}")
            self.logger.info(f"  С дубликатами: {duplicate_keys}")
            self.logger.info(f"  Модов проанализировано: {len(mod_stats)}")

        return results
