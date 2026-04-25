# verification/checks/case_inspector.py
import re


class CaseInspector:
    """
    Проверка правильности падежей после предлогов для RimWorld токенов
    Стандарт 2026 года, поддержка всех падежей включая творительный
    """

    def __init__(self):
        # Словарь: Предлог -> Ожидаемый суффикс токена
        self.RULES = {
            r"\b(для|от|из|у|без|около|сзади|вдоль)\b": "_genitive",      # Родительный
            r"\b(к|по)\b": "_dative",                                     # Дательный
            r"\b(про|сквозь|через)\b": "_accusative",                    # Винительный
            r"\b(над|под|перед|за|между)\b": "_instrumental",            # Творительный
            r"\b(о|об|обо|при)\b": "_prepositional",                      # Предложный
        }

        # Токены, которые требуют проверки падежа
        self.TARGET_TOKENS = [
            r"PAWN_nameDef",
            r"PAWN_label",
            r"PAWN_pawn",
            r"FACTION_name",
            r"THING_label",
            r"THING_defName"
        ]

    def verify_line(self, text):
        """Проверяет строку на наличие пропущенных падежных маркеров."""
        errors = []

        for prep_regex, suffix in self.RULES.items():
            # Ищем конструкцию: Предлог + Пробел + {Токен без нужного суффикса}
            # Используем негативный просмотр вперед (?!.*_suffix)
            for token in self.TARGET_TOKENS:
                pattern = f"{prep_regex}\\s+{{({token})(?!.*?{suffix})[^}}]*}}"
                matches = re.finditer(pattern, text, re.IGNORECASE)

                for match in matches:
                    errors.append({
                        "type": "GRAMMAR_CASE_MISSING",
                        "severity": "warning",
                        "prep": match.group(1),
                        "token": match.group(2),
                        "expected_suffix": suffix,
                        "context": text[max(0, match.start()-10):min(len(text), match.end()+10)],
                        "msg": f"Пропущен падежный суффикс {suffix} после предлога '{match.group(1)}'"
                    })
        return errors
