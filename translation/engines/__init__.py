# translation/engines/__init__.py
"""
Плагин-система для движков перевода.

Поддерживаемые движки:
- Google Translate
- DeepL (через веб-интерфейс)
- MyMemory
- Bing Microsoft Translator
- LibreTranslate
- Argos Translate (оффлайн)
"""

from translation.engines.base import TranslationEngine
from translation.engines.google_engine import GoogleEngine
from translation.engines.deepl_engine import DeepLEngine
from translation.engines.mymemory_engine import MyMemoryEngine
from translation.engines.bing_engine import BingEngine
from translation.engines.libre_engine import LibreEngine
from translation.engines.argos_engine import ArgosEngine

__all__ = [
    "TranslationEngine",
    "GoogleEngine",
    "DeepLEngine",
    "MyMemoryEngine",
    "BingEngine",
    "LibreEngine",
    "ArgosEngine",
]

# Registry всех доступных движков
ENGINE_REGISTRY = {
    "google": GoogleEngine,
    "deepl": DeepLEngine,
    "mymemory": MyMemoryEngine,
    "bing": BingEngine,
    "libre": LibreEngine,
    "argos": ArgosEngine,
}


def get_engine(name: str, **kwargs) -> TranslationEngine:
    """
    Создаёт экземпляр движка по имени.

    Args:
        name: Название движка (google, deepl, mymemory, bing, libre, argos)
        **kwargs: Дополнительные параметры для инициализации

    Returns:
        Экземпляр TranslationEngine

    Raises:
        ValueError: Если движок не найден
    """
    name_lower = name.lower()
    if name_lower not in ENGINE_REGISTRY:
        available = ", ".join(ENGINE_REGISTRY.keys())
        raise ValueError(
            f"Неизвестный движок: '{name}'. Доступные: {available}"
        )
    return ENGINE_REGISTRY[name_lower](**kwargs)


def list_engines() -> list[str]:
    """Возвращает список названий доступных движков."""
    return list(ENGINE_REGISTRY.keys())
