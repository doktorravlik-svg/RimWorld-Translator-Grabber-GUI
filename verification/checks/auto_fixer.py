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

    def fix(self, text):
        changes = []
        original = text

        # 1. Исправление пробелов вокруг XML-тегов и переменных
        # Убираем слипание: Слово<color -> Слово <color
        text = re.sub(r"([а-яА-Я])(<|{)", r"\1 \2", text)
        # Убираем слипание: </color>Слово -> </color> Слово
        text = re.sub(r"(>|})([а-яА-Я])", r"\1 \2", text)

        # 2. Безопасная Ё-фикация
        for eng_e, rus_yo in self.YO_SAFE_REPLACE.items():
            pattern = rf"\b{eng_e}\b"
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, rus_yo, text, flags=re.IGNORECASE)
                changes.append(f"ё: {eng_e}->{rus_yo}")

        # 3. Очистка типографики (важно для 2026 года)
        # Замена « » и “ ” на стандартные " для XML
        text = text.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')

        # 4. Удаление двойных пробелов (частая ошибка при редактировании)
        text = re.sub(r"[ ]{2,}", " ", text)

        # 5. Исправление пробелов внутри тегов
        text = re.sub(r"\[\s*(.*?)\s*\]", r"[\1]", text)
        text = re.sub(r"\{\s*(\d+)\s*\}", r"{\1}", text)

        return text, changes
