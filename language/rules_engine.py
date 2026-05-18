import re

from .rules_constants import ALPHABET_FIX_MAP, CORRECTION_RULES, PRONOUN_DECLENSIONS


class LanguageRules:
    def __init__(self, lang_code: str = "ru"):
        self.lang_code = lang_code.lower()
        self.config = PRONOUN_DECLENSIONS.get(self.lang_code, PRONOUN_DECLENSIONS["ru"])
        # Алфавиты для проверки смешивания
        self._cyrillic_pattern = re.compile(r'[\u0400-\u04FF\u0500-\u052F]')
        self._latin_pattern = re.compile(r'[A-Za-z]')

    def auto_correct(self, text: str) -> str:
        if not text:
            return text

        # 0. Проверка на смешанный язык (partial translation)
        # Удаляем перед проверкой:
        # - Шаблонные placeholderы {0}, {name}, etc.
        # - Квадратные скобки RimWorld [founderName], [deity0_name], etc.
        # - Google артефакт /n/n* из Tip-подсказок (когда Google оставляет /n/n* как текст)
        # - RimWorld-формат коды x{0}, x{1} (лат. x + {цифра} — технический префикс)
        # - Внутренние плейсхолдеры переводчика __PLACEHOLDER_n__
        # - Временные placeholderы переменных __VAR_n__
        # - Символы переводов строки \n / \r (не содержат букв, не влияют на has_latin)
        text_without_placeholders = re.sub(
            r'[\n\r]|\{[^}]*\}|\[[^\]]*\]|[\\/]n[\\/]?n\*?|x\{\d{1,2}\}|__PLACEHOLDER_\d+__|__VAR_\d+__',
            '', text, flags=re.IGNORECASE
        )
        has_cyrillic = bool(self._cyrillic_pattern.search(text_without_placeholders))
        has_latin = bool(self._latin_pattern.search(text_without_placeholders))
        if has_cyrillic and has_latin:
            # Смешанный язык - возвращаем как есть для ручной проверки
            # Это сигнализирует, что перевод неполный
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

        Returns:
            Текст с примененной капитализацией
        """
        if not text:
            return text

        # Если есть оригинал, пытаемся сохранить его регистр
        if original:
            original = original.strip()
            if not original:
                return text

            # Проверяем: вся строка заглавными
            if original.isupper():
                return text.upper()

            # Проверяем: вся строка строчными
            if original.islower():
                return text.lower()

            # Смешанный регистр - сохраняем регистр каждого слова
            return self._preserve_word_case(text, original)

        # Капитализация первого символа предложения
        if self.config.capitalizes_sentence_start:
            return text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        return text

    def _preserve_word_case(self, translated: str, original: str) -> str:
        """
        Сохраняет регистр каждого слова из оригинала в переводе.

        Args:
            translated: Переведённый текст
            original: Оригинальный текст с нужным регистром

        Returns:
            Переведённый текст с сохранённым регистром
        """
        orig_words = original.split()
        trans_words = translated.split()
        result_words = []

        for i, trans_word in enumerate(trans_words):
            if i < len(orig_words):
                orig_word = orig_words[i]
                # Проверяем регистр исходного слова
                if orig_word.isupper():
                    result_words.append(trans_word.upper())
                elif orig_word and orig_word[0].isupper():
                    # Заглавная первая буква
                    result_words.append(
                        trans_word[0].upper() + trans_word[1:] if len(trans_word) > 1 else trans_word.upper()
                    )
                else:
                    result_words.append(trans_word.lower())
            else:
                # Если слов больше в переводе, чем в оригинале - обрабатываем по умолчанию
                result_words.append(trans_word.lower())

        return " ".join(result_words)

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

    def is_valid_translation(self, text: str) -> bool:
        """
        Проверяет, является ли текст допустимым переводом на целевом языке.

        Для русского/украинского языка проверяет, что текст не содержит
        смешанных алфавитов (частичных переводов).
        
        Исключение: шаблонные placeholderы вида {0}, {name}, {0_key} и т.д.
        These are legitimate RimWorld template syntax and should not be
        considered as "partial translation" indicators.

        Args:
            text: Текст для проверки

        Returns:
            True если текст является допустимым переводом, False иначе
        """
        if not text or not text.strip():
            return False

        # Remove template placeholders before checking for mixed alphabet
        # RimWorld templates: {0}, {1}, {name}, {0_key}, {PAWN_gender ? A : B}, etc.
        # Также удаляем RimWorld-формат коды x{0}, x{1} (лат. префикс + {цифра})
        # Also remove RimWorld bracket placeholders: [deity0_name], [founderName], etc.
        # Удаляем Google-артефакт /n/n* из Tip-подсказок (когда Google оставляет /n/n* как текст)
        # Also remove internal translator placeholders: __PLACEHOLDER_0__, __PLACEHOLDER_1__, etc.
        # And translation variable placeholders: __VAR_0__, __VAR_1__, etc.
        # Удаляем символы переводов строки \n / \r (не содержат букв, не влияют на has_latin)
        text_without_placeholders = re.sub(
            r'[\n\r]|\{[^}]*\}|\[[^\]]*\]|[\\/]n[\\/]?n\*?|x\{\d{1,2}\}|__PLACEHOLDER_\d+__|__VAR_\d+__',
            '', text, flags=re.IGNORECASE
        )

        has_cyrillic = bool(self._cyrillic_pattern.search(text_without_placeholders))
        has_latin = bool(self._latin_pattern.search(text_without_placeholders))

        # Для языков с кириллицей: текст не должен содержать латиницу
        if self.lang_code in ('ru', 'uk'):
            # Если есть и кириллица, и латиница - это частичный перевод
            if has_cyrillic and has_latin:
                return False

        return True
