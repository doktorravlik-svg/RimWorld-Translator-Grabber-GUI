"""
Locale Utils - утилиты для работы с файлами локализации.

Устраняет дублирование кода в 7 migration scripts:
- add_all_gui_translations.py
- add_deps_tabs_translations.py
- add_editor_translations.py
- add_final_ui_translations.py
- add_last_ui_strings.py
- add_new_translation_keys.py
- fix_gui_translations.py

Пример использования:
    from scripts.locale_utils import add_translation_keys, LOCALES_DIR

    new_keys = {"key1": {"ru": "Перевод", "en": "Translation"}, ...}
    add_translation_keys(new_keys, "Добавлены новые UI строки")
"""

import json
from pathlib import Path

# Определяем путь к папке locales
LOCALES_DIR = Path(__file__).parent.parent / "locales"

SUPPORTED_LANGUAGES = ["ru", "en", "ua", "ja"]


def load_locale_file(lang: str) -> dict:
    """
    Загружает файл локализации.

    Args:
        lang: Код языка (ru, en, ua, ja)

    Returns:
        Словарь с переводами
    """
    file_path = LOCALES_DIR / f"{lang}.json"
    
    if not file_path.exists():
        print(f"  ⚠️ Файл не найден: {file_path}")
        return {}
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data


def save_locale_file(lang: str, data: dict) -> None:
    """
    Сохраняет файл локализации.

    Args:
        lang: Код языка
        data: Словарь с переводами
    """
    file_path = LOCALES_DIR / f"{lang}.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_translation_keys(
    new_keys: dict,
    description: str,
    languages: list[str] = None,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Добавляет новые ключи во все файлы локализации.

    Args:
        new_keys: Словарь {key: {lang: translation, ...}}
        description: Описание изменений (для вывода)
        languages: Список языков (по умолчанию все поддерживаемые)
        dry_run: Только показать что будет добавлено, не сохранять

    Returns:
        Словарь {lang: количество добавленных ключей}
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    stats = {lang: 0 for lang in languages}
    
    print(f"\n{'='*60}")
    print(f"📝 {description}")
    print(f"{'='*60}")
    
    for lang in languages:
        data = load_locale_file(lang)
        if not data:
            continue
        
        # Получаем первый ключ (код языка внутри JSON)
        lang_code = list(data.keys())[0]
        translations = data[lang_code]
        
        added = 0
        for key, lang_data in new_keys.items():
            if key not in translations:
                if not dry_run:
                    translations[key] = lang_data.get(lang, "")
                added += 1
        
        stats[lang] = added
        
        if not dry_run and added > 0:
            data[lang_code] = translations
            save_locale_file(lang, data)
        
        print(f"  {lang}: +{added} ключей")
    
    total = sum(stats.values())
    print(f"\n  ИТОГО: +{total} ключей")
    
    return stats


def remove_translation_keys(
    keys_to_remove: list[str],
    description: str,
    languages: list[str] = None,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Удаляет ключи из файлов локализации.

    Args:
        keys_to_remove: Список ключей для удаления
        description: Описание изменений
        languages: Список языков
        dry_run: Только показать что будет удалено

    Returns:
        Словарь {lang: количество удалённых ключей}
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    stats = {lang: 0 for lang in languages}
    
    print(f"\n{'='*60}")
    print(f"🗑️ {description}")
    print(f"{'='*60}")
    
    for lang in languages:
        data = load_locale_file(lang)
        if not data:
            continue
        
        lang_code = list(data.keys())[0]
        translations = data[lang_code]
        
        removed = 0
        for key in keys_to_remove:
            if key in translations:
                if not dry_run:
                    del translations[key]
                removed += 1
        
        stats[lang] = removed
        
        if not dry_run and removed > 0:
            data[lang_code] = translations
            save_locale_file(lang, data)
        
        print(f"  {lang}: -{removed} ключей")
    
    total = sum(stats.values())
    print(f"\n  ИТОГО: -{total} ключей")
    
    return stats


def update_translation_values(
    updates: dict,
    description: str,
    languages: list[str] = None,
    dry_run: bool = False
) -> dict[str, int]:
    """
    Обновляет значения существующих ключей.

    Args:
        updates: Словарь {key: {lang: new_value, ...}}
        description: Описание изменений
        languages: Список языков
        dry_run: Только показать что будет изменено

    Returns:
        Словарь {lang: количество обновлённых ключей}
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    stats = {lang: 0 for lang in languages}
    
    print(f"\n{'='*60}")
    print(f"✏️ {description}")
    print(f"{'='*60}")
    
    for lang in languages:
        data = load_locale_file(lang)
        if not data:
            continue
        
        lang_code = list(data.keys())[0]
        translations = data[lang_code]
        
        updated = 0
        for key, lang_data in updates.items():
            if key in translations:
                new_value = lang_data.get(lang)
                if new_value is not None and translations[key] != new_value:
                    if not dry_run:
                        translations[key] = new_value
                    updated += 1
        
        stats[lang] = updated
        
        if not dry_run and updated > 0:
            data[lang_code] = translations
            save_locale_file(lang, data)
        
        print(f"  {lang}: ~{updated} ключей")
    
    total = sum(stats.values())
    print(f"\n  ИТОГО: ~{total} ключей")
    
    return stats


def get_missing_keys(
    reference_lang: str = "ru",
    languages: list[str] = None
) -> dict[str, list[str]]:
    """
    Находит ключи, которые отсутствуют в некоторых языках.

    Args:
        reference_lang: Язык-эталон (обычно русский)
        languages: Список языков для проверки

    Returns:
        Словарь {lang: [отсутствующие ключи]}
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    # Загружаем эталонный язык
    ref_data = load_locale_file(reference_lang)
    if not ref_data:
        return {}
    
    ref_code = list(ref_data.keys())[0]
    ref_keys = set(ref_data[ref_code].keys())
    
    missing = {}
    
    for lang in languages:
        if lang == reference_lang:
            continue
        
        data = load_locale_file(lang)
        if not data:
            missing[lang] = list(ref_keys)
            continue
        
        lang_code = list(data.keys())[0]
        lang_keys = set(data[lang_code].keys())
        
        missing_keys = ref_keys - lang_keys
        if missing_keys:
            missing[lang] = sorted(missing_keys)
    
    return missing


def print_locale_stats(languages: list[str] = None) -> None:
    """
    Печатает статистику по всем файлам локализации.

    Args:
        languages: Список языков
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    print(f"\n{'='*60}")
    print("📊 Статистика локализации")
    print(f"{'='*60}")
    
    for lang in languages:
        data = load_locale_file(lang)
        if not data:
            print(f"  {lang}: файл не найден")
            continue
        
        lang_code = list(data.keys())[0]
        count = len(data[lang_code])
        print(f"  {lang}: {count} ключей")
