#!/usr/bin/env python
"""
Скрипт валидации файлов переводов
Проверяет:
- Валидность JSON
- Наличие всех ключей относительно reference файла
- Корректность кодировки UTF-8
"""

import json
import sys
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"
REFERENCE_FILE = LOCALES_DIR / "en.json"


def validate_json(file_path):
    """Проверить валидность JSON файла"""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return True, data, None
    except json.JSONDecodeError as e:
        return False, None, f"❌ JSON ошибка: {e}"
    except Exception as e:
        return False, None, f"❌ Ошибка чтения: {e}"


def validate_keys(reference, target, file_name):
    """Сравнить ключи с reference файлом"""
    ref_keys = set(reference.keys())
    target_keys = set(target.keys())

    missing = ref_keys - target_keys
    extra = target_keys - ref_keys

    issues = []
    if missing:
        issues.append(f"  ⚠️ Отсутствуют {len(missing)} ключей")
    if extra:
        issues.append(f"  ℹ️ Лишние {len(extra)} ключей")

    if issues:
        print(f"\n{file_name}:")
        for issue in issues:
            print(issue)
        return False

    return True


def main():
    print("🔍 Валидация файлов переводов\n")

    if not LOCALES_DIR.exists():
        print(f"❌ Папка {LOCALES_DIR} не найдена!")
        return 1

    # Загружаем reference
    if not REFERENCE_FILE.exists():
        print(f"❌ Reference файл {REFERENCE_FILE} не найден!")
        return 1

    success, ref_data, error = validate_json(REFERENCE_FILE)
    if not success:
        print(error)
        return 1

    # Извлекаем переводы из reference (формат {"en": {...}})
    ref_lang = list(ref_data.keys())[0]
    ref_translations = ref_data[ref_lang]
    print(f"📖 Reference: {REFERENCE_FILE.name} ({ref_lang})")
    print(f"   {len(ref_translations)} переводов\n")

    # Проверяем все файлы
    all_valid = True
    file_count = 0

    for lang_file in sorted(LOCALES_DIR.glob("*.json")):
        if lang_file.name == "README.md":
            continue

        file_count += 1
        print(f"📄 {lang_file.name}...", end=" ")

        # Валидация JSON
        success, data, error = validate_json(lang_file)
        if not success:
            print(error)
            all_valid = False
            continue

        print("✅ JSON валиден", end="")

        # Извлекаем переводы
        lang_code = list(data.keys())[0]
        translations = data[lang_code]

        print(f" ({lang_code}: {len(translations)} переводов)")

        # Проверка ключей
        if lang_file != REFERENCE_FILE:
            validate_keys(ref_translations, translations, lang_file.name)

    print(f"\n{'=' * 50}")
    print(f"Проверено файлов: {file_count}")

    if all_valid:
        print("✅ Все файлы валидны!")
        return 0
    else:
        print("❌ Найдены ошибки!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
