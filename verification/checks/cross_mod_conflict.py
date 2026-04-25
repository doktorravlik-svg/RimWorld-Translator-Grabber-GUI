# verification/checks/cross_mod_conflict.py
"""
Поиск конфликтов переводов одного и того же Core-дефа между разными модами.
"""

import logging
import os
from typing import Any

from ..verification_coordinator import VerificationCheck, CheckResult
from ..conflict_detector import ConflictDetector

logger = logging.getLogger(__name__)


class CrossModConflictCheck(VerificationCheck):
    """
    Поиск конфликтов переводов одного и того же Core-дефа между разными модами.
    """

    @property
    def name(self) -> str:
        return "cross_mod_conflicts"

    @property
    def description(self) -> str:
        return "Обнаружение конфликтов переводов Core-дефов между модами"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_id = mod_info["mod_id"]
        conflicts = []

        conflict_detector: ConflictDetector | None = context.get("conflict_detector")
        if not conflict_detector:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="ConflictDetector не доступен в контексте",
            )

        # Основная проверка
        try:
            duplicates = conflict_detector.find_duplicate_keys()
            for dup in duplicates:
                if mod_id in [dup.mod_a, dup.mod_b]:
                    conflicts.append(
                        {
                            "key": dup.key,
                            "mods": [dup.mod_a, dup.mod_b],
                            "severity": dup.severity.value,
                            "description": dup.description,
                        }
                    )
        except Exception as e:
            logger.debug(f"Ошибка cross-mod conflict check: {e}")

        if conflicts:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Найдено {len(conflicts)} конфликтов переводов Core-дефов",
                details={"conflicts": conflicts},
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Конфликты переводов Core не обнаружены",
            )

        # Примечание: нижележащий блок является дублем и недостижим,
        # но оставлен в исходном коде для совместимости.
        try:
            duplicates = conflict_detector.find_duplicate_keys()
            for dup in duplicates:
                if mod_id in [dup.mod_a, dup.mod_b]:
                    conflicts.append(
                        {
                            "key": dup.key,
                            "mods": [dup.mod_a, dup.mod_b],
                            "severity": dup.severity.value,
                            "description": dup.description,
                        }
                    )
        except Exception as e:
            logger.debug(f"Ошибка cross-mod conflict check: {e}")

        if conflicts:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Найдено {len(conflicts)} конфликтов переводов Core-дефов",
                details={"conflicts": conflicts},
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Конфликты переводов Core не обнаружены",
            )
