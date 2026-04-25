# verification/checks/structural_integrity.py
"""
Проверка целостности XML структуры и переменных {0}.
"""

import logging
import os
from typing import Any

from ..verification_coordinator import VerificationCheck, CheckResult


class StructuralIntegrityCheck(VerificationCheck):
    """Проверка целостности XML структуры и переменных {0}"""

    @property
    def name(self) -> str:
        return "structural_integrity"

    @property
    def description(self) -> str:
        return "Проверка XML-тегов и переменных формата {0}"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_path = mod_info.get("mod_path", "")
        errors = []
        warnings = []

        from verification.xml_parser import XMLParser
        parser = XMLParser()

        for root_dir, _, files in os.walk(mod_path):
            for filename in files:
                if not filename.endswith(".xml"):
                    continue
                file_path = os.path.join(root_dir, filename)
                result = parser.parse(file_path)
                if not result.success or result.root is None:
                    errors.append(f"Не удалось распарсить: {file_path}")
                    continue

                # Проверка на невалидные теги
                for child in result.root:
                    if child.tag and not isinstance(child.tag, str):
                        errors.append(f"Некорректный тег в {filename}")
                        continue

                    # Проверка текста на переменные {0}, {1} без соответствия
                    if child.text:
                        text = child.text.strip()
                        open_braces = text.count('{')
                        close_braces = text.count('}')
                        if open_braces != close_braces:
                            warnings.append(
                                f"Несбалансированные фигурные скобки в {filename}/{child.tag}"
                            )

                        # Проверка экранирования
                        if '{' in text and '}' not in text:
                            warnings.append(f"Незакрытая переменная {{ в {filename}/{child.tag}")

        severity = "error" if errors else "warning" if warnings else "info"
        message = "; ".join(errors + warnings) if (errors or warnings) else "Структура XML корректна"
        return CheckResult(
            check_name=self.name,
            passed=len(errors) == 0,
            severity=severity,
            message=message,
            details={"errors": errors, "warnings": warnings},
        )
