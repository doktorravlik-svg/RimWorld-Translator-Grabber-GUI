# verification/checks_base.py
"""
Базовые классы для проверок верификации.
Выделено в отдельный модуль для избежания циклических импортов.
"""

from abc import ABC, abstractmethod
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from verification.verification_coordinator import CheckResult


class VerificationCheck(ABC):
    """
    Абстрактный класс для проверок верификации.

    Наследуйте этот класс для создания собственных проверок.

    Пример:
        class MyCustomCheck(VerificationCheck):
            @property
            def name(self) -> str:
                return "my_custom_check"

            @property
            def description(self) -> str:
                return "Моя кастомная проверка"

            def run(self, mod_info: Dict, context: Dict) -> "CheckResult":
                # Логика проверки
                return CheckResult(...)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя проверки"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание проверки"""
        pass

    @property
    def severity(self) -> str:
        """Серьёзность по умолчанию"""
        return "warning"

    @abstractmethod
    def run(self, mod_info: dict, context: dict) -> "CheckResult":
        """
        Выполнить проверку.

        Args:
            mod_info: Информация о моде
            context: Контекст верификации

        Returns:
            CheckResult с результатом проверки
        """
        pass
