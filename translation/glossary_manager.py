# translation/glossary_manager.py
"""
Менеджер для работы с несколькими файлами глоссария.

Поддерживает:
- Официальные термины (official.json)
- Базовые термины (base.json)
- Извлечённые из переводов (extracted.json)
- Общие термины (common.json)
- Пользовательские термины (user.json) - управляются через TranslationDatabase
- Категории (weapons.json, materials.json, plants.json и т.д.)
"""

import json
import os
from typing import Any

from translation.glossary_utils import MAX_GLOSSARY_SIZE, CATEGORY_PREFIXES, get_lang_code_from_name, determine_category

# Импорты перемещены в начало файла (согласно PEP 8)
try:
    from utils.Morphy import RimWorldUniversalParser
    HAS_MORPHY = True
except ImportError:
    HAS_MORPHY = False

from translation.glossary import Glossary


class GlossaryManager:
    """
    Менеджер для работы с несколькими файлами глоссария.
    
    Args:
        glossary_dir: Директория с файлами глоссария
        logger: Логгер
        use_morphy: Использовать морфологию
        target_lang: Целевой язык
    """

    DEFAULT_FILES = {
        "official": "official.json",
        "base": "base.json",
        "extracted": "extracted.json",
        "common": "common.json",
    }

    def __init__(
        self,
        glossary_dir: str | None = None,
        logger: Any = None,
        use_morphy: bool = False,
        target_lang: str = "ru",
        auto_split_glossary: bool = True,
    ):
        self._target_lang = target_lang.lower()
        self.glossary_dir = glossary_dir or self._get_default_glossary_dir()
        self.logger = logger
        self._use_morphy = use_morphy
        self._auto_split_glossary = auto_split_glossary
        self._entries: dict[str, str] = {}
        # Список источников для каждого термина (не перезаписывается)
        self._term_sources: dict[str, list[str]] = {}
        self._file_sources: dict[str, str] = {}
        self._protected_terms = {
            "li", "ul", "ol", "color", "size", "class", "type", "def",
            "parent", "mayrequire", "tag", "href", "src", "alt", "title",
            "style", "id", "name", "value", "key", "path", "url"
        }
        self._morph_parser: Any | None = None

        # Единый экземпляр Glossary — вся логика применения переводов живёт там
        self._glossary: Glossary = Glossary(
            logger=logger,
            use_morphy=use_morphy,
            target_lang=target_lang,
        )

        if use_morphy and HAS_MORPHY:
            try:
                self._morph_parser = RimWorldUniversalParser(lang=self._target_lang)
            except Exception as e:
                if logger:
                    logger.warning(f"Не удалось инициализировать Morphy: {e}")

        self._load_all_files()

    @property
    def glossary(self) -> Glossary:
        return self._glossary

    def _get_default_glossary_dir(self) -> str:
        from pathlib import Path
        base_dir = Path(__file__).parent.parent
        lang_code = get_lang_code_from_name(self._target_lang)
        return str(base_dir / "data_storage" / lang_code / "glossary")

    def _load_all_files(self) -> None:
        """Загружает все файлы глоссария."""
        if not os.path.exists(self.glossary_dir):
            os.makedirs(self.glossary_dir, exist_ok=True)
            self._create_default_files()

        index_path = os.path.join(self.glossary_dir, "..", "glossary_index.json")
        if not os.path.exists(index_path):
            index_path = os.path.join(self.glossary_dir, "glossary_index.json")

        if os.path.exists(index_path):
            self._load_index(index_path)
        else:
            self._discover_files()

        for filename, source in list(self._file_sources.items()):
            filepath = os.path.join(self.glossary_dir, filename)
            if os.path.exists(filepath):
                self._load_file(filepath, source)

    def _create_default_files(self) -> None:
        """Создаёт стандартные файлы глоссария."""
        for source, filename in self.DEFAULT_FILES.items():
            filepath = os.path.join(self.glossary_dir, filename)
            if not os.path.exists(filepath):
                data = {"entries": {}, "source": source, "created": True}
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def _split_glossary_by_categories(self) -> None:
        if len(self._entries) < MAX_GLOSSARY_SIZE:
            return
        categories: dict[str, dict[str, str]] = {}
        uncategorized: dict[str, str] = {}
        for original, translation in self._entries.items():
            category = determine_category(original)
            if category:
                if category not in categories:
                    categories[category] = {}
                categories[category][original] = translation
            else:
                uncategorized[original] = translation
        for category, entries in categories.items():
            self._save_category_to_file(category, entries)
        if uncategorized:
            self._save_category_to_file("uncategorized", uncategorized)
        self._rebuild_index()

    def _save_category_to_file(self, category: str, entries: dict[str, str]) -> None:
        """Сохраняет категорию в отдельный файл."""
        if not entries:
            return
        filepath = os.path.join(self.glossary_dir, f"{category}.json")
        data = {"entries": entries, "source": category, "auto_split": True}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._file_sources[f"{category}.json"] = category

    def _rebuild_index(self) -> None:
        """Пересобирает индекс файлов."""
        index_path = os.path.join(self.glossary_dir, "glossary_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"files": self._file_sources}, f, ensure_ascii=False, indent=2)

    def _load_index(self, index_path: str) -> None:
        """Загружает индекс файлов."""
        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)
            self._file_sources = index.get("files", {})

    def _discover_files(self) -> None:
        """Обнаруживает файлы глоссария в директории."""
        for filename in os.listdir(self.glossary_dir):
            if filename.endswith(".json") and filename != "glossary_index.json":
                source = filename.replace(".json", "")
                self._file_sources[filename] = source

    def _load_file(self, filepath: str, source: str) -> None:
        """Загружает отдельный файл глоссария."""
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                entries = data.get("entries", {})
                for original, translation in entries.items():
                    key = original.lower()
                    self._entries[key] = translation
                    # Добавляем источник в список, а не перезаписываем
                    if key not in self._term_sources:
                        self._term_sources[key] = []
                    if source not in self._term_sources[key]:
                        self._term_sources[key].append(source)
                    # Синхронизируем с внутренним Glossary
                    self._glossary.add(original, translation)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка загрузки {filepath}: {e}")

    def apply_to_text(self, text: str) -> str:
        """
        Применяет глоссарий к тексту.

        ✅ Использует единую реализацию Glossary.apply_to_text
            — поддержка морфологии, regex-записей, защиты XML-тегов
        """
        return self._glossary.apply_to_text(text)

    def add(self, original: str, translation: str, source: str = "user") -> None:
        """Добавляет запись в глоссарий."""
        key = original.lower()
        self._entries[key] = translation
        if key not in self._term_sources:
            self._term_sources[key] = []
        if source not in self._term_sources[key]:
            self._term_sources[key].append(source)
        self._save_to_source(source, original, translation)
        self._glossary.add(original, translation)
        if self._auto_split_glossary and len(self._entries) >= MAX_GLOSSARY_SIZE:
            self._split_glossary_by_categories()

    def _save_to_source(self, source: str, original: str, translation: str) -> None:
        """Сохраняет запись в соответствующий файл."""
        filename = self.DEFAULT_FILES.get(source, f"{source}.json")
        filepath = os.path.join(self.glossary_dir, filename)

        data = {"entries": {}, "source": source}
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

        data["entries"][original] = translation

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def remove(self, original: str) -> bool:
        """Удаляет запись из глоссария (изо всех файлов-источников)."""
        key = original.lower()
        if key in self._entries:
            del self._entries[key]
            sources = self._term_sources.pop(key, None)
            if sources:
                for source in sources:
                    self._save_to_file(source, original, None)
            self._glossary.remove(original)
            return True
        return False

    def _save_to_file(self, source: str, original: str, translation: str | None) -> None:
        """Сохраняет или удаляет запись в файл."""
        filename = self.DEFAULT_FILES.get(source, f"{source}.json")
        filepath = os.path.join(self.glossary_dir, filename)

        if not os.path.exists(filepath):
            return

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        entries = data.get("entries", {})
        if translation is None:
            entries.pop(original, None)
        else:
            entries[original] = translation

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_to_db(self, db) -> None:
        """Экспортирует термины в базу данных (сохраняет все источники)."""
        try:
            c = db.conn.cursor()
            for key, translation in self._entries.items():
                sources = self._term_sources.get(key, ["user"])
                source_str = ",".join(sources)
                c.execute(
                    "INSERT OR REPLACE INTO glossary (term, translation, category, description, target_language) VALUES (?, ?, ?, ?, ?)",
                    (key, translation, source_str, "", db.target_language)
                )
            db.conn.commit()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка экспорта в БД: {e}")

    def import_from_db(self, db) -> None:
        """Импортирует термины из базы данных."""
        try:
            c = db.conn.cursor()
            c.execute("SELECT term, translation FROM glossary WHERE target_language = ?", (db.target_language,))
            for row in c.fetchall():
                term = row[0] if hasattr(row, '__getitem__') else getattr(row, 'term', None)
                translation = row[1] if hasattr(row, '__getitem__') else getattr(row, 'translation', None)
                if term and translation:
                    self.add(term, translation, "db")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка импорта из БД: {e}")

    def get(self, original: str) -> str | None:
        """Получает перевод."""
        return self._entries.get(original.lower())

    def has(self, original: str) -> bool:
        """Проверяет наличие термина."""
        return original.lower() in self._entries

    def search(self, query: str) -> list[tuple[str, str, str]]:
        """Поиск терминов. Возвращает список (термин, перевод, источники)."""
        query_lower = query.lower()
        results = []
        for key, translation in self._entries.items():
            if query_lower in key or query_lower in translation.lower():
                sources = self._term_sources.get(key, ["unknown"])
                results.append((key, translation, ",".join(sources)))
        return results

    def get_all(self) -> list[tuple[str, str, str]]:
        """Возвращает все записи (термин, перевод, источники)."""
        return [
            (k, v, ",".join(self._term_sources.get(k, ["unknown"])))
            for k, v in self._entries.items()
        ]

    def get_stats(self) -> dict[str, int]:
        """
        Возвращает статистику — сколько терминов приходится на каждый источник.
        Термин, определённый в нескольких файлах, учтётся в каждом из них.
        """
        stats = {}
        for sources in self._term_sources.values():
            for source in sources:
                stats[source] = stats.get(source, 0) + 1
        return stats

    @property
    def count(self) -> int:
        return len(self._entries)
