import os
import sqlite3
import threading

from loguru import logger
from lxml import etree


class AnchorManager:
    _instance = None
    _initialized = False

    def __new__(cls, db_path=None):
        """Синглтон: один экземпляр на весь процесс"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path=None):
        # Избегаем повторной инициализации
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Путь к БД: приоритет переданного, затем конфиг, затем default
        if db_path is None:
            try:
                import json
                config_path = os.path.join(os.path.dirname(__file__), "..", "gui_config.json")
                if os.path.exists(config_path):
                    with open(config_path, encoding="utf-8") as f:
                        config = json.load(f)
                        db_path = config.get("anchor_db_path", "translation_anchors.db")
                else:
                    db_path = "translation_anchors.db"
            except Exception:
                db_path = "translation_anchors.db"

        self.db_path = db_path
        # check_same_thread=False для доступа из нескольких потоков (например, из worker'ов)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()  # Защита concurrent access
        self._prepare_db()
        self._core_loaded = False  # Флаг: загружены ли Core переводы
        self._initialized = True

    @classmethod
    def get_instance(cls, db_path=None) -> "AnchorManager":
        """
        Возвращает синглтон-экземпляр, инициализируя его при необходимости.
        Параметр db_path учитывается только при первом вызове.
        """
        if cls._instance is None:
            cls._instance = cls(db_path)
        return cls._instance

    @classmethod
    def initialize_with_game_path(cls, game_path, target_lang="Russian", db_path=None):
        """
        Инициализирует AnchorManager и сканирует официальные переводы Core игры.

        Args:
            game_path: Путь к папке RimWorld (например, C:/Games/RimWorld)
            target_lang: Целевой язык перевода ('Russian', 'Ukrainian' и т.д.)
            db_path: Путь к файлу БД (опционально)

        Returns:
            AnchorManager: Инициализированный экземпляр
        """
        manager = cls.get_instance(db_path)
        count = manager.scan_core_translations(game_path, target_lang)
        logger.info(
            f"AnchorManager: загружено {count} официальных переводов из Core ({target_lang})"
        )
        return manager

    def _prepare_db(self):
        # Расширенная схема: original + context (DefType) + translation + source + priority
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS anchors (
                original TEXT NOT NULL,
                context TEXT DEFAULT '',
                translation TEXT NOT NULL,
                source_file TEXT,
                priority INTEGER DEFAULT 3,
                PRIMARY KEY (original, context)
            )
        """)
        self.conn.commit()
        # Миграция: добавляем column context если его нет (старые базы)
        try:
            self.conn.execute("ALTER TABLE anchors ADD COLUMN context TEXT DEFAULT ''")
            self.conn.commit()
        except Exception:
            pass
        # Существующие строки с NULL контекстом или без значения приводим к пустой строке
        try:
            self.conn.execute("UPDATE anchors SET context = '' WHERE context IS NULL OR context = ''")
            self.conn.commit()
        except Exception:
            pass

    def scan_translations(self, path):
        """Сканирует папку DefInjected на наличие комментариев EN"""
        for root, _, files in os.walk(path):
            for file in files:
                if not file.endswith(".xml"): continue
                self._index_file(os.path.join(root, file))

    def _index_file(self, file_path):
        try:
            parser = etree.XMLParser(recover=True, remove_comments=False)
            tree = etree.parse(file_path, parser)
            # Ищем комментарии и следующие за ними теги
            for comment in tree.xpath("//comment()"):
                if comment.text:
                    text = comment.text.strip()
                    if text.startswith("EN:"):
                        original = text[3:].strip()
                        node = comment.getnext()
                        if node is not None and node.text:
                            # Извлекаем DefType из тега как контекст
                            context = ""
                            if isinstance(node.tag, str) and '_' in node.tag:
                                context = node.tag.split('_', 1)[0]
                            self.add_anchor(
                                original=original,
                                translation=node.text.strip(),
                                source=file_path,
                                priority=2,
                                context=context
                            )
        except Exception:
            pass

    def add_anchor(self, original, translation, source="manual", priority=None, context=""):
        """
        Добавляет якорь перевода с приоритетом и контекстом (DefType).

        Args:
            original: Оригинальный английский текст
            translation: Перевод
            source: Источник перевода ("manual", "Core/...", etc.)
            priority: Приоритет (1-4, где 1-highest)
            context: Контекст — обычно DefType (ThingDef, RecipeDef, FactionDef, ...)
                     Приводится к нижнему регистру для case-insensitive сравнения.
        """
        # Нормализуем контекст: к нижнему регистру, убираем пробелы
        context = (context or "").lower().strip()

        if priority is None:
            if source == "manual":
                priority = 1
            elif source.startswith("Core/"):
                priority = 3
            else:
                priority = 2

        self.conn.execute(
            "INSERT OR REPLACE INTO anchors VALUES (?, ?, ?, ?, ?)",
            (original, context, translation, source, priority)
        )
        self.conn.commit()

    def _try_auto_load_core(self):
        """Автоматически загружает Core переводы при первом использовании, если есть game_path в конфиге."""
        # Пытаемся загрузить только один раз (флаг _core_loaded проверяется в find)
        try:
            config_paths = [
                "gui_config.json",
                os.path.join(os.path.dirname(__file__), "..", "gui_config.json"),
                os.path.join(os.path.expanduser("~"), ".rimworld_translator", "config.json"),
            ]
            for conf_path in config_paths:
                if os.path.exists(conf_path):
                    import json
                    with open(conf_path, encoding="utf-8") as f:
                        config = json.load(f)
                    game_path = config.get("game_path", "")
                    target_lang = config.get("target_language", "Russian")
                    if game_path and os.path.exists(game_path):
                        count = self.scan_core_translations(game_path, target_lang)
                        log = logger
                        if count > 0:
                            log.info(f"✅ Загружено {count} Core переводов из {game_path} ({target_lang})")
                        else:
                            log.debug(f"Core переводы не найдены (game_path: {game_path})")
                        return
        except Exception as e:
            logger.debug(f"Auto-load Core translations skipped: {e}")

    def find(self, original: str, context: str = "") -> str | None:
        """
        Находит перевод для оригинального текста с учётом контекста (DefType).
        Comparison is case-insensitive.

        Args:
            original: Оригинальный английский текст
            context: Контекст (DefType, например "ThingDef", "RecipeDef")

        Returns:
            Перевод или None
        """
        with self._lock:
            if not self._core_loaded:
                self._try_auto_load_core()
                self._core_loaded = True

            ctx_norm = (context or "").lower().strip()

            res = self.conn.execute("""
                SELECT translation, priority, context FROM anchors
                WHERE original = ? AND (LOWER(context) = ? OR context = '')
                ORDER BY
                    CASE WHEN LOWER(context) = ? THEN 0 ELSE 1 END,
                    priority ASC
                LIMIT 1
            """, (original, ctx_norm, ctx_norm)).fetchone()

            if res:
                translation, priority, found_context = res
                if logger:
                    logger.debug(
                        f"✅ EN якорь найден (ctx={found_context}, priority={priority}): "
                        f"'{original[:50]}' -> '{translation[:50]}'"
                    )
                return translation
            return None

    def scan_core_translations(self, game_path, target_lang="Russian"):
        """
        Сканирует стандартные переводы Core игры и добавляет все стандартные термины в базу якорей.
        Сохраняет контекст (DefType) из папки (ThingDef, RecipeDef, FactionDef, ...).

        Args:
            game_path: путь к папке RimWorld
            target_lang: целевой язык перевода
        """
        en_path = os.path.join(game_path, "Data/Core/Languages/English/DefInjected")
        target_path = os.path.join(game_path, f"Data/Core/Languages/{target_lang}/DefInjected")

        if not os.path.exists(en_path) or not os.path.exists(target_path):
            return 0

        count = 0
        parser = etree.XMLParser(recover=True)

        for root_dir, _, files in os.walk(en_path):
            for filename in files:
                if not filename.endswith(".xml"):
                    continue

                relative_path = os.path.relpath(os.path.join(root_dir, filename), en_path)
                en_file = os.path.join(en_path, relative_path)
                target_file = os.path.join(target_path, relative_path)

                if not os.path.exists(target_file):
                    continue

                # Извлекаем контекст (DefType) из пути: DefInjected/<DefType>/...
                # Например: "ThingDef/Weapon/SomeFile.xml" -> context = "ThingDef"
                parts = relative_path.split(os.sep)
                context = parts[0] if parts else ""

                try:
                    en_tree = etree.parse(en_file, parser)
                    target_tree = etree.parse(target_file, parser)

                    target_map = {}
                    for node in target_tree.getroot():
                        if hasattr(node, 'tag') and node.text:
                            target_map[node.tag] = node.text.strip()

                    for node in en_tree.getroot():
                        if hasattr(node, 'tag') and node.text:
                            en_text = node.text.strip()
                            if not en_text:
                                continue
                            if node.tag in target_map:
                                self.add_anchor(
                                    original=en_text,
                                    translation=target_map[node.tag],
                                    source=f"Core/{relative_path}",
                                    priority=3,
                                    context=context
                                )
                                count += 1

                except Exception:
                    continue

        self.conn.commit()
        return count
