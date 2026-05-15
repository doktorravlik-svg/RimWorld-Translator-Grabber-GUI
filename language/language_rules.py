# language_rules.py - Файл-мост для обратной совместимости
from .rules_constants import PRONOUN_DECLENSIONS


# Возвращаем функции, которые использовались в оригинале напрямую
def get_language_config(lang_code):
    """Возвращает конфиг для указанного языка (совместимость)"""
    return PRONOUN_DECLENSIONS.get(lang_code.lower(), PRONOUN_DECLENSIONS["ru"])


def detect_language_from_text(text):
    text_l = text.lower()
    # Характерные буквы для украинского
    if any(c in text_l for c in "іїєґ"):
        return "uk"
    # Характерные буквы для русского (которых нет в украинском)
    if any(c in text_l for c in "ыэъё"):
        return "ru"
    # Остальная кириллица
    if any(c in text_l for c in "абвгдежзийклмнопрстуфхцчшщьюя"):
        return "ru"  # По умолчанию для кириллицы
    return "en"


# Теперь импорты в других ваших файлах:
# import sys; sys.path.append(...)
# from language_rules import LanguageRules, detect_language_from_text
# БУДУТ РАБОТАТЬ ИСПРАВНО.
