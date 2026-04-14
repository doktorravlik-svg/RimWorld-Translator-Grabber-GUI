# translation/engines/base.py
"""
Базовый класс для движков перевода.

Все движки должны наследовать TranslationEngine и реализовать
метод translate().
"""

from abc import ABC, abstractmethod
from typing import Optional


class TranslationEngine(ABC):
    """
    Абстрактный базовый класс для движков перевода.

    Attributes:
        name: Название движка
        source_lang: Исходный язык (auto для автоопределения)
        target_lang: Целевой язык
        proxy: Словарь прокси {http: ..., https: ...}
    """

    def __init__(
        self,
        source_lang: str = "auto",
        target_lang: str = "ru",
        proxy: Optional[dict] = None,
    ):
        self.name = self.__class__.__name__
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.proxy = proxy
        self._initialized = False
        self._error_count = 0

    @abstractmethod
    def translate(self, text: str) -> Optional[str]:
        """
        Переводит текст.

        Args:
            text: Текст для перевода

        Returns:
            Переведённый текст или None при ошибке
        """
        pass

    def is_available(self) -> bool:
        """
        Проверяет доступность движка.

        Returns:
            True если движок готов к работе
        """
        return self._initialized

    def reset_error_count(self):
        """Сбрасывает счётчик ошибок."""
        self._error_count = 0

    def increment_error_count(self):
        """Увеличивает счётчик ошибок."""
        self._error_count += 1

    @property
    def error_count(self) -> int:
        return self._error_count

    def __repr__(self) -> str:
        status = "available" if self._initialized else "unavailable"
        return f"{self.name}({self.source_lang}->{self.target_lang}, {status})"
