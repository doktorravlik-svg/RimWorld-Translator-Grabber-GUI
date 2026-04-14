import re

from .rules_constants import PLACEHOLDER_PATTERNS


def validate_placeholders(original: str, translated: str) -> tuple[bool, list[str]]:
    """
    Базовая проверка плейсхолдеров (совместимость с оригиналом).
    Проверяет, что все {0}, {1} и т.д. из оригинала есть в переводе.
    """
    errors = []

    # Собираем все найденные теги, избегая дублирования
    all_orig_tags = set()
    all_trans_tags = set()

    for pattern in PLACEHOLDER_PATTERNS:
        all_orig_tags.update(re.findall(pattern, original))
        all_trans_tags.update(re.findall(pattern, translated))

    # Проверяем утерю
    missing = all_orig_tags - all_trans_tags
    if missing:
        missing_str = "', '".join(sorted(str(m) for m in missing))
        errors.append(f"Утеряны технические теги: '{missing_str}'")

    is_valid = len(errors) == 0
    return is_valid, errors


def validate_translation_integrity(original: str, translated: str) -> tuple[bool, list[str]]:
    """
    Расширенная проверка целостности.
    Проверяет не только утерю, но и появление лишних тегов, а также пунктуацию.
    """
    is_valid, errors = validate_placeholders(original, translated)

    # Собираем все теги для проверки лишних
    all_orig_tags = set()
    all_trans_tags = set()
    for pattern in PLACEHOLDER_PATTERNS:
        all_orig_tags.update(re.findall(pattern, original))
        all_trans_tags.update(re.findall(pattern, translated))

    # Дополнительная проверка на лишние теги (которых не было в оригинале)
    extra = all_trans_tags - all_orig_tags
    if extra:
        extra_str = "', '".join(sorted(str(e) for e in extra))
        errors.append(f"Обнаружены лишние теги: '{extra_str}'")

    # Проверка: не превратились ли <li> в что-то другое
    if "<li>" in original.lower() and "<li>" not in translated.lower():
        # Проверяем, может тег просто написан с ошибкой
        if any(bad in translated for bad in ["< li>", "<li >", "[li]"]):
            errors.append("Тег <li> написан с ошибкой (проверьте пробелы или скобки)")

    # Проверка соответствия знаков препинания в конце (?!.)
    if original and translated:
        for char in ".?!":
            if original.endswith(char) and not translated.endswith(char):
                errors.append(f"В оригинале есть '{char}' в конце, в переводе — нет")

    return len(errors) == 0, errors


def check_translation_quality(original: str, translated: str) -> list[str]:
    """
    Проверка качества перевода.
    Следит за длиной строки и подозрительными изменениями.
    """
    warnings = []
    if not original or not translated:
        return warnings

    # Проверка на аномальную разницу в длине (более чем в 3 раза)
    len_orig = len(original)
    len_trans = len(translated)
    if len_trans > len_orig * 3 and len_orig > 5:
        warnings.append("Перевод значительно длиннее оригинала")
    elif len_trans < len_orig / 3 and len_orig > 10:
        warnings.append("Перевод подозрительно короткий")

    return warnings
