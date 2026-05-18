# verification/checks/dependencies.py
"""
Проверка зависимостей мода.
"""

from loguru import logger
import os
from typing import Any

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class DependenciesCheck(VerificationCheck):
    """Проверка зависимостей мода"""

    @property
    def name(self) -> str:
        return "dependencies"

    @property
    def description(self) -> str:
        return "Проверка зависимостей мода"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        all_mods = context.get("all_mods", {})
        dependencies = mod_info.get("dependencies", [])

        missing = []
        for dep in dependencies:
            dep_id = dep.get("packageId") if isinstance(dep, dict) else str(dep)
            if dep_id and dep_id not in all_mods:
                missing.append(dep_id)

        passed = len(missing) == 0
        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity="warning",
            message=f"Отсутствуют зависимости: {', '.join(missing)}"
            if missing
            else "Все зависимости найдены",
            details={"missing": missing},
        )
