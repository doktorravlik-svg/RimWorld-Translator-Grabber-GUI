# gui/help/help_loader.py
"""Загрузчик справки и подсказок из JSON файлов."""

import json
from pathlib import Path

# Путь к директории help
_HELP_DIR = Path(__file__).parent


def _get_help_file(language="ru"):
    """Получить путь к файлу справки для языка"""
    # Список языков для fallback (от специфичного к общему)
    for lang in [language, "ua", "en", "ru"]:
        filename = f"editor_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath

    # Если ничего не найдено
    return _HELP_DIR / "editor_help_ru.json"


def load_editor_help(language="ru"):
    """Загрузить справку редактора из JSON"""
    filepath = _get_help_file(language)

    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки: {e}")
        return {}


def format_editor_help_text(help_data):
    """Форматировать текст справки для отображения"""
    title = help_data.get("title", "📖 Справка")
    sections = help_data.get("sections", {})

    parts = [title, ""]

    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])

        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")  # Пустая строка между секциями

    return "\n".join(parts)


def _get_tooltips_file(language="ru"):
    """Получить путь к файлу тултипов для языка"""
    # Список языков для fallback (от специфичного к общему)
    for lang in [language, "ua", "en", "ru"]:
        filename = f"editor_tooltips_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath

    # Если ничего не найдено
    return _HELP_DIR / "editor_tooltips_ru.json"


def load_editor_tooltips(language="ru"):
    """Загрузить тултипы редактора из JSON"""
    filepath = _get_tooltips_file(language)

    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки тултипов: {e}")
        return {}


def get_tooltip(tooltips_data, key):
    """Получить текст подсказки по ключу"""
    tip = tooltips_data.get(key, {})

    # Если есть detail, объединяем
    if "detail" in tip:
        return f"{tip.get('text', '')}\n{tip['detail']}"

    return tip.get("text", "")


# ═══════════════════════════════════════════
# Справка по вкладке «Дубликаты»
# ═══════════════════════════════════════════


def _get_duplicates_help_file(language="ru"):
    """Получить путь к файлу справки дубликатов для языка"""
    # Список языков для fallback (от специфичного к общему)
    for lang in [language, "ua", "en", "ru"]:
        filename = f"duplicates_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath

    # Если ничего не найдено
    return _HELP_DIR / "duplicates_help_ru.json"


def load_duplicates_help(language="ru"):
    """Загрузить справку по дубликатам из JSON"""
    filepath = _get_duplicates_help_file(language)

    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки дубликатов: {e}")
        return {}


def format_duplicates_help_text(help_data):
    """Форматировать текст справки дубликатов для отображения"""
    title = help_data.get("title", "📖 Справка по дубликатам")
    sections = help_data.get("sections", {})

    parts = [title, ""]

    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])

        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")  # Пустая строка между секциями

    return "\n".join(parts)


# ═══════════════════════════════════════════
# Справка по вкладке «Фильтры»
# ═══════════════════════════════════════════


def _get_filters_help_file(language="ru"):
    """Получить путь к файлу справки фильтров для языка"""
    for lang in [language, "ua", "en", "ru"]:
        filename = f"filters_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath
    return _HELP_DIR / "filters_help_ru.json"


def load_filters_help(language="ru"):
    """Загрузить справку по фильтрам из JSON"""
    filepath = _get_filters_help_file(language)
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки фильтров: {e}")
        return {}


def format_filters_help_text(help_data):
    """Форматировать текст справки фильтров для отображения"""
    title = help_data.get("title", "📖 Справка по фильтрам")
    sections = help_data.get("sections", {})

    parts = [title, ""]
    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])
        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════
# Справка по вкладке «Верификация»
# ═══════════════════════════════════════════


def _get_verification_help_file(language="ru"):
    """Получить путь к файлу справки верификации для языка"""
    for lang in [language, "ua", "en", "ru"]:
        filename = f"verification_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath
    return _HELP_DIR / "verification_help_ru.json"


def load_verification_help(language="ru"):
    """Загрузить справку по верификации из JSON"""
    filepath = _get_verification_help_file(language)
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки верификации: {e}")
        return {}


def format_verification_help_text(help_data):
    """Форматировать текст справки верификации для отображения"""
    title = help_data.get("title", "📖 Справка по верификации")
    sections = help_data.get("sections", {})

    parts = [title, ""]
    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])
        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════
# Справка по вкладке «Перевод»
# ═══════════════════════════════════════════


def _get_translation_help_file(language="ru"):
    """Получить путь к файлу справки перевода для языка"""
    for lang in [language, "ua", "en", "ru"]:
        filename = f"translation_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath
    return _HELP_DIR / "translation_help_ru.json"


def load_translation_help(language="ru"):
    """Загрузить справку по переводу из JSON"""
    filepath = _get_translation_help_file(language)
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки перевода: {e}")
        return {}


def format_translation_help_text(help_data):
    """Форматировать текст справки перевода для отображения"""
    title = help_data.get("title", "📖 Справка по переводу")
    sections = help_data.get("sections", {})

    parts = [title, ""]
    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])
        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════
# Справка по вкладке «Зависимости»
# ═══════════════════════════════════════════


def _get_dependencies_help_file(language="ru"):
    """Получить путь к файлу справки зависимостей для языка"""
    for lang in [language, "ua", "en", "ru"]:
        filename = f"dependencies_help_{lang}.json"
        filepath = _HELP_DIR / filename
        if filepath.exists():
            return filepath
    return _HELP_DIR / "dependencies_help_ru.json"


def load_dependencies_help(language="ru"):
    """Загрузить справку по зависимостям из JSON"""
    filepath = _get_dependencies_help_file(language)
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки справки зависимостей: {e}")
        return {}


def format_dependencies_help_text(help_data):
    """Форматировать текст справки зависимостей для отображения"""
    title = help_data.get("title", "📖 Справка по зависимостям")
    sections = help_data.get("sections", {})

    parts = [title, ""]
    for section_key, section in sections.items():
        sec_title = section.get("title", "")
        items = section.get("items", [])
        parts.append(sec_title)
        for item in items:
            parts.append(f"  • {item}")
        parts.append("")

    return "\n".join(parts)
