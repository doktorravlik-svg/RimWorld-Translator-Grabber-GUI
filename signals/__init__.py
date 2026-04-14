"""
Система сигналов для слабой связи между модулями.

Модуль предоставляет:
- Базовые классы событий (Event)
- Специализированные события (LogEvent, ProgressEvent, etc.)
- Централизованную шину сигналов (SignalBus)

Использование:
    from signals import SignalBus, LogEvent, LogLevel
    
    bus = SignalBus.get_instance()
    bus.connect(LogEvent, lambda e: print(f"Log: {e.message}"))
    bus.emit_log(LogLevel.INFO, "Hello, World!")
"""

from signals.events import (
    Event,
    LogLevel,
    LogEvent,
    ProgressEvent,
    VerificationStatus,
    VerificationEvent,
    TranslationEvent,
    ConflictEvent,
    ErrorEvent,
)

from signals.signal_bus import SignalBus

# Экспорт наиболее часто используемых компонентов
__all__ = [
    # Базовые классы
    "Event",
    
    # Уровни логирования
    "LogLevel",
    
    # События
    "LogEvent",
    "ProgressEvent",
    "VerificationStatus",
    "VerificationEvent",
    "TranslationEvent",
    "ConflictEvent",
    "ErrorEvent",
    
    # Шина сигналов
    "SignalBus",
]

# Версия модуля
__version__ = "1.0.0"
