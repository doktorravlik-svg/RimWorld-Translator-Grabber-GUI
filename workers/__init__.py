# workers/__init__.py
"""
Workers - асинхронные worker-ы для GUI.

Этот пакет предоставляет классы для выполнения длительных операций
(верификация, перевод, дубликаты, целостность) в отдельных потоках без блокировки GUI.

Основные классы:
- BaseWorker: Базовый класс для всех worker-ов
- VerificationWorker: Worker для верификации переводов
- TranslationWorker: Worker для перевода модов (inplace/merge режимы)
- SeparateWorker: Worker для перевода модов (separate режим)
- DuplicateWorker: Worker для слияния дубликатов
- IntegrityWorker: Worker для проверки целостности

Пример использования:
    from workers import TranslationWorker, SeparateWorker
    from workers.factory import create_translation_worker

    # Через фабрику (рекомендуется)
    worker = create_translation_worker(
        mode="separate",
        mods_folder="C:/Mods",
        target_lang="Russian"
    )

    # Или напрямую
    worker = SeparateWorker(mods_folder="C:/Mods")
"""

# Экспорт базового класса
from .base_worker import BaseWorker
from .duplicate_worker import DuplicateResultDTO, DuplicateWorker
from .factory import create_translation_worker, get_available_modes, get_worker_class
from .integrity_worker import IntegrityResultDTO, IntegrityWorker
from .path_strategy import InplacePathStrategy, SeparatePathStrategy, PathStrategy
from .separate_worker import SeparateWorker
from .translation_worker import TranslationResultDTO, TranslationWorker
from .verification_worker import VerificationWorker

# Экспорт версии пакета
__version__ = "1.2.0"

# Публичный API
__all__ = [
    "BaseWorker",
    "DuplicateResultDTO",
    "DuplicateWorker",
    "IntegrityResultDTO",
    "IntegrityWorker",
    "PathStrategy",
    "InplacePathStrategy",
    "SeparatePathStrategy",
    "TranslationResultDTO",
    "TranslationWorker",
    "SeparateWorker",
    "VerificationWorker",
    "create_translation_worker",
    "get_available_modes",
    "get_worker_class",
]
