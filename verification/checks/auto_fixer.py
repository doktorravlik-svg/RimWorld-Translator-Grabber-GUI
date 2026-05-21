# verification/checks/auto_fixer.py
import re


class AutoFixer:
    """
    Автоматические безопасные исправления переводов
    Только 100% безопасные правки, не меняющие смысл
    Стандарт 2026 года
    """

    def __init__(self):
        # Словарь для безопасной замены "е" на "ё" (только бесспорные случаи)
        self.YO_SAFE_REPLACE = {
            "еще": "ещё",
            "ее": "её",
            "свое": "своё",
            "мое": "моё",
            "твое": "твоё",
            "идет": "идёт",
            "желтый": "жёлтый"
        }

        # Исправлено: предкомпиляция паттернов
        # Добавлены ё и Ё в диапазоны символов
        self.SPACE_BEFORE_TAG = re.compile(r"([а-яА-ЯёЁa-zA-Z0-9_])(<|{)")
        self.SPACE_AFTER_TAG = re.compile(r"(>|})([а-яА-ЯёЁa-zA-Z0-9_])")
        
        # Предкомпиляция паттернов для ёфикации
        self.YO_PATTERNS = {
            word: (re.compile(rf"\b{word}\b", re.IGNORECASE), replacement)
            for word, replacement in self.YO_SAFE_REPLACE.items()
        }
        
        # Паттерны для типографики
        self.DOUBLE_SPACE = re.compile(r"[ ]{2,}")
        self.TAG_WHITESPACE = re.compile(r"\[\s*(.*?)\s*\]")
        self.CURLY_WHITESPACE = re.compile(r"\{\s*(\d+)\s*\}")
        
        # Теги и токены для защиты от замены кавычек
        self.TAG_DELIMITER = re.compile(r"(<[^>]+>|\[[^\]]+\])")

    def _preserve_case_yo(self, match, replacement):
        """Вспомогательный метод для сохранения регистра при ёфикации"""
        word = match.group(0)
        if word.isupper():
            return replacement.upper()
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    def fix(self, text):
        if not isinstance(text, str):
            return text, []

        changes = []
        original = text

        # 1. Исправление пробелов вокруг XML-тегов и переменных (исключая стыки тегов)
        # Убираем слипание: Слово<color -> Слово <color
        text = self.SPACE_BEFORE_TAG.sub(r"\1 \2", text)
        # Убираем слипание: </color>Слово -> </color> Слово
        text = self.SPACE_AFTER_TAG.sub(r"\1 \2", text)

        # 2. Безопасная Ё-фикация с сохранением регистра (Еще -> Ещё, ЕЩЕ -> ЕЩЁ)
        for word, (pattern, rus_yo) in self.YO_PATTERNS.items():
            if pattern.search(text):
                text = pattern.sub(
                    lambda m: self._preserve_case_yo(m, rus_yo),
                    text
                )
                changes.append(f"ё: {word}->{rus_yo}")

        # 3. Умная очистка типографики (не трогаем кавычки внутри тегов [ ] и < >)
        # Разбиваем текст на токены, чтобы менять кавычки только в обычном тексте
        parts = self.TAG_DELIMITER.split(text)
        for i in range(len(parts)):
            # Если это обычный текст, а не тег/токен
            if not (parts[i].startswith('<') or parts[i].startswith('[')):
                parts[i] = parts[i].replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
        text = "".join(parts)

        # 4. Удаление двойных пробелов (но сохраняем переносы строк и табы)
        text = self.DOUBLE_SPACE.sub(" ", text)

        # 5. Исправление пробелов внутри тегов (безопасные жадные квантификаторы)
        text = self.TAG_WHITESPACE.sub(r"[\1]", text)
        text = self.CURLY_WHITESPACE.sub(r"{\1}", text)

        return text, changes