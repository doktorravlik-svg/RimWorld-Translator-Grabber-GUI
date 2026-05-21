# verification/checks/style_lint.py
import re


class StyleLint:
    """
    Стилистический контроль и анти-калька для переводов
    Обнаруживает пассивный залог, канцеляризмы и нейросетевые шаблоны
    Стандарт 2026 года для RimWorld
    """

    def __init__(self):
        # Паттерны компилируются один раз при инициализации класса
        raw_patterns = {
            r"\bвы\s+были\s+\w+ы\b": "Пассивный залог (Вы были ударены). Лучше: 'Вас ударили'.",
            r"\bпожалуйста,?\s+(выберите|нажмите|введите)\b": "Излишняя вежливость 'Пожалуйста'. В RimWorld лучше сразу: 'Выберите'.",
            r"\bявляется\s+\w+ом\b": "Канцеляризм 'является'. Лучше просто: 'это ...'.",
            r"\bс\s+помощью\s+того,\s+чтобы\b": "Слишком сложная конструкция. Упростите.",
            r"\bможет\s+быть\s+использован\b": "Пассивный залог. Лучше: 'Используйте для ...'.",
            r"\bв\s+целях\b": "Канцеляризм 'в целях'. Замените на 'для'.",
            r"\bданный\s+\w+\b": "Канцеляризм 'данный'. Удалите или замените на 'этот'.",
        }

        # Сохраняем скомпилированные объекты для высокой производительности
        self.PATTERNS = {re.compile(p, re.IGNORECASE): msg for p, msg in raw_patterns.items()}

    def verify(self, text):
        """Проверяет строку на стилистические ошибки и канцеляризмы."""
        warnings = []
        if not isinstance(text, str):
            return warnings

        for pattern, suggestion in self.PATTERNS.items():
            match = pattern.search(text)
            if match:
                warnings.append({
                    "type": "STYLE_ADVICE",
                    "severity": "info",
                    "msg": suggestion,
                    "match": match.group(0),
                    "context": text[max(0, match.start()-15):min(len(text), match.end()+15)]
                })
        return warnings