# verification/checks/lang_detector.py
import re


class LangDetector:
    """
    Детектор непереведенного английского текста
    Специальная логика для RulePackDef
    Стандарт 2026 года
    """

    def __init__(self):
        self.LATIN_WORDS_PATTERN = re.compile(r'\b[a-zA-Z]{5,}\b')
        self.LATIN_FULL_PATTERN = re.compile(r'[a-zA-Z]{4,}')
        self.CYRILLIC_PATTERN = re.compile(r'[а-яА-ЯёЁ]')
        self.LATIN_ANY_PATTERN = re.compile(r'[a-zA-Z]')
        self.CLEAN_TOKEN_PATTERN = re.compile(r'\[.*?\]')

    def verify(self, text, original_text=None):
        errors = []
        if not isinstance(text, str):
            return errors

        # Если перевод 1-в-1 совпадает с оригиналом и там есть латиница
        if original_text and isinstance(original_text, str) and text.strip() == original_text.strip():
            if self.LATIN_FULL_PATTERN.search(text):
                errors.append({
                    "type": "CRITICAL_UNTRANSLATED",
                    "severity": "error",
                    "msg": "Текст полностью совпадает с оригиналом (не переведён)"
                })

        # Поиск английских слов длиннее 4 символов среди кириллицы
        eng_words = self.LATIN_WORDS_PATTERN.findall(text)
        if eng_words:
            errors.append({
                "type": "WARNING_ENG_WORD",
                "severity": "warning",
                "msg": f"Найдены английские слова: {', '.join(eng_words)}",
                "words": eng_words
            })

        # ✅ НОВОЕ: Проверка на смешанный язык (двухязычный контент)
        mixed_lang_errors = self._check_mixed_language(text)
        errors.extend(mixed_lang_errors)

        return errors

    def _check_mixed_language(self, text):
        """
        Проверяет наличие смешанного языка в тексте.
        Полезно для обнаружения случаев, когда в переводе остались английские слова
        рядом с переведёнными фразами.
        """
        errors = []

        if not text or not text.strip():
            return errors

        try:
            has_cyrillic = bool(self.CYRILLIC_PATTERN.search(text))
            has_latin = bool(self.LATIN_ANY_PATTERN.search(text))

            if has_cyrillic and has_latin:
                latin_words = self.LATIN_WORDS_PATTERN.findall(text)
                if len(latin_words) >= 3:
                    errors.append({
                        "type": "MIXED_LANGUAGE_CONTENT",
                        "severity": "warning",
                        "msg": f"Обнаружен смешанный язык: найдены английские слова '{', '.join(latin_words[:3])}' рядом с кириллицей",
                        "words": latin_words
                    })
        except Exception:
            pass

        return errors

    def verify_rulepack_line(self, xml_line):
        """Специальная проверка для строк RulePackDef -> значение"""
        errors = []
        if not isinstance(xml_line, str) or "->" not in xml_line:
            return errors

        try:
            _, result = xml_line.split("->", 1)
            # Удаляем токены в скобках [pawn_nameDef], чтобы они не считались английским текстом
            clean_text = self.CLEAN_TOKEN_PATTERN.sub('', result).strip()

            # Если после очистки от токенов остался английский текст
            if self.LATIN_FULL_PATTERN.search(clean_text):
                errors.append({
                    "type": "RULEPACK_UNTRANSLATED_VAL",
                    "severity": "warning",
                    "msg": f"В результате правила найден английский текст: '{clean_text[:50]}'"
                })
        except Exception:
            pass
        return errors