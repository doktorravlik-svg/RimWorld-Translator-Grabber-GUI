# translation_db.py — База данных переводов (SQLite)
"""
Централизованная база данных переводов для подхвата в редакторе.

Хранит:
- Переведённые пары ключ → значение из всех обработанных файлов
- Глоссарий терминов (оригинал → перевод)
- Историю версий каждого файла
- Статистику по переводам

Поддержка множественных языков:
- translations_ru.db, translations_en.db, translations_de.db и т.д.
- glossary_ru.json, glossary_en.json и т.д.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from translation.glossary_utils import MAX_GLOSSARY_SIZE, CATEGORY_PREFIXES

DEFAULT_DB_PATH = "translations.db"
DEFAULT_GLOSSARY_PATH = "config/glossary.json"
DATA_STORAGE_DIR = "data_storage"


def _get_default_language() -> str:
    """Читает язык по умолчанию из настроек"""
    try:
        from config.config_manager import get_config_manager
        config = get_config_manager()
        return config.get("target_language", "Russian")
    except Exception:
        return "Russian"


def _resolve_target_language(lang: str | None) -> str:
    """Разрешает язык: если None, читает из конфига"""
    return lang if lang is not None else _get_default_language()


def ensure_lang_dir(lang_code: str) -> Path:
    """Создаёт директорию для языка в data_storage если её нет"""
    base_dir = Path(__file__).parent
    lang_dir = base_dir / DATA_STORAGE_DIR / lang_code
    lang_dir.mkdir(parents=True, exist_ok=True)
    return lang_dir


from translation.glossary_utils import get_lang_code_from_name, determine_category


def get_db_path_for_language(target_language: str = None) -> str:
    """Возвращает путь к БД для указанного языка"""
    target_language = _resolve_target_language(target_language)
    lang_code = get_lang_code_from_name(target_language)
    lang_dir = ensure_lang_dir(lang_code)
    return str(lang_dir / f"translations_{lang_code}.db")


def get_glossary_dir_for_language(target_language: str = None) -> str:
    """Возвращает директорию для глоссария для указанного языка"""
    target_language = _resolve_target_language(target_language)
    lang_code = get_lang_code_from_name(target_language)
    lang_dir = ensure_lang_dir(lang_code)
    glossary_dir = lang_dir / "glossary"
    glossary_dir.mkdir(parents=True, exist_ok=True)
    return str(glossary_dir)


def get_fuzzy_log_path_for_language(target_language: str = None) -> str:
    """Возвращает путь к fuzzy логу для указанного языка"""
    target_language = _resolve_target_language(target_language)
    lang_code = get_lang_code_from_name(target_language)
    lang_dir = ensure_lang_dir(lang_code)
    return str(lang_dir / "fuzzy_review_needed.log")


def get_fuzzy_log_path_for_pair(source_language: str, target_language: str) -> str:
    """Возвращает путь к fuzzy логу для пары языков (source-target)"""
    src_code = get_lang_code_from_name(source_language)
    tgt_code = get_lang_code_from_name(target_language)
    lang_dir = ensure_lang_dir(f"{src_code}-{tgt_code}")
    return str(lang_dir / "fuzzy_review_needed.log")


class TranslationDatabase:
    """База данных переводов с поддержкой нескольких языков"""

    def __init__(self, target_language: str = None):
        target_language = _resolve_target_language(target_language)
        self.target_language = target_language
        self.db_path = get_db_path_for_language(target_language)
        self.glossary_dir = get_glossary_dir_for_language(target_language)
        self.fuzzy_log_path = get_fuzzy_log_path_for_language(target_language)
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Подключиться к базе данных"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")

    def _create_tables(self):
        """Создать таблицы если не существуют"""
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                original_value TEXT DEFAULT '',
                translated_value TEXT DEFAULT '',
                source_language TEXT DEFAULT 'English',
                target_language TEXT DEFAULT 'Russian',
                file_name TEXT DEFAULT '',
                mod_name TEXT DEFAULT '',
                quality_score REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(key, source_language, target_language, file_name)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL,
                translation TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                description TEXT DEFAULT '',
                target_language TEXT DEFAULT 'Russian',
                mod_name TEXT DEFAULT '',
                usage_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(term, target_language)
            )
        """)

        # История версий файлов
        c.execute("""
            CREATE TABLE IF NOT EXISTS file_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                version INTEGER NOT NULL,
                content TEXT NOT NULL,
                entries_count INTEGER DEFAULT 0,
                translated_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, version)
            )
        """)

        # Словарь автопредложений (key → best translation)
        c.execute("""
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                suggested_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                source TEXT DEFAULT 'database',
                target_language TEXT DEFAULT 'Russian',
                UNIQUE(key, target_language, source)
            )
        """)

        self.conn.commit()

        # Индексы для ускорения поиска (добавлено в 2026-04)
        c.execute("CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(key)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_translations_mod ON translations(mod_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_translations_file ON translations(file_name)")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_translations_lang ON translations(source_language, target_language)"
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_glossary_term ON glossary(term)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_glossary_category ON glossary(category)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_glossary_lang ON glossary(target_language)")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_suggestions_key ON suggestions(key, target_language)"
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_history_path ON file_history(file_path)")

        self.conn.commit()

        self._migrate_database()

    def _migrate_database(self):
        """Миграция базы данных: добавление недостающих колонок и исправление схемы"""
        c = self.conn.cursor()

        c.execute("PRAGMA table_info(glossary)")
        columns = [row[1] for row in c.fetchall()]

        if 'target_language' not in columns:
            c.execute("ALTER TABLE glossary ADD COLUMN target_language TEXT DEFAULT 'Russian'")
            c.execute("UPDATE glossary SET target_language = 'Russian' WHERE target_language IS NULL")
            self.conn.commit()

        if 'mod_name' not in columns:
            c.execute("ALTER TABLE glossary ADD COLUMN mod_name TEXT DEFAULT ''")
            c.execute("UPDATE glossary SET mod_name = '' WHERE mod_name IS NULL")
            self.conn.commit()

        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='glossary'")
        table_sql = c.fetchone()[0]

        if 'UNIQUE(term, target_language)' not in table_sql:
            c.execute('''
                CREATE TABLE glossary_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    description TEXT DEFAULT '',
                    target_language TEXT DEFAULT 'Russian',
                    mod_name TEXT DEFAULT '',
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(term, target_language)
                )
            ''')
            c.execute('''
                INSERT INTO glossary_new (term, translation, category, description, target_language, mod_name, usage_count, created_at)
                SELECT term, translation, category, description, COALESCE(target_language, 'Russian'), COALESCE(mod_name, ''), usage_count, created_at FROM glossary
            ''')
            c.execute('DROP TABLE glossary')
            c.execute('ALTER TABLE glossary_new RENAME TO glossary')
            c.execute("CREATE INDEX IF NOT EXISTS idx_glossary_lang ON glossary(target_language)")
            self.conn.commit()

        self._load_glossary_from_json()

    def _load_glossary_from_json(self):
        """Загружает термины из JSON файлов в базу данных для текущего языка"""
        import json

        lang_code = get_lang_code_from_name(self.target_language)
        
        # Ensure glossary directory exists
        os.makedirs(self.glossary_dir, exist_ok=True)

        # Check if there are any JSON files to load (excluding glossary_index.json)
        json_files = []
        try:
            for filename in os.listdir(self.glossary_dir):
                if not filename.endswith(".json"):
                    continue
                category = filename.replace(".json", "")
                # Пропускаем системные файлы
                if category in ("glossary_index",):
                    continue
                json_files.append((filename, category))
        except Exception:
            pass

        # If no JSON files exist, load seed glossary
        if not json_files:
            self._load_seed_glossary()
            return

        c = self.conn.cursor()

        # Сначала загружаем user.json, затем категории
        # Это позволяет категориям обновлять записи из user.json

        # Сортируем: сначала user.json, потом категории
        def sort_key(item):
            filename, category = item
            if category == "user":
                return (0, filename)  # user.json - первым
            return (1, filename)  # категории - после

        json_files.sort(key=sort_key)

        for filename, category in json_files:
            json_path = os.path.join(self.glossary_dir, filename)
            try:
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", {})
                    for term, translation in entries.items():
                        c.execute(
                            "INSERT OR REPLACE INTO glossary (term, translation, category, description, target_language) VALUES (?, ?, ?, ?, ?)",
                            (term, translation, category, "", self.target_language),
                        )
                    self.conn.commit()
                    logger.debug(f"Загружено {len(entries)} терминов из {json_path}")
            except Exception as e:
                logger.debug(f"Не удалось загрузить глоссарий из {json_path}: {e}")

        # Ensure glossary_index.json exists
        self._rebuild_glossary_index_for_dir(self.glossary_dir)

        self._load_seed_glossary()

    def _load_seed_glossary(self):
        """Загружает стандартные термины из внешнего JSON-файла"""
        import json

        c = self.conn.cursor()
        lang_lower = self.target_language.lower()
        lang_code = get_lang_code_from_name(self.target_language)
        # Проверяем наличие seed записей с разными форматами языка
        c.execute(
            "SELECT COUNT(*) FROM glossary WHERE category = 'seed' AND (target_language = ? OR target_language = ? OR target_language = ?)",
            (self.target_language, lang_code, lang_lower)
        )
        if c.fetchone()[0] > 0:
            # Seed entries already exist - don't overwrite JSON files
            # The _load_glossary_from_json already loaded from JSON files
            return

        base_dir = Path(__file__).parent
        seed_dir = base_dir / "config" / "glossary_seeds"

        lang_map = {
            "russian": "ru", "english": "en", "german": "de", "french": "fr",
            "spanish": "es", "chinese": "zh", "japanese": "ja", "korean": "ko",
            "polish": "pl", "portuguese": "pt", "portuguesebrazilian": "pt-br",
            "italian": "it", "ukrainian": "uk", "czech": "cs", "dutch": "nl",
            "swedish": "sv", "turkish": "tr", "hungarian": "hu", "romanian": "ro",
            "arabic": "ar", "finnish": "fi", "norwegian": "no", "danish": "da",
            "thai": "th", "vietnamese": "vi", "catalan": "ca",
        }

        lang_lower = self.target_language.lower()
        lang_code = lang_map.get(lang_lower, lang_lower[:2])

        seed_file = seed_dir / f"rimworld_{lang_code}.json"

        if not seed_file.exists():
            seed_file = seed_dir / "rimworld_en.json"

        if seed_file.exists():
            try:
                with open(seed_file, encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", {})
                    for term, translation in entries.items():
                        c.execute(
                            "INSERT OR IGNORE INTO glossary (term, translation, category, description, target_language) VALUES (?, ?, ?, ?, ?)",
                            (term, translation, "seed", "", self.target_language),
                        )
                    self.conn.commit()
                self._sync_glossary_to_json(self.target_language)
            except Exception as e:
                logger.debug(f"Не удалось загрузить seed глоссарий из {seed_file}: {e}")

    # ===== ОСНОВНЫЕ ОПЕРАЦИИ =====

    def add_translation(
        self,
        key,
        original,
        translated,
        file_name="",
        mod_name="",
        source_lang="English",
        target_lang=None,
    ):
        """Добавить или обновить перевод"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        now = datetime.now().isoformat()

        c.execute(
            """
            INSERT INTO translations (key, original_value, translated_value, file_name, mod_name,
                                     source_language, target_language, last_used, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key, source_language, target_language, file_name)
            DO UPDATE SET
                translated_value = excluded.translated_value,
                original_value = excluded.original_value,
                last_used = ?,
                updated_at = ?,
                usage_count = usage_count + 1
        """,
            (
                key,
                original,
                translated,
                file_name,
                mod_name,
                source_lang,
                target_lang,
                now,
                now,
                now,
                now,
            ),
        )

        self.conn.commit()

    def get_translation(self, key, source_lang="English", target_lang=None):
        """Получить перевод по ключу"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        c.execute(
            """
            SELECT * FROM translations
            WHERE key = ? AND source_language = ? AND target_language = ?
            ORDER BY usage_count DESC, updated_at DESC
            LIMIT 1
        """,
            (key, source_lang, target_lang),
        )
        return c.fetchone()

    def find_similar_translations(self, key, target_lang=None, limit=5):
        """Найти похожие переводы (частичное совпадение ключа)"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        # Ищем по частичному совпадению
        c.execute(
            """
            SELECT * FROM translations
            WHERE (key LIKE ? OR key LIKE ?)
            AND target_language = ?
            ORDER BY usage_count DESC
            LIMIT ?
        """,
            (f"%{key}%", f"%{key.replace('_', ' ')}%", target_lang, limit),
        )
        return c.fetchall()

    def search_translations(self, query, target_lang=None, limit=20):
        """Поиск переводов по ключу или значению"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        search = f"%{query}%"
        c.execute(
            """
            SELECT * FROM translations
            WHERE (key LIKE ? OR translated_value LIKE ? OR original_value LIKE ?)
            AND target_language = ?
            ORDER BY usage_count DESC
            LIMIT ?
        """,
            (search, search, search, target_lang, limit),
        )
        return c.fetchall()

    def get_all_translations(self, file_name="", mod_name=""):
        """Получить все переводы с фильтрами"""
        c = self.conn.cursor()
        if file_name:
            c.execute("SELECT * FROM translations WHERE file_name = ? ORDER BY key", (file_name,))
        elif mod_name:
            c.execute("SELECT * FROM translations WHERE mod_name = ? ORDER BY key", (mod_name,))
        else:
            c.execute("SELECT * FROM translations ORDER BY key")
        return c.fetchall()

    def bulk_add_translations(
        self, entries, file_name="", mod_name="", source_lang="English", target_lang=None
    ):
        """Массовое добавление переводов"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        now = datetime.now().isoformat()

        for entry in entries:
            key = entry.get("key", "")
            original = entry.get("original_value", "")
            translated = entry.get("value", "")

            c.execute(
                """
                INSERT INTO translations (key, original_value, translated_value, file_name, mod_name,
                                         source_language, target_language, last_used, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key, source_language, target_language, file_name)
                DO UPDATE SET
                    translated_value = excluded.translated_value,
                    last_used = ?,
                    updated_at = ?,
                    usage_count = usage_count + 1
        """,
                (
                    key,
                    original,
                    translated,
                    file_name,
                    mod_name,
                    source_lang,
                    target_lang,
                    now,
                    now,
                    now,
                    now,
                ),
            )

        self.conn.commit()

    def apply_glossary_to_text(self, text: str, target_language: str = None) -> str:
        """
        Применяет глоссарий к тексту.

        Заменяет термины в тексте на переводы из глоссария.
        Использует GlossaryManager для применения с учётом морфологии и защиты XML-тегов.
        Сначала импортирует термины из БД в GlossaryManager.

        Args:
            text: Исходный текст
            target_language: Язык (если None, используется target_language экземпляра)

        Returns:
            Текст с применёнными терминами глоссария
        """
        if target_language is None:
            target_language = self.target_language

        try:
            from translation.glossary_manager import GlossaryManager
            lang_code = get_lang_code_from_name(target_language)
            glossary_dir = str(Path(__file__).parent / "data_storage" / lang_code / "glossary")
            manager = GlossaryManager(glossary_dir=glossary_dir, target_lang=target_language)
            manager.import_from_db(self)
            return manager.apply_to_text(text)
        except Exception as e:
            logger.debug(f"Не удалось применить глоссарий к тексту: {e}")
            return text

    def get_stats(self):
        """Получить статистику базы данных"""
        c = self.conn.cursor()
        stats = {}

        c.execute("SELECT COUNT(*) FROM translations")
        stats["total_translations"] = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT file_name) FROM translations")
        stats["total_files"] = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT mod_name) FROM translations")
        stats["total_mods"] = c.fetchone()[0]

        c.execute("SELECT SUM(usage_count) FROM translations")
        stats["total_usage"] = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(*) FROM glossary")
        stats["glossary_terms"] = c.fetchone()[0]

        return stats

    def _resolve_target_language(self, target_language=None):
        """Разрешает язык: если None, использует target_language экземпляра"""
        if target_language is None:
            return self.target_language
        return target_language

    def _get_language_filters(self, target_language=None):
        """Возвращает список значений для фильтрации по языку (поддержка разных форматов)"""
        lang = self._resolve_target_language(target_language)
        lang_lower = lang.lower()
        lang_code = get_lang_code_from_name(lang)
        return (lang, lang_code, lang_lower)

    def get_all_categories(self, target_language=None):
        """Получить все категории глоссария"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        c.execute(
            "SELECT DISTINCT category FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ?",
            (lang, lang_code, lang_lower)
        )
        return [row[0] for row in c.fetchall()]

    def get_all_glossary(self, target_language=None):
        """Получить все термины глоссария"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        c.execute(
            "SELECT * FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ? ORDER BY term",
            (lang, lang_code, lang_lower)
        )
        return c.fetchall()

    def get_glossary_total_count(self, target_language=None, category=None):
        """Получить общее количество терминов в глоссарии"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        if category:
            c.execute(
                "SELECT COUNT(*) FROM glossary WHERE (target_language = ? OR target_language = ? OR target_language = ?) AND category = ?",
                (lang, lang_code, lang_lower, category)
            )
        else:
            c.execute(
                "SELECT COUNT(*) FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ?",
                (lang, lang_code, lang_lower)
            )
        return c.fetchone()[0]

    def get_glossary_total_count_by_confidence(self, confidence=None, category=None, target_language=None):
        """Получить количество терминов по уверенности (для совместимости)"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        if category:
            c.execute(
                "SELECT COUNT(*) FROM glossary WHERE (target_language = ? OR target_language = ? OR target_language = ?) AND category = ?",
                (lang, lang_code, lang_lower, category)
            )
        else:
            c.execute(
                "SELECT COUNT(*) FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ?",
                (lang, lang_code, lang_lower)
            )
        return c.fetchone()[0]

    def get_glossary_by_confidence(self, confidence, category=None, limit=100, offset=0, target_language=None):
        """Получить термины по уверенности (для совместимости)"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        if category:
            c.execute(
                "SELECT * FROM glossary WHERE (target_language = ? OR target_language = ? OR target_language = ?) AND category = ? ORDER BY term LIMIT ? OFFSET ?",
                (lang, lang_code, lang_lower, category, limit, offset)
            )
        else:
            c.execute(
                "SELECT * FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ? ORDER BY term LIMIT ? OFFSET ?",
                (lang, lang_code, lang_lower, limit, offset)
            )
        return c.fetchall()

    def get_glossary_by_category(self, category, limit=100, offset=0, target_language=None):
        """Получить термины по категории с пагинацией"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        c.execute(
            "SELECT * FROM glossary WHERE (target_language = ? OR target_language = ? OR target_language = ?) AND category = ? ORDER BY term LIMIT ? OFFSET ?",
            (lang, lang_code, lang_lower, category, limit, offset)
        )
        return c.fetchall()

    def get_all_glossary_paginated(self, limit=100, offset=0, target_language=None):
        """Получить все термины глоссария с пагинацией"""
        c = self.conn.cursor()
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        c.execute(
            "SELECT * FROM glossary WHERE target_language = ? OR target_language = ? OR target_language = ? ORDER BY term LIMIT ? OFFSET ?",
            (lang, lang_code, lang_lower, limit, offset)
        )
        return c.fetchall()

    def search_glossary(self, query, target_language=None, mod_name=None, category=None):
        """Поиск терминов в глоссарии"""
        c = self.conn.cursor()
        search = f"%{query}%"
        lang, lang_code, lang_lower = self._get_language_filters(target_language)
        params = [lang, lang_code, lang_lower, search, search, search]
        sql = """
            SELECT * FROM glossary
            WHERE (target_language = ? OR target_language = ? OR target_language = ?)
            AND (term LIKE ? OR translation LIKE ? OR description LIKE ?)
        """
        if category and category != "Все":
            sql += " AND category = ?"
            params.append(category)
        if mod_name:
            sql += " AND mod_name = ?"
            params.append(mod_name)
        sql += " ORDER BY term"
        c.execute(sql, params)
        return c.fetchall()

    def add_glossary_term(self, term, translation, category, description, target_language=None, mod_name=""):
        """Добавить термин в глоссарий"""
        if target_language is None:
            target_language = self.target_language
        c = self.conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO glossary (term, translation, category, description, target_language, mod_name) VALUES (?, ?, ?, ?, ?, ?)",
            (term, translation, category, description, target_language, mod_name)
        )
        self.conn.commit()
        self._sync_glossary_to_json(target_language)

    def rename_glossary_term(self, old_term, new_term, translation, category, description, target_language=None):
        """Переименовать термин в глоссарии"""
        if target_language is None:
            target_language = self.target_language
        c = self.conn.cursor()
        c.execute(
            "UPDATE glossary SET term = ?, translation = ?, category = ?, description = ? WHERE term = ? AND target_language = ?",
            (new_term, translation, category, description, old_term, target_language)
        )
        self.conn.commit()
        self._sync_glossary_to_json(target_language)

    def remove_glossary_term(self, term, target_language=None):
        """Удалить термин из глоссария"""
        if target_language is None:
            target_language = self.target_language
        c = self.conn.cursor()
        c.execute("DELETE FROM glossary WHERE term = ? AND target_language = ?", (term, target_language))
        self.conn.commit()
        self._sync_glossary_to_json(target_language)

    def _split_glossary_by_categories(self, target_language=None):
        if target_language is None:
            target_language = self.target_language

        c = self.conn.cursor()
        c.execute("SELECT term, translation FROM glossary WHERE target_language = ? AND category != 'seed'", (target_language,))
        entries = {row[0]: row[1] for row in c.fetchall()}

        if len(entries) < MAX_GLOSSARY_SIZE:
            return

        categories: dict[str, dict[str, str]] = {}
        uncategorized: dict[str, str] = {}

        for original, translation in entries.items():
            category = determine_category(original)
            if category:
                if category not in categories:
                    categories[category] = {}
                categories[category][original] = translation
            else:
                uncategorized[original] = translation

        for category, cat_entries in categories.items():
            self._save_category_to_file(category, cat_entries)
        if uncategorized:
            self._save_category_to_file("uncategorized", uncategorized)
        self._rebuild_index()

    def _save_category_to_file(self, category: str, entries: dict[str, str]) -> None:
        """Сохраняет категорию в отдельный файл."""
        if not entries:
            return
        import json
        filepath = os.path.join(self.glossary_dir, f"{category}.json")
        data = {"entries": entries, "source": category, "auto_split": True}
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Категория сохранена в {filepath} ({len(entries)} терминов)")
        except Exception as e:
            logger.error(f"Ошибка сохранения категории {category}: {e}")

    def _rebuild_index(self) -> None:
        """Пересобирает индекс файлов глоссария."""
        import json
        index_path = os.path.join(self.glossary_dir, "glossary_index.json")
        files = {}
        for filename in os.listdir(self.glossary_dir):
            if filename.endswith(".json") and filename != "glossary_index.json":
                files[filename] = filename.replace(".json", "")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"files": files}, f, ensure_ascii=False, indent=2)

    def _sync_glossary_to_json(self, target_language=None):
        """
        Синхронизирует глоссарий с JSON-файлами.

        Экспортирует термины из базы данных SQLite:
        - user.json: пользовательские термины (category != 'seed' и не категория-файл)
        - seed.json: seed-термины (только те, что не удалось категоризировать)
        - категории: weapons.json, materials.json и т.д. (при glossary_auto_split=True)
        """
        if target_language is None:
            target_language = self.target_language
        import json
        from translation.glossary_utils import determine_category

        c = self.conn.cursor()

        # Get all non-seed entries grouped by category
        c.execute("SELECT term, translation, category FROM glossary WHERE target_language = ? AND category != 'seed'", (target_language,))
        entries_by_category: dict[str, dict[str, str]] = {}
        for row in c.fetchall():
            category = row[2]
            if category not in entries_by_category:
                entries_by_category[category] = {}
            entries_by_category[category][row[0]] = row[1]

        # Get seed entries and auto-categorize them
        c.execute("SELECT term, translation FROM glossary WHERE target_language = ? AND category = 'seed'", (target_language,))
        seed_entries_by_category: dict[str, dict[str, str]] = {}
        uncategorized_seed_entries: dict[str, str] = {}
        
        for row in c.fetchall():
            term, translation = row[0], row[1]
            category = determine_category(term)
            if category:
                if category not in seed_entries_by_category:
                    seed_entries_by_category[category] = {}
                seed_entries_by_category[category][term] = translation
            else:
                uncategorized_seed_entries[term] = translation

        auto_split = True
        try:
            from config.config_manager import get_config_manager
            auto_split = get_config_manager().get("glossary_auto_split", True)
        except Exception:
            pass

        # Ensure glossary directory exists
        os.makedirs(self.glossary_dir, exist_ok=True)

        files_to_save: list[tuple[str, dict[str, str]]] = []

        if auto_split:
            # Save each category to its own file (including auto-categorized seed entries)
            for category, entries in entries_by_category.items():
                if entries:
                    files_to_save.append((category, entries))
            for category, entries in seed_entries_by_category.items():
                if entries:
                    files_to_save.append((category, entries))
            # Save uncategorized seed entries
            if uncategorized_seed_entries:
                files_to_save.append(("seed", uncategorized_seed_entries))
        else:
            # Save all non-seed entries to user.json
            user_entries = {}
            for cat_entries in entries_by_category.values():
                user_entries.update(cat_entries)
            for cat_entries in seed_entries_by_category.values():
                user_entries.update(cat_entries)
            if user_entries:
                files_to_save.append(("user", user_entries))
            # Save uncategorized seed entries
            if uncategorized_seed_entries:
                files_to_save.append(("seed", uncategorized_seed_entries))

        # Save all files
        for name, entries in files_to_save:
            json_path = os.path.join(self.glossary_dir, f"{name}.json")
            data = {
                "entries": entries,
                "source": name,
                "auto_split": True if auto_split else False,
            }
            if auto_split:
                data["auto_split"] = True
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug(f"Глоссарий сохранен в {json_path} ({len(entries)} терминов)")
            except Exception as e:
                logger.error(f"Ошибка сохранения глоссария в JSON: {e}")

        # Rebuild glossary_index.json
        self._rebuild_glossary_index_for_dir(self.glossary_dir)

    def recategorize_seed_entries(self):
        """
        Перекатегоризует seed-термины в базе данных на основе имени термина.
        Обновляет категорию для всех терминов с category='seed'.
        """
        from translation.glossary_utils import determine_category
        
        c = self.conn.cursor()
        
        # Get all seed entries
        c.execute("SELECT id, term FROM glossary WHERE target_language = ? AND category = 'seed'", (self.target_language,))
        seed_entries = c.fetchall()
        
        updated_count = 0
        for entry in seed_entries:
            entry_id = entry[0] if hasattr(entry, '__getitem__') else getattr(entry, 'id', None)
            term = entry[1] if hasattr(entry, '__getitem__') else getattr(entry, 'term', None)
            
            if entry_id is None or term is None:
                continue
                
            new_category = determine_category(term)
            if new_category:
                c.execute("UPDATE glossary SET category = ? WHERE id = ?", (new_category, entry_id))
                updated_count += 1
        
        if updated_count > 0:
            self.conn.commit()
            logger.info(f"Перекатегоризовано {updated_count} seed-терминов")
        
        return updated_count

    def _rebuild_glossary_index_for_dir(self, glossary_dir: str):
        """Пересобирает индекс файлов глоссария для указанной директории."""
        import json
        index_path = os.path.join(glossary_dir, "glossary_index.json")
        files = {}
        try:
            for filename in os.listdir(glossary_dir):
                if filename.endswith(".json") and filename != "glossary_index.json":
                    category = filename.replace(".json", "")
                    files[filename] = category
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump({"files": files}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка пересоздания индекса глоссария: {e}")

    def sync_glossary_to_all_languages(self, source_language: str = "Russian"):
        """
        Синхронизирует глоссарий со всеми языками на основе источника.

        Для каждого языка копирует категории и термины из источника,
        создавая структуру файлов глоссария.

        Args:
            source_language: Язык-источник для копирования категорий
        """
        import json

        c = self.conn.cursor()

        # Получаем все языки
        c.execute("SELECT DISTINCT target_language FROM glossary WHERE target_language IS NOT NULL")
        languages = [row[0] for row in c.fetchall()]

        # Получаем категории из источника
        lang_code = get_lang_code_from_name(source_language)
        c.execute(
            "SELECT DISTINCT category FROM glossary WHERE target_language = ? OR target_language = ?",
            (source_language, lang_code)
        )
        categories = [row[0] for row in c.fetchall()]

        for lang in languages:
            lang_code = get_lang_code_from_name(lang)
            glossary_dir = str(Path(__file__).parent / "data_storage" / lang_code / "glossary")
            os.makedirs(glossary_dir, exist_ok=True)

            # Получаем термины для этого языка
            c.execute(
                "SELECT term, translation, category FROM glossary WHERE target_language = ? OR target_language = ?",
                (lang, lang_code)
            )

            entries_by_category: dict[str, dict[str, str]] = {}
            for row in c.fetchall():
                category = row[2] or "general"
                if category not in entries_by_category:
                    entries_by_category[category] = {}
                entries_by_category[category][row[0]] = row[1]

            # Сохраняем термины по категориям
            for category, entries in entries_by_category.items():
                json_path = os.path.join(glossary_dir, f"{category}.json")
                data = {
                    "entries": entries,
                    "source": category,
                    "auto_split": True,
                    "synced_at": datetime.now().isoformat()
                }
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            # Пересобираем индекс
            self._rebuild_glossary_index_for_dir(glossary_dir)
            logger.info(f"Глоссарий синхронизирован для языка: {lang}")

    def initialize_glossary_for_all_languages(self):
        """
        Создаёт структуру глоссария для всех языков на основе категорий из базы данных.

        Для каждого языка создаёт пустые JSON-файлы категорий, если они отсутствуют.
        Это обеспечивает наличие файлов глоссария для всех поддерживаемых языков.
        """
        from pathlib import Path
        import json

        # Получаем все доступные языки из базы данных
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT target_language FROM glossary WHERE target_language IS NOT NULL")
        languages = [row[0] for row in c.fetchall()]

        # Если нет языков в базе, используем стандартные
        if not languages:
            languages = ["Russian", "English", "German", "French", "Spanish"]

        # Получаем все категории из базы данных
        c.execute("SELECT DISTINCT category FROM glossary WHERE category IS NOT NULL")
        categories = [row[0] for row in c.fetchall()]

        # Стандартные категории, если нет в базе
        if not categories:
            categories = ["game", "seed", "user", "auto", "general", "materials", "weapons",
                          "armor", "clothing", "plants", "interface", "names", "biomes",
                          "body_parts", "factions"]

        for lang in languages:
            lang_code = get_lang_code_from_name(lang)
            glossary_dir = str(Path(__file__).parent / "data_storage" / lang_code / "glossary")

            # Создаём директорию если её нет
            os.makedirs(glossary_dir, exist_ok=True)

            # Создаём category_index.json для отслеживания категорий
            category_index_path = os.path.join(glossary_dir, "category_index.json")
            if not os.path.exists(category_index_path):
                category_data = {"categories": categories, "created_at": datetime.now().isoformat()}
                with open(category_index_path, "w", encoding="utf-8") as f:
                    json.dump(category_data, f, ensure_ascii=False, indent=2)

            # Создаём пустые JSON-файлы для каждой категории если они отсутствуют
            for category in categories:
                json_path = os.path.join(glossary_dir, f"{category}.json")
                if not os.path.exists(json_path):
                    data = {
                        "entries": {},
                        "source": category,
                        "auto_split": True,
                        "created_at": datetime.now().isoformat()
                    }
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

            # Пересобираем индекс
            self._rebuild_glossary_index_for_dir(glossary_dir)

    # ===== ИСТОРИЯ ВЕРСИЙ =====

    def save_file_version(self, file_path, entries, version=None):
        """Сохранить версию файла"""
        c = self.conn.cursor()

        if version is None:
            c.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM file_history WHERE file_path = ?",
                (file_path,),
            )
            version = c.fetchone()[0]

        import json

        content = json.dumps(entries, ensure_ascii=False)
        entries_count = len(entries)
        translated_count = sum(1 for e in entries if e.get("value", "").strip())

        c.execute(
            """
            INSERT OR REPLACE INTO file_history (file_path, version, content, entries_count, translated_count)
            VALUES (?, ?, ?, ?, ?)
        """,
            (file_path, version, content, entries_count, translated_count),
        )
        self.conn.commit()
        return version

    def get_file_versions(self, file_path):
        """Получить список версий файла"""
        c = self.conn.cursor()
        c.execute(
            """
            SELECT version, entries_count, translated_count, created_at
            FROM file_history
            WHERE file_path = ?
            ORDER BY version DESC
        """,
            (file_path,),
        )
        return c.fetchall()

    def get_file_version(self, file_path, version):
        """Получить конкретную версию файла"""
        c = self.conn.cursor()
        import json

        c.execute(
            """
            SELECT content, entries_count, translated_count, created_at
            FROM file_history
            WHERE file_path = ? AND version = ?
        """,
            (file_path, version),
        )
        row = c.fetchone()
        if row:
            return {
                "entries": json.loads(row["content"]),
                "entries_count": row["entries_count"],
                "translated_count": row["translated_count"],
                "created_at": row["created_at"],
            }
        return None

    def delete_file_version(self, file_path, version):
        """Удалить версию файла"""
        c = self.conn.cursor()
        c.execute(
            "DELETE FROM file_history WHERE file_path = ? AND version = ?", (file_path, version)
        )
        self.conn.commit()

    # ===== АВТОПРЕДЛОЖЕНИЯ =====

    def get_suggestion(self, key, target_lang=None):
        """Получить лучшее предложение перевода для ключа"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        c.execute(
            """
            SELECT * FROM suggestions
            WHERE key = ? AND target_language = ?
            ORDER BY confidence DESC
            LIMIT 1
        """,
            (key, target_lang),
        )
        return c.fetchone()

    def add_suggestion(self, key, value, confidence=0.5, source="database", target_lang=None):
        """Добавить предложение перевода"""
        if target_lang is None:
            target_lang = self.target_language
        c = self.conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO suggestions (key, suggested_value, confidence, source, target_language)
            VALUES (?, ?, ?, ?, ?)
        """,
            (key, value, confidence, source, target_lang),
        )
        self.conn.commit()

    def generate_suggestions(self):
        """Сгенерировать автопредложения на основе существующих переводов"""
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO suggestions (key, suggested_value, confidence, source, target_language)
            SELECT
                key,
                translated_value as suggested_value,
                CASE
                    WHEN MAX(usage_count) OVER (PARTITION BY target_language) > 0
                    THEN CAST(usage_count AS REAL) / MAX(usage_count) OVER (PARTITION BY target_language)
                    ELSE 0.0
                END as confidence,
                'database' as source,
                target_language
            FROM translations
            WHERE usage_count > 0
            GROUP BY key, target_language
        """)
        self.conn.commit()

    def get_suggestions_for_entries(self, entries, target_lang=None):
        """Получить предложения для списка записей"""
        if target_lang is None:
            target_lang = self.target_language
        suggestions = {}
        for entry in entries:
            key = entry.get("key", "")
            # 1. Прямое совпадение
            s = self.get_suggestion(key, target_lang)
            if s:
                suggestions[key] = {
                    "value": s["suggested_value"],
                    "confidence": s["confidence"],
                    "source": s["source"],
                }
                continue

            # 2. Похожие переводы
            similar = self.find_similar_translations(key, target_lang, limit=3)
            if similar:
                # Берём самый популярный
                best = similar[0]
                suggestions[key] = {
                    "value": best["translated_value"],
                    "confidence": 0.3,
                    "source": "similar",
                }

        return suggestions

    def close(self):
        """Закрыть соединение. Безопасно вызывать множество раз."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            finally:
                self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        """Деструктор: безопасно закрывает соединение при сборке мусора.

        Использует try/except вокруг close() чтобы пережить ситуацию,
        когда sqlite3 или другие зависимости уже удалены сборщиком мусора.
        """
        conn = getattr(self, 'conn', None)
        if conn is not None:
            try:
                conn.close()
            except (AttributeError, TypeError):
                # sqlite3 модуль или объект Connection уже удалены — игнорируем
                pass
            except Exception:
                pass


# Синглтон для удобства
_db_instances = {}


def get_translation_db(target_language: str = None):
    """Получить экземпляр базы данных (синглтон по языку)"""
    global _db_instances

    target_language = _resolve_target_language(target_language)

    if target_language not in _db_instances:
        _db_instances[target_language] = TranslationDatabase(target_language=target_language)

    return _db_instances[target_language]


def clear_db_instances():
    """Очистить все экземпляры БД (полезно для тестирования)"""
    global _db_instances
    for db in _db_instances.values():
        try:
            db.close()
        except Exception:
            pass
    _db_instances = {}
