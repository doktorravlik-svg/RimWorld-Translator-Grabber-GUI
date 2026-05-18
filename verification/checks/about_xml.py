# verification/checks/about_xml.py
"""
Проверка корректности About.xml.
"""

from loguru import logger
import os
from typing import Any

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class AboutXmlCheck(VerificationCheck):
    """Проверка корректности About.xml"""

    @property
    def name(self) -> str:
        return "about_xml"

    @property
    def description(self) -> str:
        return "Проверка корректности About.xml"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        about_data = mod_info.get("about_data", {})

        errors = []
        if not about_data.get("mod_id"):
            errors.append("Отсутствует packageId")
        if not about_data.get("name"):
            errors.append("Отсутствует название мода")

        version = about_data.get("version", "0.0.0")
        if not self._is_valid_version(version):
            errors.append(f"Некорректный формат версии: {version}")

        passed = len(errors) == 0
        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity="error",
            message="; ".join(errors) if errors else "About.xml корректен",
            details={"errors": errors},
        )

    def _is_valid_version(self, version: str) -> bool:
        try:
            parts = version.split(".")
            return len(parts) >= 2 and all(p.isdigit() for p in parts)
        except (AttributeError, ValueError):
            return False
