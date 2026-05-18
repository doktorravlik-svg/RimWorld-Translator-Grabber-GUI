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

    def verify(self, text):
        errors = []
        for word in self.YO_WORDS:
            # Ищем слово отдельно, чтобы не цеплять части других слов
            pattern = rf"\b{word}\b"
            if re.search(pattern, text, re.IGNORECASE):
                errors.append({
                    "type": "YO_MISSING",
                    "severity": "info",
                    "word": word,
                    "msg": f"Рекомендуется заменить 'е' на 'ё' в слове '{word}'"
                })
        return errors
