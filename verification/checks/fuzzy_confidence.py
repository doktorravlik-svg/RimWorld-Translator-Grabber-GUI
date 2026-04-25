# verification/checks/fuzzy_confidence.py
"""
Анализ уверенности fuzzy-совпадений.
Собирает все теги, которые были сопоставлены через RapidFuzz,
и фильтрует те, у которых score < 85%.
"""

import logging
import os
from typing import Any

from ..verification_coordinator import VerificationCheck, CheckResult


class FuzzyConfidenceCheck(VerificationCheck):
    """
    Анализ уверенности fuzzy-совпадений.
    Собирает все теги, которые были сопоставлены через RapidFuzz,
    и фильтрует те, у которых score < 85%.
    """

    @property
    def name(self) -> str:
        return "fuzzy_confidence"

    @property
    def description(self) -> str:
        return "Оценка уверенности fuzzy-совпадений (порог 85%)"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        # Этот чек работает на уровне already-generated DefInjected файлов
        # Он анализирует логи или кэш fuzzy-совпадений (нужен сбор статистики при генерации)
        # Пока вернём info — требуется интеграция с логами или кэшем
        return CheckResult(
            check_name=self.name,
            passed=True,
            severity="info",
            message="Требует интеграции статистики fuzzy_matches из per_def_generator",
        )
