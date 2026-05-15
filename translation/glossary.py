# translation/glossary.py
"""
Глоссарий — пользовательские термины с приоритетом.

Позволяет задать собственные переводы для конкретных слов/фраз,
которые будут применяться перед автоматическим переводом.
"""

import json
import os
import re
from typing import Any

try:
    from utils.Morphy import RimWorldUniversalParser
    HAS_MORPHY = True
except ImportError:
    HAS_MORPHY = False


class Glossary:
    """
    Глоссарий переводов.

    Хранит пары оригинал->перевод и применяет их
    до/после автоматического перевода.

    Args:
        filepath: Путь к JSON-файлу глоссария
    """

    # ✅ Встроенный черный список системных терминов которые НИКОГДА не должны заменяться
    # Защита от порчи XML тегов, атрибутов и служебных имен
    PROTECTED_TERMS = {
        "li", "ul", "ol", "color", "size", "class", "type", "def",
        "parent", "mayrequire", "tag", "href", "src", "alt", "title",
        "style", "id", "name", "value", "key", "path", "url"
    }

    def __init__(self, filepath: str | None = None, logger = None, use_morphy: bool = False, target_lang: str = "ru"):
        self.filepath = filepath
        self._entries: dict[str, str] = {}
        self._original_terms: dict[str, str] = {}
        self._regex_entries: list[tuple[re.Pattern, str]] = []
        self._case_sensitive: bool = False
        self._protected_terms = self.PROTECTED_TERMS.copy()
        self.logger = logger
        self._use_morphy = use_morphy
        self._target_lang = target_lang.lower()
        self._morph_parser: Any | None = None
        self._cached_pattern: re.Pattern | None = None
        self._automaton_dirty: bool = False  # Флаг необходимости пересборки автомата
        
        if use_morphy and HAS_MORPHY:
            try:
                self._morph_parser = RimWorldUniversalParser(lang=self._target_lang)
            except Exception as e:
                if logger:
                    logger.warning(f"Не удалось инициализировать Morphy: {e}")
        
        if filepath:
            self.load(filepath)

    def add(self, original: str, translation: str) -> None:
        """
        Добавляет запись в глоссарий.
        
        ✅ Поддерживает обычные строки и регулярные выражения:
        Если ключ начинается и заканчивается на '/' → это регулярное выражение
        Пример: `/Slaves?/i` будет совпадать с Slave, slave, Slaves, slaves

        Args:
            original: Оригинальный текст или регулярное выражение
            translation: Перевод
        """
        if original.startswith('/') and original.endswith('/'):
            parts = original[1:-1].rsplit('/', 1)
            pattern = parts[0]
            flags = parts[1] if len(parts) > 1 else ''

            regex_flags = 0
            if 'i' in flags:
                regex_flags |= re.IGNORECASE

            try:
                compiled = re.compile(rf'\b{pattern}\b', regex_flags)
                self._regex_entries.append((compiled, translation))
            except re.error:
                if self.logger:
                    self.logger.warning(
                        f"Глоссарий: некорректное регулярное выражение '{original}', запись пропущена"
                    )
                return
        else:
            key = original if self._case_sensitive else original.lower()
            self._entries[key] = translation
            self._original_terms[original] = translation
            self._cached_pattern = None
            self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать

    def remove(self, original: str) -> bool:
        """Удаляет запись из глоссария."""
        key = original if self._case_sensitive else original.lower()
        if key in self._entries:
            del self._entries[key]
            self._original_terms.pop(key, None)
            self._cached_pattern = None
            self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать
            return True
        return False

    def get(self, original: str) -> str | None:
        """Получает перевод из глоссария."""
        key = original if self._case_sensitive else original.lower()
        return self._entries.get(key)

    def has(self, original: str) -> bool:
        """Проверяет наличие термина в глоссарии."""
        key = original if self._case_sensitive else original.lower()
        return key in self._entries

    def apply_to_text(self, text: str) -> str:
        """
        Применяет глоссарий к тексту.

        Заменяет все известные термины в тексте их переводами.
        ✅ ИСПРАВЛЕНИЕ 1: Заменяет ТОЛЬКО ЦЕЛЫЕ СЛОВА, не подстроки внутри других слов
        ✅ ИСПРАВЛЕНИЕ 2: Никогда не заменяет системные термины из черного списка
        ✅ ИСПРАВЛЕНИЕ 3: Автоматически пропускает текст содержащий XML теги
        ✅ ИСПРАВЛЕНИЕ 4: Сохраняет RimWorld-специфичные конструкции (*Health), {0}, [text]

        Args:
            text: Исходный текст

        Returns:
            Текст с применёнными терминами глоссария
        """
        if not text or not self._entries:
            return text

        # Проверка наличия настоящих XML тегов (не просто < и >, а парные теги)
        # Исключаем RimWorld-конструкции: (*tag), {0}, [text]
        has_xml_tags = False
        if '<' in text and '>' in text:
            # Проверяем, что это настоящие XML теги, а не RimWorld символы
            tag_pattern = re.compile(r'<[a-zA-Z][^>]*>')
            if tag_pattern.search(text):
                has_xml_tags = True
        
        if has_xml_tags:
            return text

        result = text

        # Сохраняем RimWorld-специфичные конструкции перед обработкой
        placeholders = []
        
        # Сохраняем переменные в фигурных скобках {0}, {letter}, и т.п.
        def save_brace_variable(match):
            placeholders.append(match.group(0))
            return f"__PLACEHOLDER_{len(placeholders)-1}__"
        
        result = re.sub(r'\{[a-zA-Z0-9_]+\}', save_brace_variable, result)
        
        # Сохраняем RimWorld-методы (*Health), (*Food), и т.п.
        def save_rimworld_method(match):
            placeholders.append(match.group(0))
            return f"__PLACEHOLDER_{len(placeholders)-1}__"
        
        result = re.sub(r'\(\*[a-zA-Z][a-zA-Z0-9]*\)', save_rimworld_method, result)
        
        # Сохраняем квадратные скобки [text]
        def save_bracketed(match):
            placeholders.append(match.group(0))
            return f"__PLACEHOLDER_{len(placeholders)-1}__"
        
        result = re.sub(r'\[[^\]]+\]', save_bracketed, result)

        # Компилируем паттерн для замены (только если есть записи и не готов паттерн)
        if self._cached_pattern is None and self._entries:
            escaped_terms = []
            for term in self._entries.keys():
                if term.lower() not in self._protected_terms:
                    escaped_terms.append(re.escape(term))
            if escaped_terms:
                self._cached_pattern = re.compile(
                    r'\b(' + '|'.join(escaped_terms) + r')\b',
                    re.IGNORECASE
                )

        if self._cached_pattern:
            def replacer(match):
                original_word = match.group(0)
                translation = self._entries.get(original_word.lower(), original_word)
                
                if translation.lower() in self._protected_terms:
                    return original_word
                
                if self._morph_parser and self._use_morphy and self._target_lang in ['ru', 'uk']:
                    translation = self.apply_morphology(text, translation, original_word)
                
                if original_word.isupper():
                    return translation.upper()
                elif original_word.istitle():
                    return translation.capitalize()
                elif original_word.islower():
                    return translation.lower()
                return translation

            result = self._cached_pattern.sub(replacer, result)

        # Применяем регулярные выражения
        for pattern, translation in self._regex_entries:
            if self.logger and pattern.search(result):
                self.logger.debug(f"📕 Глоссарий [Regex]: /{pattern.pattern}/ → '{translation}' | в тексте: {text[:50]}...")

            def replace_with_case_regex(match):
                original_word = match.group(0)
                if original_word.isupper():
                    return translation.upper()
                elif original_word.istitle():
                    return translation.capitalize()
                elif original_word.islower():
                    return translation.lower()
                return translation

            result = pattern.sub(replace_with_case_regex, result)

        # Восстанавливаем сохранённые конструкции
        for i, placeholder in enumerate(placeholders):
            result = result.replace(f"__PLACEHOLDER_{i}__", placeholder)

        return result

    def apply_morphology(self, text: str, translation: str, original_word: str) -> str:
        """
        Применяет морфологическое склонение к переводу.
        
        Для русского/украинского языка возвращает морфологичный перевод
        с учетом рода оригинального слова.
        
        Args:
            text: Исходный текст (для поиска слова)
            translation: Перевод
            original_word: Оригинальное слово
            
        Returns:
            Морфологиченый перевод или исходный перевод
        """
        if not self._use_morphy or not self._morph_parser:
            return translation
        
        if self._target_lang not in ['ru', 'uk']:
            return translation
        
        try:
            forms = self._morph_parser.get_word_forms(original_word)
            if forms and translation:
                for form_name, form_word in forms.items():
                    if form_word and form_word.lower() in text.lower():
                        return form_word
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Morphology error for '{original_word}': {e}")
        
        return translation

    def load(self, filepath: str) -> None:
        """Загружает глоссарий из JSON-файла.
        ✅ Если файл не существует - автоматически создаст пустой файл глоссария
        ✅ Поддерживает множественные файлы глоссария через load_from_directory()

        Args:
            filepath: Путь к JSON-файлу глоссария
        """
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                entries = data.get("entries", {})
                self._case_sensitive = data.get("case_sensitive", False)
                self.filepath = filepath
                self._use_morphy = data.get("use_morphy", False)
                self._target_lang = data.get("target_lang", "ru").lower()
                
                self._entries = {}
                self._original_terms = {}
                for original, translation in entries.items():
                    key = original if self._case_sensitive else original.lower()
                    self._entries[key] = translation
                    self._original_terms[original] = translation
                    
                self._cached_pattern = None
                self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать
        else:
            self.filepath = filepath
            self.save(filepath)
            if self.logger:
                self.logger.info(f"📘 Создан новый пустой файл глоссария: {filepath}")

    def load_from_directory(self, directory: str) -> None:
        """Загружает глоссарий из директории с несколькими JSON-файлами.
        
        Args:
            directory: Путь к директории с файлами глоссария
        """
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        index_path = os.path.join(directory, "glossary_index.json")
        if os.path.exists(index_path):
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
                file_mapping = index.get("files", {})
        else:
            file_mapping = {}
        
        for filename in os.listdir(directory):
            if not filename.endswith(".json") or filename == "glossary_index.json":
                continue
            
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    entries = data.get("entries", {})
                    for original, translation in entries.items():
                        key = original if self._case_sensitive else original.lower()
                        self._entries[key] = translation
                        self._original_terms[original] = translation
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка загрузки {filepath}: {e}")
        
        self.filepath = directory
        self._cached_pattern = None
        self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать

    def save(self, filepath: str | None = None) -> None:
        """
        Сохраняет глоссарий в JSON-файл.

        Args:
            filepath: Путь для сохранения (если None, используется self.filepath)

        Raises:
            ValueError: Если не указан путь для сохранения
        """
        path = filepath or self.filepath
        if not path:
            raise ValueError("Не указан путь для сохранения глоссария")

        data = {
            "entries": self._original_terms.copy(),
            "case_sensitive": self._case_sensitive,
            "use_morphy": self._use_morphy,
            "target_lang": self._target_lang,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def entries(self) -> dict[str, str]:
        """Все записи глоссария."""
        return self._entries.copy()

    @property
    def count(self) -> int:
        """Количество записей."""
        return len(self._entries)

    @property
    def case_sensitive(self) -> bool:
        """Флаг чувствительности к регистру."""
        return self._case_sensitive

    @case_sensitive.setter
    def case_sensitive(self, value: bool) -> None:
        """
        Устанавливает флаг чувствительности к регистру.

        Args:
            value: Новое значение флага
        """
        self._case_sensitive = value

    def merge(self, other: "Glossary") -> None:
        """
        Объединяет с другим глоссарием.

        Args:
            other: Другой глоссарий для объединения
        """
        self._entries.update(other._entries)
        self._original_terms.update(other._original_terms)

    def clear(self) -> None:
        """Очищает глоссарий."""
        self._entries.clear()
        self._original_terms.clear()
        self._regex_entries.clear()
        self._cached_pattern = None
        self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать

    def _needs_automaton_rebuild(self) -> bool:
        """Проверяет, нужно ли пересобирать автомат."""
        return self._automaton_dirty

    def rebuild_automaton(self) -> None:
        """Принудительно пересобирает автомат (компилирует паттерн)."""
        self._cached_pattern = None
        self._automaton_dirty = False
        # Принудительно собираем паттерн
        if self._entries:
            escaped_terms = []
            for term in self._entries.keys():
                if term.lower() not in self._protected_terms:
                    escaped_terms.append(re.escape(term))
            if escaped_terms:
                self._cached_pattern = re.compile(
                    r'\b(' + '|'.join(escaped_terms) + r')\b',
                    re.IGNORECASE
                )

    def export_dict(self) -> dict[str, str]:
        """
        Экспортирует в словарь.

        Returns:
            Копия всех записей глоссария
        """
        return self._entries.copy()

    def add_protected_term(self, term: str) -> None:
        """Добавляет термин в черный список защищенных слов"""
        self._protected_terms.add(term.lower())

    def remove_protected_term(self, term: str) -> bool:
        """Удаляет термин из черного списка"""
        term_lower = term.lower()
        if term_lower in self._protected_terms:
            self._protected_terms.remove(term_lower)
            return True
        return False

    def is_protected(self, term: str) -> bool:
        """Проверяет находится ли термин в защищенном списке"""
        return term.lower() in self._protected_terms

    def import_dict(self, data: dict[str, str]) -> None:
        """
        Импортирует из словаря.

        Args:
            data: Словарь с записями для импорта
        """
        self._entries.update(data)
        self._cached_pattern = None
        self._automaton_dirty = True  # Отмечаем, что автомат нужно пересобрать
