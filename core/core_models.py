# core_models.py
import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class TranslationEntry:
    """Представляет одну запись перевода"""

    key: str
    value: str
    file_path: str
    mod_name: str
    hash: str = ""
    timestamp: str = ""
    mod_version: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Инициализирует поля после создания объекта"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.hash:
            # Подстраховка на случай, если value пришёл как None
            safe_value = self.value if self.value is not None else ""
            self.hash = hashlib.md5(safe_value.encode("utf-8")).hexdigest()[:12]


@dataclass(slots=True)
class AutoResolveSettings:
    """Настройки автоматического разрешения конфликтов"""

    prefer_longer: bool = True
    prefer_newer_version: bool = True
    prefer_higher_priority: bool = True
    create_synonyms: bool = False
    priority_mods: list[str] = field(default_factory=list)
