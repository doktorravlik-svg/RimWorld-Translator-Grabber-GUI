# utils/mod_classifier.py
"""
Единый модуль классификации модов RimWorld.

Используется для определения является ли мод переводом.
Это единственный источник правды для всей системы.
"""

import os
from typing import Any

# Ключевые слова для определения переводов
TRANSLATION_KEYWORDS = [
    "translation",
    "localization",
    "localiser",
    "translator",
    "russian",
    "русификатор",
    "перевод",
    "локализация",
    "ru-ru",
    "utf",
]


def is_translation_mod(about_data: dict[str, Any]) -> bool:
    """
    Определяет является ли мод переводом.

    Проверяет в порядке приороритета:
    1. Явные признаки (target_mod_id, target_content_creator)
    2. Ключевые слова в ID/name (НО: только если нет Defs)
    3. Структурные признаки (есть Languages, нет Defs)

    Args:
        about_data: Словарь с данными из About.xml

    Returns:
        True если мод является переводом
    """
    # 1. Явные признаки (наивысший приоритет)
    if about_data.get("target_mod_id"):
        return True

    if about_data.get("target_content_creator"):
        return True

    # 2. Проверяем структурные признаки ПЕРЕД ключевыми словами
    # Это предотвращает ложные срабатывания на полноценных модах
    mod_path = about_data.get("mod_path", "")
    has_languages = False
    has_defs = False

    if mod_path:
        has_languages = _has_language_folder(mod_path)
        has_defs = _has_defs_folder(mod_path)

    # Если есть Languages и НЕТ Defs - это перевод
    if has_languages and not has_defs:
        return True

    # 3. Ключевые слова в ID/name - проверяем ТОЛЬКО если нет Defs
    # Это предотвращает ложные срабатывания на полноценных модах
    if not has_defs:
        mod_id = (about_data.get("mod_id") or "").lower()
        mod_name = (about_data.get("name") or "").lower()

        if any(kw in mod_id for kw in TRANSLATION_KEYWORDS):
            return True

        if any(kw in mod_name for kw in TRANSLATION_KEYWORDS):
            return True

    # 4. LoadAfter проверка (если есть load_after) - ТОЛЬКО если нет Defs
    if not has_defs:
        load_after = about_data.get("load_after", [])
        if load_after:
            # Если мод загружается после другого мода и не является библиотекой
            if not _is_base_dependency(about_data.get("mod_id", "")):
                # Проверяем есть ли Languages
                if mod_path and has_languages:
                    return True

    return False


def _has_language_folder(mod_path: str) -> bool:
    """
    Проверяет наличие папки Languages.
    Поддерживает Common/Languages и LoadFolders.xml.
    """
    try:
        from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders

        langs = find_all_languages_folders_with_loadfolders(mod_path)
        if langs:
            # Проверяем что внутри есть хотя бы один язык
            for lang_folder in langs:
                if os.path.exists(lang_folder) and os.listdir(lang_folder):
                    return True
    except ImportError:
        # Fallback: простая проверка
        langs_path = os.path.join(mod_path, "Languages")
        if os.path.exists(langs_path):
            return True

    return False


def _has_defs_folder(mod_path: str) -> bool:
    """
    Проверяет наличие папки Defs.
    Поддерживает Common/Defs и LoadFolders.xml.
    """
    try:
        from utils.loadfolders_parser import find_all_defs_folders_with_loadfolders

        defs = find_all_defs_folders_with_loadfolders(mod_path)
        return len(defs) > 0
    except ImportError:
        # Fallback: простая проверка
        defs_path = os.path.join(mod_path, "Defs")
        return os.path.exists(defs_path)


def _is_base_dependency(package_id: str) -> bool:
    """Проверяет является ли мод базовой зависимостью (библиотекой)"""
    base_libs = [
        "unlimitedhugs.hugslib",
        "0harmony",
        "imranfish.xmlextensions",
        "brrailz.lib",
        "pardeike.harmony",
    ]

    package_id_lower = package_id.lower()
    return any(lib in package_id_lower for lib in base_libs)
