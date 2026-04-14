# translation_db.py — База данных переводов (SQLite)
"""
Централизованная база данных переводов для подхвата в редакторе.

Хранит:
- Переведённые пары ключ → значение из всех обработанных файлов
- Глоссарий терминов (оригинал → перевод)
- Историю версий каждого файла
- Статистику по переводам
"""

import sqlite3
from datetime import datetime

DB_PATH = "translations.db"


class TranslationDatabase:
    """База данных переводов"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Подключиться к базе данных"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Включаем WAL для лучшей конкурентности
        self.conn.execute("PRAGMA journal_mode=WAL")

    def _create_tables(self):
        """Создать таблицы если не существуют"""
        c = self.conn.cursor()

        # Основная таблица переводов
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

        # Глоссарий терминов
        c.execute("""
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL UNIQUE,
                translation TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                description TEXT DEFAULT '',
                usage_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_suggestions_key ON suggestions(key, target_language)"
        )
        c.execute("CREATE INDEX IF NOT EXISTS idx_file_history_path ON file_history(file_path)")

        self.conn.commit()

        # Добавляем стандартные термины в глоссарий если пусто
        self._seed_glossary()

    def _seed_glossary(self):
        """Добавить стандартные термины RimWorld"""
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM glossary")
        if c.fetchone()[0] == 0:
            glossary_terms = [
                # RimWorld термины
                ("Colonist", "Колонист", "game", "Житель колонии"),
                ("Pawn", "Персонаж", "game", "Игровой персонаж (пешка)"),
                ("Workbench", "Верстак", "game", "Рабочее место"),
                ("Research", "Исследование", "game", "Научное исследование"),
                ("Manufacturing", "Производство", "game", "Крафт/создание"),
                ("Storage", "Склад", "game", "Место хранения"),
                ("Bedroom", "Спальня", "game", "Комната для сна"),
                ("Hospital", "Больница", "game", "Медицинское помещение"),
                ("Prison", "Тюрьма", "game", "Тюремное помещение"),
                ("Barracks", "Казарма", "game", "Общая спальня"),
                ("Workshop", "Мастерская", "game", "Рабочая комната"),
                ("Dining", "Столовая", "game", "Помещение для еды"),
                ("Recreation", "Отдых", "game", "Зона отдыха"),
                ("Raid", "Рейд", "game", "Вражеское нападение"),
                ("Caravan", "Караван", "game", "Группа путешественников"),
                ("Trade", "Торговля", "game", "Обмен товарами"),
                ("Disease", "Болезнь", "medical", "Заболевание"),
                ("Injury", "Рана", "medical", "Травма/повреждение"),
                ("Treatment", "Лечение", "medical", "Медицинская помощь"),
                ("Surgery", "Операция", "medical", "Хирургическое вмешательство"),
                ("Infection", "Инфекция", "medical", "Заражение"),
                ("Pain", "Боль", "medical", "Болевые ощущения"),
                ("Consciousness", "Сознание", "medical", "Уровень сознания"),
                ("Blood", "Кровь", "medical", "Потеря крови"),
                ("Metal", "Металл", "material", "Ресурс металл"),
                ("Wood", "Дерево", "material", "Ресурс древесина"),
                ("Cloth", "Ткань", "material", "Ресурс ткань"),
                ("Steel", "Сталь", "material", "Ресурс сталь"),
                ("Plasteel", "Пласталь", "material", "Продвинутый материал"),
                ("Gold", "Золото", "material", "Ресурс золото"),
                ("Silver", "Серебро", "material", "Ресурс серебро"),
                ("Component", "Компонент", "material", "Базовый компонент"),
                ("Advanced Component", "Продвинутый компонент", "material", "Улучшенный компонент"),
                ("Quality", "Качество", "general", "Уровень качества предмета"),
                ("Awful", "Ужасное", "quality", "Самое низкое качество"),
                ("Poor", "Плохое", "quality", "Низкое качество"),
                ("Normal", "Нормальное", "quality", "Среднее качество"),
                ("Good", "Хорошее", "quality", "Высокое качество"),
                ("Excellent", "Отличное", "quality", "Очень высокое качество"),
                ("Masterwork", "Шедевр", "quality", "Высочайшее качество"),
                ("Legendary", "Легендарное", "quality", "Мифическое качество"),
                ("Fire", "Огонь", "general", "Пламя/пожар"),
                ("Flood", "Наводнение", "general", "Затопление"),
                ("Drought", "Засуха", "general", "Отсутствие дождей"),
                ("Heat", "Жара", "general", "Высокая температура"),
                ("Cold", "Холод", "general", "Низкая температура"),
                ("Food", "Еда", "general", "Пища/продукты"),
                ("Meal", "Блюдо", "general", "Приготовленная еда"),
                ("Raw", "Сырой", "general", "Необработанный"),
                ("Cooked", "Приготовленный", "general", "Обработанный готовкой"),
                ("Rotting", "Гниение", "general", "Процесс порчи"),
                ("Fresh", "Свежий", "general", "Неиспорченный"),
                ("Mood", "Настроение", "general", "Психическое состояние"),
                ("Opinion", "Мнение", "general", "Отношение к другому"),
                ("Relationship", "Отношения", "general", "Связь между персонаами"),
                ("Skill", "Навык", "general", "Умение персонажа"),
                ("Passion", "Призвание", "general", "Интерес к навыку"),
                ("Trait", "Черта", "general", "Особенность характера"),
                ("Apparel", "Одежда", "general", "Предметы одежды"),
                ("Weapon", "Оружие", "general", "Средство нападения"),
                ("Armor", "Броня", "general", "Защитное снаряжение"),
                ("Helmet", "Шлем", "general", "Защита головы"),
                ("Body", "Тело", "general", "Тело персонажа"),
                ("Head", "Голова", "general", "Голова персонажа"),
                ("Left", "Левый", "general", "Левая сторона"),
                ("Right", "Правый", "general", "Правая сторона"),
                ("Upper", "Верхний", "general", "Верхняя часть"),
                ("Lower", "Нижний", "general", "Нижняя часть"),
                ("Inside", "Внутри", "general", "Внутренняя часть"),
                ("Outside", "Снаружи", "general", "Внешняя часть"),
            ]
            for term, translation, category, description in glossary_terms:
                c.execute(
                    "INSERT OR IGNORE INTO glossary (term, translation, category, description) VALUES (?, ?, ?, ?)",
                    (term, translation, category, description),
                )
            self.conn.commit()

    # ===== ОСНОВНЫЕ ОПЕРАЦИИ =====

    def add_translation(
        self,
        key,
        original,
        translated,
        file_name="",
        mod_name="",
        source_lang="English",
        target_lang="Russian",
    ):
        """Добавить или обновить перевод"""
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

    def get_translation(self, key, source_lang="English", target_lang="Russian"):
        """Получить перевод по ключу"""
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

    def find_similar_translations(self, key, target_lang="Russian", limit=5):
        """Найти похожие переводы (частичное совпадение ключа)"""
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

    def search_translations(self, query, target_lang="Russian", limit=20):
        """Поиск переводов по ключу или значению"""
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
        self, entries, file_name="", mod_name="", source_lang="English", target_lang="Russian"
    ):
        """Массовое добавление переводов"""
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

    # ===== ГЛОССАРИЙ =====

    def add_glossary_term(self, term, translation, category="general", description=""):
        """Добавить термин в глоссарий"""
        c = self.conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO glossary (term, translation, category, description)
            VALUES (?, ?, ?, ?)
        """,
            (term, translation, category, description),
        )
        self.conn.commit()

    def get_glossary_term(self, term):
        """Получить перевод термина из глоссария"""
        c = self.conn.cursor()
        # Точное совпадение
        c.execute("SELECT * FROM glossary WHERE term = ?", (term,))
        row = c.fetchone()
        if row:
            return row

        # Частичное совпадение (case-insensitive)
        c.execute("SELECT * FROM glossary WHERE LOWER(term) = LOWER(?)", (term,))
        return c.fetchone()

    def search_glossary(self, query):
        """Поиск терминов в глоссарии"""
        c = self.conn.cursor()
        search = f"%{query}%"
        c.execute(
            """
            SELECT * FROM glossary
            WHERE term LIKE ? OR translation LIKE ? OR description LIKE ?
            ORDER BY usage_count DESC
        """,
            (search, search, search),
        )
        return c.fetchall()

    def get_all_glossary(self, category=None):
        """Получить все термины глоссария"""
        c = self.conn.cursor()
        if category:
            c.execute("SELECT * FROM glossary WHERE category = ? ORDER BY term", (category,))
        else:
            c.execute("SELECT * FROM glossary ORDER BY term")
        return c.fetchall()

    def apply_glossary_to_text(self, text):
        """Заменить термины в тексте переводами из глоссария"""
        result = text
        terms = self.get_all_glossary()
        # Сортируем по длине — сначала длинные термины
        terms.sort(key=lambda t: len(t["term"]), reverse=True)
        for term in terms:
            if term["term"].lower() in result.lower():
                # Заменяем только если термин стоит отдельно (не часть другого слова)
                import re

                pattern = re.compile(re.escape(term["term"]), re.IGNORECASE)
                result = pattern.sub(term["translation"], result)
        return result

    def remove_glossary_term(self, term):
        """Удалить термин из глоссария"""
        c = self.conn.cursor()
        c.execute("DELETE FROM glossary WHERE term = ?", (term,))
        self.conn.commit()

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

    def get_suggestion(self, key, target_lang="Russian"):
        """Получить лучшее предложение перевода для ключа"""
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

    def add_suggestion(self, key, value, confidence=0.5, source="database", target_lang="Russian"):
        """Добавить предложение перевода"""
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
        # Находим самые используемые переводы для каждого ключа
        c.execute("""
            INSERT OR REPLACE INTO suggestions (key, suggested_value, confidence, source, target_language)
            SELECT
                key,
                translated_value as suggested_value,
                MIN(usage_count * 1.0 / MAX(usage_count) OVER(), 1.0) as confidence,
                'database' as source,
                target_language
            FROM translations
            WHERE usage_count > 0
            GROUP BY key, target_language
            HAVING MAX(usage_count)
        """)
        self.conn.commit()

    def get_suggestions_for_entries(self, entries, target_lang="Russian"):
        """Получить предложения для списка записей"""
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
        """Закрыть соединение"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()


# Синглтон для удобства
_db_instance = None


def get_translation_db():
    """Получить экземпляр базы данных (синглтон)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TranslationDatabase()
    return _db_instance
