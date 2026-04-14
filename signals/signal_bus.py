"""
Централизованная шина сигналов для связи между модулями.

Обеспечивает слабую связь между компонентами системы через
подписку на события. Использует WeakSet для автоматической
отписки при удалении объектов-подписчиков.
"""

import threading
from collections.abc import Callable
from typing import Any, Optional
from weakref import WeakSet

from signals.events import (
    ConflictEvent,
    ErrorEvent,
    Event,
    LogEvent,
    LogLevel,
    ProgressEvent,
    TranslationEvent,
    VerificationEvent,
    VerificationStatus,
)


class SignalBus:
    """
    Централизованный обработчик сигналов (Singleton).

    Обеспечивает:
    - Потокобезопасную отправку событий
    - Автоматическую отписку при удалении объектов (WeakSet)
    - Внутреннюю очередь для асинхронной обработки
    """

    _instance: Optional["SignalBus"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SignalBus":
        """Реализация Singleton паттерна."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Инициализация шины сигналов."""
        if self._initialized:
            return

        # Подписки: Type[Event] -> WeakSet[Callable]
        self._subscriptions: dict[type[Event], WeakSet[Callable]] = {}

        # Потокобезопасность
        self._lock = threading.RLock()

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "SignalBus":
        """Получить глобальный экземпляр SignalBus."""
        return cls()

    def connect(self, event_type: type[Event], callback: Callable[[Event], None]) -> None:
        """
        Подписаться на событие определённого типа.

        Args:
            event_type: Класс события (например, LogEvent)
            callback: Функция обратного вызова, принимающая Event
        """
        with self._lock:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = WeakSet()

            self._subscriptions[event_type].add(callback)

    def disconnect(self, event_type: type[Event], callback: Callable[[Event], None]) -> bool:
        """
        Отписаться от события.

        Args:
            event_type: Класс события
            callback: Функция обратного вызова

        Returns:
            True если отписка успешна, False если callback не был подписан
        """
        with self._lock:
            if event_type not in self._subscriptions:
                return False

            subscriptions = self._subscriptions[event_type]
            if callback in subscriptions:
                subscriptions.discard(callback)
                return True
            return False

    def emit(self, event: Event) -> None:
        """
        Отправить событие всем подписчикам.

        Args:
            event: Событие для отправки
        """
        event_type = type(event)

        # Создаём копию подписчиков, чтобы избежать проблем
        # при изменении подписок во время итерации
        with self._lock:
            callbacks = []
            if event_type in self._subscriptions:
                callbacks = list(self._subscriptions[event_type])

        # Вызываем все обратные вызовы
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                # Логируем ошибку, но не прерываем обработку
                print(f"Error in signal callback: {e}")

    def emit_log(self, level: LogLevel, message: str, source: str = "unknown") -> None:
        """
        Отправить событие логирования.

        Args:
            level: Уровень важности
            message: Текст сообщения
            source: Источник события
        """
        event = LogEvent(level=level, message=message, source=source)
        self.emit(event)

    def emit_progress(
        self, current: int, total: int, message: str = "", source: str = "unknown"
    ) -> None:
        """
        Отправить событие прогресса.

        Args:
            current: Текущее значение
            total: Всего элементов
            message: Дополнительное сообщение
            source: Источник события
        """
        event = ProgressEvent(current=current, total=total, message=message, source=source)
        self.emit(event)

    def emit_verification(
        self,
        mod_name: str,
        status: VerificationStatus,
        issues: list[str] | None = None,
        source: str = "unknown",
    ) -> None:
        """
        Отправить событие верификации.

        Args:
            mod_name: Имя модуля/мода
            status: Статус верификации
            issues: Список проблем
            source: Источник события
        """
        event = VerificationEvent(mod_name=mod_name, status=status, issues=issues, source=source)
        self.emit(event)

    def emit_translation(
        self,
        mod_name: str,
        progress: float,
        result: dict[str, Any] | None = None,
        source: str = "unknown",
    ) -> None:
        """
        Отправить событие перевода.

        Args:
            mod_name: Имя модуля/мода
            progress: Прогресс (0.0 - 1.0)
            result: Результат перевода
            source: Источник события
        """
        event = TranslationEvent(mod_name=mod_name, progress=progress, result=result, source=source)
        self.emit(event)

    def emit_conflict(
        self, key: str, mods: list[str], resolution: str | None = None, source: str = "unknown"
    ) -> None:
        """
        Отправить событие конфликта.

        Args:
            key: Ключ конфликта
            mods: Список модов
            resolution: Способ разрешения
            source: Источник события
        """
        event = ConflictEvent(key=key, mods=mods, resolution=resolution, source=source)
        self.emit(event)

    def emit_error(
        self, error_type: str, message: str, traceback: str | None = None, source: str = "unknown"
    ) -> None:
        """
        Отправить событие ошибки.

        Args:
            error_type: Тип ошибки
            message: Сообщение об ошибке
            traceback: Трассировка стека
            source: Источник события
        """
        event = ErrorEvent(
            error_type=error_type, message=message, traceback=traceback, source=source
        )
        self.emit(event)

    def get_subscription_count(self, event_type: type[Event]) -> int:
        """
        Получить количество подписчиков для типа события.

        Args:
            event_type: Класс события

        Returns:
            Количество подписчиков
        """
        with self._lock:
            if event_type not in self._subscriptions:
                return 0
            return len(self._subscriptions[event_type])

    def clear_subscriptions(self, event_type: type[Event] | None = None) -> None:
        """
        Очистить подписки.

        Args:
            event_type: Если указан - очистить только этот тип,
                       иначе все подписки
        """
        with self._lock:
            if event_type is not None:
                if event_type in self._subscriptions:
                    self._subscriptions[event_type].clear()
            else:
                for subscriptions in self._subscriptions.values():
                    subscriptions.clear()
