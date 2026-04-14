import re

from .rules_constants import ALPHABET_FIX_MAP, CORRECTION_RULES, PRONOUN_DECLENSIONS


class LanguageRules:
    def __init__(self, lang_code: str = "ru"):
        self.lang_code = lang_code.lower()
        self.config = PRONOUN_DECLENSIONS.get(self.lang_code, PRONOUN_DECLENSIONS["ru"])

    def auto_correct(self, text: str) -> str:
        if not text:
            return text

        # 1. Исправление смешивания алфавитов (ы -> и для украинизации и т.д.)
        text = self.fix_alphabet_mixing(text)

        # 2. Словарная коррекция (суржик)
        corrected = text
        for error, fix in CORRECTION_RULES.items():
            pattern = re.compile(re.escape(error), re.IGNORECASE)

            def replace_case(match):
                found = match.group(0)
                if found.isupper():
                    return fix.upper()
                if found[0].isupper():
                    return fix.capitalize()
                return fix

            corrected = pattern.sub(replace_case, corrected)
        return corrected

    def fix_alphabet_mixing(self, text: str) -> str:
        """Исправляет буквы из чужого алфавита (например, русская 'ы' в украинском)"""
        if self.lang_code not in ALPHABET_FIX_MAP:
            return text

        mapping = ALPHABET_FIX_MAP[self.lang_code]
        for wrong, right in mapping.items():
            # Обрабатываем оба регистра
            text = text.replace(wrong, right)
            text = text.replace(wrong.upper(), right.upper())
        return text

    def fix_rimworld_tags(self, text: str) -> str:
        """Исправляет типичные ошибки в XML разметке RimWorld"""
        # Исправляем [ Name] или [Name ] -> [Name]
        text = re.sub(r"\[\s*(.*?)\s*\]", r"[\1]", text)

        # Исправляем { 0} или {0 } -> {0}
        text = re.sub(r"\{\s*(\d+)\s*\}", r"{\1}", text)

        # Исправляем кривые <li>: <li > или </ li>
        text = re.sub(r"<\s*li\s*>", "<li>", text)
        text = re.sub(r"<\s*/\s*li\s*>", "</li>", text)

        return text

    def apply_capitalization(self, text: str, original: str = None) -> str:
        """
        Применяет правила капитализации целевого языка.

        Args:
            text: Текст для капитализации
            original: Оригинальный текст (для сохранения регистра)
        """
        if not text:
            return text

        # Если есть оригинал, пытаемся сохранить его регистр
        if original:
            if original.isupper():
                return text.upper()
            elif original[0].isupper():
                return text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            else:
                return text.lower()

        # Капитализация первого символа предложения
        if self.config.capitalizes_sentence_start:
            return text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        return text

    def get_pronoun_case(self, pronoun: str, case: str) -> str:
        """
        Возвращает местоимение в нужном падеже.

        Args:
            pronoun: Местоимение в именительном падеже
            case: Падеж ('им', 'род', 'дат', 'вин', 'твор', 'пред')
        """
        pronoun_lower = pronoun.lower()

        if pronoun_lower in self.config.pronoun_cases:
            cases = self.config.pronoun_cases[pronoun_lower]
            return cases.get(case, pronoun)

        return pronoun

    def is_case_sensitive_duplicate(self, text1: str, text2: str) -> bool:
        """
        Проверяет, являются ли два текста дубликатами с учётом регистра.

        Args:
            text1: Первый текст
            text2: Второй текст

        Returns:
            True если это дубликаты (игнорируя регистр)
        """
        return text1.lower() == text2.lower()

    def get_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет семантическую схожесть двух текстов.
        Упрощённая версия на основе совпадения слов.

        Args:
            text1: Первый текст
            text2: Второй текст

        Returns:
            float: Коэффициент схожести от 0.0 до 1.0
        """
        if not text1 or not text2:
            return 0.0

        # Приводим к нижнему регистру
        t1 = text1.lower()
        t2 = text2.lower()

        # Если тексты идентичны
        if t1 == t2:
            return 1.0

        # Разбиваем на слова
        words1 = set(t1.split())
        words2 = set(t2.split())

        if not words1 or not words2:
            return 0.0

        # Вычисляем коэффициент Жаккара
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0
