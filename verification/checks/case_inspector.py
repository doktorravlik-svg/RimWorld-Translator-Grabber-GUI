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

        # Исправлено: все комбинации предлогов и токенов компилируются заранее
        self._compiled_rules = []
        for prep_regex, suffix in self.RULES.items():
            for token in self.TARGET_TOKENS:
                # Исправлено: используем корректный lookahead для проверки отсутствия суффикса
                pattern = re.compile(
                    f"{prep_regex}\\s+{{({token})(?![^}}]*{suffix})[^}}]*}}",
                    re.IGNORECASE
                )
                self._compiled_rules.append((pattern, suffix))

    def verify_line(self, text):
        """Проверяет строку на наличие пропущенных падежных маркеров."""
        errors = []
        if not isinstance(text, str):
            return errors

        for pattern, suffix in self._compiled_rules:
            for match in pattern.finditer(text):
                errors.append({
                    "type": "GRAMMAR_CASE_MISSING",
                    "severity": "warning",
                    "prep": match.group(1),
                    "token": match.group(2),
                    "expected_suffix": suffix,
                    "context": text[max(0, match.start()-10):min(len(text), match.end()+10)],
                })
        return errors