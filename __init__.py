# RimWorld Translator Grabber Package
"""
RimWorld Translator Grabber - інструмент для перекладу та верифікації модів RimWorld.

Основні модулі:
- gui: Графічний інтерфейс користувача
- main: Консольний інтерфейс
- translator: Автоматичний переклад
- mod_verifier: Верифікація модів
- duplicate_merger: Об'єднання дублікатів
- integrity_checker: Перевірка цілісності
- game_data_processor: Завантаження офіційних даних гри
- grabber_settings: Налаштування фільтрації тегів
"""

__version__ = "2.1.0"
__author__ = "RimWorld Translator Team"
__python_version__ = "3.14"
__last_updated__ = "2026-04-03"

# Експорт основних компонентів
__all__ = [
    # Основні модулі
    "gui",
    "main",
    # Пакети
    "core",
    "utils",
    "collectors",
    "scanner",
    "translation",
    "language",
    "duplicates",
    "config",
    "integrity",
    "helpers",
    "gui",
    "tests",
    "workers",
    "signals",
    "verification",
    "dto",
]
