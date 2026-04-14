# translation_utils.py
"""
Утилиты для работы с переводами.

Предоставляет функции для сравнения, импорта и разрешения конфликтов
переводов из различных источников (CSV, JSON).
"""

import csv
import json
from typing import Any

from core.core_models import AutoResolveSettings
from translation.translation_merger import TranslationMerger
from utils.cli_helpers import prompt_yes_no


def compare_translations(
    source_map: dict[str, str],
    existing_map: dict[str, str],
    logger: Any,
) -> dict[str, Any]:
    """
    Сравнивает исходные и существующие переводы.

    Args:
        source_map: Карта исходных переводов
        existing_map: Карта существующих переводов
        logger: Логгер для записи сообщений

    Returns:
        Словарь со статистикой сравнения, включающий:
            - total_source: Общее количество исходных ключей
            - total_existing: Общее количество существующих ключей
            - translated: Количество переведённых ключей
            - missing: Количество отсутствующих ключей
            - extra: Количество дополнительных ключей
            - percent: Процент перевода
            - missing_keys: Множество отсутствующих ключей
            - extra_keys: Множество дополнительных ключей
    """
    source_keys = set(source_map.keys())
    existing_keys = set(existing_map.keys())
    translated = source_keys & existing_keys
    missing = source_keys - existing_keys
    extra = existing_keys - source_keys
    total_source = len(source_keys)

    return {
        "total_source": total_source,
        "total_existing": len(existing_keys),
        "translated": len(translated),
        "missing": len(missing),
        "extra": len(extra),
        "percent": (len(translated) / total_source * 100) if total_source > 0 else 0,
        "missing_keys": missing,
        "extra_keys": extra,
    }


# find_duplicates() удалён - используйте duplicate_merger.find_duplicates()


def import_translations_from_csv(csv_path: str, logger: Any) -> dict[str, str]:
    """
    Импортирует переводы из CSV файла.

    Args:
        csv_path: Путь к CSV файлу
        logger: Логгер для записи сообщений

    Returns:
        Словарь импортированных переводов {key: value}
    """
    translations = {}
    try:
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip():
                    translations[row[0].strip()] = row[1].strip()
        logger.info(f"Импортировано {len(translations)} переводов из CSV")
    except Exception as e:
        logger.error(f"Ошибка импорта CSV: {e}")
    return translations


def import_translations_from_json(json_path: str, logger: Any) -> dict[str, str]:
    """
    Импортирует переводы из JSON файла.

    Args:
        json_path: Путь к JSON файлу
        logger: Логгер для записи сообщений

    Returns:
        Словарь импортированных переводов {key: value}
    """
    translations = {}
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                translations = data
        logger.info(f"Импортировано {len(translations)} переводов из JSON")
    except Exception as e:
        logger.error(f"Ошибка импорта JSON: {e}")
    return translations


def resolve_conflicts(
    duplicates: dict[str, dict[str, list]],
    existing_map: dict[str, str],
    logger: Any,
    interactive: bool = True,
) -> tuple[dict[str, str], int]:
    """
    Разрешает конфликты дубликатов переводов в интерактивном режиме.

    Args:
        duplicates: Словарь дубликатов {base_value: {value: [keys]}}
        existing_map: Карта существующих переводов
        logger: Логгер для записи сообщений
        interactive: Режим интерактивного выбора

    Returns:
        Кортеж (разрешённая карта переводов, количество разрешённых конфликтов)
    """
    resolved = existing_map.copy()
    if not duplicates:
        return resolved, 0

    print(f"\n=== Найдены конфликты дубликатов: {len(duplicates)} ===")
    resolved_count = 0

    for base_value, key_groups in duplicates.items():
        print(f"\nЗначение: '{base_value[:50]}...'")
        for value, keys in key_groups.items():
            print(f"  Ключи: {', '.join(keys)}\n  Значение: '{value}'")

        print(
            "Варианты:\n  1. Оставить первый\n  2. Оставить последний\n  3. Оставить все\n  4. Пропустить"
        )
        choice = input("Выбери (1-4): ").strip() if interactive else "4"

        if choice == "1":
            first_key = list(key_groups.keys())[0]
            for key in key_groups:
                if key != first_key:
                    del resolved[key]
            resolved_count += 1
        elif choice == "2":
            last_key = list(key_groups.keys())[-1]
            for key in key_groups:
                if key != last_key:
                    del resolved[key]
            resolved_count += 1
    return resolved, resolved_count


def analyze_conflicts_advanced(
    mods_base_path: str,
    mods_to_analyze: list,
    logger: Any,
    interactive: bool = True,
) -> TranslationMerger:
    """
    Выполняет расширенный анализ конфликтов переводов.

    Args:
        mods_base_path: Базовый путь к папке модов
        mods_to_analyze: Список модов для анализа
        logger: Логгер для записи сообщений
        interactive: Режим интерактивного выбора

    Returns:
        Экземпляр TranslationMerger с результатами анализа
    """
    print("\n=== Расширенный анализ конфликтов ===")
    settings = AutoResolveSettings(
        prefer_longer=True,
        prefer_newer_version=True,
        prefer_higher_priority=True,
        create_synonyms=prompt_yes_no(
            "Авто-создавать синонимы для дубликатов?", default="y", interactive=interactive
        ),
    )
    merger = TranslationMerger(mods_base_path, logger=logger)
    results = merger.run_full_analysis(mods_to_analyze)

    print("\nРезультаты анализа:")
    for k, v in results.items():
        print(f"  {k}: {v}")

    if prompt_yes_no(
        "Показать отчёт (translation_report.md)?", default="y", interactive=interactive
    ):
        try:
            with open("translation_report.md", encoding="utf-8") as f:
                print(f.read())
        except OSError:
            print("Отчёт не найден")
    return merger
