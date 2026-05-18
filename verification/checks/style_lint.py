# verification/checks/style_lint.py
import re


class StyleLint:
    """
    Стилистический контроль и анти-калька для переводов
    Обнаруживает пассивный залог, канцеляризмы и нейросетевые шаблоны
    Стандарт 2026 года для RimWorld
    """

    def __init__(self):
        # Паттерны для поиска пассивного залога и канцеляризмов
        self.PATTERNS = {
            r"(?i)\bвы\s+были\s+\w+ы\b": "Пассивный залог (Вы были ударены). Лучше: 'Вас ударили'.",
            r"(?i)\bпожалуйста,?\s+(выберите|нажмите|введите)\b": "Излишняя вежливость 'Пожалуйста'. В RimWorld лучше сразу: 'Выберите'.",
            r"(?i)\bявляется\s+\w+ом\b": "Канцеляризм 'является'. Лучше просто: 'это ...'.",
            r"(?i)\bс\s+помощью\s+того,\s+чтобы\b": "Слишком сложная конструкция. Упростите.",
            r"(?i)\bможет\s+быть\s+использован\b": "Пассивный залог. Лучше: 'Используйте для ...'.",
            r"(?i)\bв\s+целях\b": "Канцеляризм 'в целях'. Замените на 'для'.",
            r"(?i)\bданный\s+\w+\b": "Канцеляризм 'данный'. Удалите или замените на 'этот'.",
        }

    def verify(self, text):
        warnings = []
        for pattern, suggestion in self.PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                warnings.append({
                    "type": "STYLE_ADVICE",
                    "severity": "info",
                    "msg": suggestion,
                    "match": match.group(0),
                    "context": text[max(0, match.start()-15):min(len(text), match.end()+15)]
                })
        return warnings
