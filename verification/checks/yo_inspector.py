# verification/checks/yo_inspector.py
import re


class YoInspector:
    """
    Проверка пропущенной буквы 'ё' в ключевых словах
    Стандарт сообщества RimWorld 2026 года
    """

    def __init__(self):
        # Список слов, где "Е" вместо "Ё" — частая ошибка или меняет смысл
        self.YO_WORDS = [
            "еще", "идет", "пойдет", "придет", "свое", "мое", "твое",
            "желтый", "черный", "мертвый", "спасен", "убит", "тяжелый",
            "легкий", "наемник", "король", "елка", "еж", "береза",
            "все", "ее", "ничего", "чего", "что"
        ]
        # Предкомпиляция регулярных выражений для каждого слова с границами слова (\b)
        self._compiled_patterns = {
            word: re.compile(rf"\b{word}\b", re.IGNORECASE) for word in self.YO_WORDS
        }

    def verify(self, text):
        errors = []
        if not isinstance(text, str):
            return errors

        for word, pattern in self._compiled_patterns.items():
            if pattern.search(text):
                errors.append({
                    "type": "YO_MISSING",
                    "severity": "info",
                    "word": word,
                    "msg": f"Рекомендуется заменить 'е' на 'ё' в слове '{word}'"
                })
        return errors