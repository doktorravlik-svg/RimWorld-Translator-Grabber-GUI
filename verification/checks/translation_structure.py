# verification/checks/translation_structure.py
"""
Проверка структуры файлов переводов.
"""

from loguru import logger
import os
from typing import Any

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class TranslationStructureCheck(VerificationCheck):
    """Проверка структуры переводов"""

    @property
    def name(self) -> str:
        return "translation_structure"

    @property
    def description(self) -> str:
        return "Проверка структуры файлов переводов"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        # Базовая проверка типа входных данных
        if not isinstance(mod_info, dict):
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message="Некорректные данные о моде (mod_info не является словарем)",
            )

        mod_path = mod_info.get("mod_path", "")
        
        # Проверка на пустой или некорректный путь
        if not mod_path or not isinstance(mod_path, str):
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message="Путь к моду пуст или некорректен",
            )

        # Проверяем наличие Languages
        langs_path = os.path.join(mod_path, "Languages")
        has_languages = os.path.exists(langs_path)

        # Проверяем наличие Defs
        defs_path = os.path.join(mod_path, "Defs")
        has_defs = os.path.exists(defs_path)

        warnings = []
        if mod_info.get("is_translation") and not has_languages:
            warnings.append("Переводной мод не содержит папку Languages")
        if not has_defs and not has_languages:
            warnings.append("Мод не содержит ни Defs, ни Languages")

        return CheckResult(
            check_name=self.name,
            passed=len(warnings) == 0,
            severity="warning",
            message="; ".join(warnings) if warnings else "Структура переводов корректна",
            details={"warnings": warnings},
        )