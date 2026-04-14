# workers/__init__.py
"""
Workers - асинхронные worker-ы для GUI.

Этот пакет предоставляет классы для выполнения длительных операций
(верификация, перевод, дубликаты, целостность) в отдельных потоках без блокировки GUI.

Основные классы:
- BaseWorker: Базовый класс для всех worker-ов
- VerificationWorker: Worker для верификации переводов
- TranslationWorker: Worker для перевода модов
- DuplicateWorker: Worker для слияния дубликатов
- IntegrityWorker: Worker для проверки целостности

Пример использования:
    from workers import VerificationWorker

    worker = VerificationWorker(mods_folder="C:/Mods")
    worker.on_progress(lambda p, t, m: print(f"{p}/{t}: {m}"))
    worker.on_complete(lambda r: print(f"Results: {r.total_mods}"))
    worker.start()
"""

# Экспорт базового класса
from .base_worker import BaseWorker
from .duplicate_worker import DuplicateResultDTO, DuplicateWorker
from .integrity_worker import IntegrityResultDTO, IntegrityWorker
from .translation_worker import TranslationResultDTO, TranslationWorker

# Экспорт worker-ов
from .verification_worker import VerificationWorker

# Экспорт версии пакета
__version__ = "1.1.0"

# Публичный API
__all__ = [
    "BaseWorker",
    "DuplicateResultDTO",
    "DuplicateWorker",
    "IntegrityResultDTO",
    "IntegrityWorker",
    "TranslationResultDTO",
    "TranslationWorker",
    "VerificationWorker",
]
