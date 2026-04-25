# utils/cyrillic_checker.py
"""
Утилита для проверки наличия кириллицы в Python файлах.
Используется для контроля качества кода.

Запуск:
    python -m utils.cyrillic_checker

Или:
    python utils/cyrillic_checker.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Паттерн для поиска кириллических символов
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")

# Директории для проверки
SEARCH_DIRS = [".", "gui", "workers", "config", "utils", "translation", "verification"]

# Исключенные файлы
EXCLUDE_FILES = {
    "language_constants.py",  # Содержит русские строки намеренно
    "gui_i18n.py",  # Содержит переводы
    "__init__.py",
}


def check_file_for_cyrillic(file_path: Path) -> list[tuple[int, str]]:
    """
    Проверить файл на наличие кириллицы.

    Args:
        file_path: Путь к файлу

    Returns:
        Список кортежей (номер_строки, содержимое_строки)
    """
    findings = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # Пропускаем комментарии и строки
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if CYRILLIC_PATTERN.search(stripped):
                    findings.append((line_num, stripped))
    except (OSError, UnicodeDecodeError):
        pass

    return findings


def scan_directory(root_dir: str = ".") -> dict[str, list[tuple[int, str]]]:
    """
    Сканировать директорию на наличие кириллицы.

    Args:
        root_dir: Корневая директория

    Returns:
        Словарь {путь_к_файлу: [(номер_строки, содержимое)]}
    """
    results = {}

    for search_dir in SEARCH_DIRS:
        full_dir = os.path.join(root_dir, search_dir)
        if not os.path.exists(full_dir):
            continue

        for dirpath, _, filenames in os.walk(full_dir):
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                if filename in EXCLUDE_FILES:
                    continue

                file_path = Path(dirpath) / filename
                findings = check_file_for_cyrillic(file_path)
                if findings:
                    results[str(file_path)] = findings

    return results


def print_report(results: dict[str, list[tuple[int, str]]]) -> None:
    """
    Вывести отчет о найденной кириллице.

    Args:
        results: Результаты сканирования
    """
    if not results:
        print("✅ Кириллица в коде не найдена!")
        return

    print(f"⚠️ Найдена кириллица в {len(results)} файлах:\n")

    total_lines = 0
    for file_path, lines in sorted(results.items()):
        print(f"📄 {file_path}")
        for line_num, content in lines:
            print(f"   Строка {line_num}: {content[:80]}...")
            total_lines += 1
        print()

    print(f"Итого: {total_lines} строк с кириллицей")
    print("\nРекомендуется заменить кириллицу в коде на i18n ключи!")


def main():
    """Точка входа."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results = scan_directory(root)
    print_report(results)

    # Возвращаем код ошибки если найдены проблемы
    sys.exit(1 if results else 0)


if __name__ == "__main__":
    main()
