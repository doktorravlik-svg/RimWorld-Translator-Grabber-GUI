"""
События для системы сигналов.

Базовый класс Event и его специализированные реализации для:
- Логирования
- Отслеживания прогресса
- Верификации
- Перевода
- Конфликтов
- Ошибок
"""

from datetime import datetime
from typing import Any, Optional
from enum import Enum


class Event:
    """Базовый класс для всех событий."""

    def __init__(self, source: str):
        """
        Инициализировать событие.

        Args:
            source: Источник события (имя модуля/класса)
        """
        self.timestamp: datetime = datetime.now()
        self.source: str = source

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(source={self.source!r}, timestamp={self.timestamp.isoformat()})"


class LogLevel(Enum):
    """Уровни логирования."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEvent(Event):
    """Событие для логирования."""

    def __init__(self, level: LogLevel, message: str, source: str = "unknown"):
        """
        Создать событие логирования.

        Args:
            level: Уровень важности сообщения
            message: Текст сообщения
            source: Источник события
        """
        super().__init__(source)
        self.level: LogLevel = level
        self.message: str = message

    def __repr__(self) -> str:
        return f"LogEvent(level={self.level.value}, message={self.message!r}, source={self.source!r})"


class ProgressEvent(Event):
    """Событие для отслеживания прогресса."""

    def __init__(self, current: int, total: int, message: str = "", source: str = "unknown"):
        """
        Создать событие прогресса.

        Args:
            current: Текущее значение прогресса
            total: Всего элементов
            message: Дополнительное сообщение
            source: Источник события
        """
        super().__init__(source)
        self.current: int = (current or 0)
        self.total: int = (total or 0)
        self.message: str = message

    @property
    def percentage(self) -> float:
        """Вычислить процент выполнения."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100

    def __repr__(self) -> str:
        return f"ProgressEvent(current={self.current}, total={self.total}, progress={self.percentage:.1f}%)"


class VerificationStatus(Enum):
    """Статусы верификации."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class VerificationEvent(Event):
    """Событие для верификации модов."""

    def __init__(
        self,
        mod_name: str,
        status: VerificationStatus,
        issues: Optional[list[str]] = None,
        source: str = "unknown"
    ):
        """
        Создать событие верификации.

        Args:
            mod_name: Имя модуля/мода
            status: Статус верификации
            issues: Список проблем (если есть)
            source: Источник события
        """
        super().__init__(source)
        self.mod_name: str = mod_name
        self.status: VerificationStatus = status
        self.issues: list[str] = issues or []

    @property
    def is_passed(self) -> bool:
        """Проверить, прошла ли верификация."""
        return self.status == VerificationStatus.PASSED

    @property
    def has_issues(self) -> bool:
        """Есть ли проблемы."""
        return len(self.issues) > 0

    def __repr__(self) -> str:
        return f"VerificationEvent(mod={self.mod_name!r}, status={self.status.value}, issues={len(self.issues)})"


class TranslationEvent(Event):
    """Событие для перевода."""

    def __init__(
        self,
        mod_name: str,
        progress: float,
        result: Optional[dict[str, Any]] = None,
        source: str = "unknown"
    ):
        """
        Создать событие перевода.

        Args:
            mod_name: Имя модуля/мода
            progress: Прогресс перевода (0.0 - 1.0)
            result: Результат перевода (опционально)
            source: Источник события
        """
        super().__init__(source)
        self.mod_name: str = mod_name
        self.progress: float = progress
        self.result: Optional[dict[str, Any]] = result

    @property
    def percentage(self) -> float:
        """Получить прогресс в процентах."""
        return self.progress * 100

    def __repr__(self) -> str:
        return f"TranslationEvent(mod={self.mod_name!r}, progress={self.percentage:.1f}%)"


class ConflictEvent(Event):
    """Событие для конфликтов."""

    def __init__(
        self,
        key: str,
        mods: list[str],
        resolution: Optional[str] = None,
        source: str = "unknown"
    ):
        """
        Создать событие конфликта.

        Args:
            key: Ключ конфликта
            mods: Список модов, участвующих в конфликте
            resolution: Способ разрешения (если разрешён)
            source: Источник события
        """
        super().__init__(source)
        self.key: str = key
        self.mods: list[str] = mods
        self.resolution: Optional[str] = resolution

    @property
    def is_resolved(self) -> bool:
        """Конфликт разрешён?"""
        return self.resolution is not None

    def __repr__(self) -> str:
        return f"ConflictEvent(key={self.key!r}, mods={self.mods!r}, resolved={self.is_resolved})"


class ErrorEvent(Event):
    """Событие для ошибок."""

    def __init__(
        self,
        error_type: str,
        message: str,
        traceback: Optional[str] = None,
        source: str = "unknown"
    ):
        """
        Создать событие ошибки.

        Args:
            error_type: Тип ошибки
            message: Сообщение об ошибке
            traceback: Трассировка стека (опционально)
            source: Источник события
        """
        super().__init__(source)
        self.error_type: str = error_type
        self.message: str = message
        self.traceback: Optional[str] = traceback

    def __repr__(self) -> str:
        return f"ErrorEvent(type={self.error_type!r}, message={self.message!r})"
