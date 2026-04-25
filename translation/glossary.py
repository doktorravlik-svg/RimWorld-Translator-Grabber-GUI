# translation/glossary.py
"""
Глоссарий — пользовательские термины с приоритетом.

Позволяет задать собственные переводы для конкретных слов/фраз,
которые будут применяться перед автоматическим переводом.
"""

import json
import os
import re


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

    def __init__(self, filepath: str | None = None, logger = None):
        self.filepath = filepath
        self._entries: dict[str, str] = {}
        self._regex_entries: list[tuple[re.Pattern, str]] = []
        self._case_sensitive: bool = False
        self._protected_terms = self.PROTECTED_TERMS.copy()
        self.logger = logger

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
        # Проверяем является ли это регулярным выражением
        if original.startswith('/') and original.endswith('/'):
            # Извлекаем паттерн и флаги
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
                # Если некорректный regex - добавляем как обычную строку
                key = original if self._case_sensitive else original.lower()
                self._entries[key] = translation
        else:
            key = original if self._case_sensitive else original.lower()
            self._entries[key] = translation

    def remove(self, original: str) -> bool:
        """Удаляет запись из глоссария."""
        key = original if self._case_sensitive else original.lower()
        if key in self._entries:
            del self._entries[key]
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
        ✅ ИСПРАВЛЕНИЕ 3: Автоматически пропускает текст содержащий XML разметку

        Args:
            text: Исходный текст

        Returns:
            Текст с применёнными терминами глоссария
        """
        if not text or not self._entries:
            return text

        # 🛡️ Защита XML: если текст выглядит как разметка - не трогаем вообще
        if '<' in text and '>' in text:
            return text

        result = text

        # 🛡️ Защита переменных: сохраняем все {0} {1} плейсхолдеры
        # Временно заменяем переменные на маркеры чтобы глоссарий их не трогал
        placeholders = []
        def save_placeholder(match):
            placeholders.append(match.group(0))
            return f"__PLACEHOLDER_{len(placeholders)-1}__"

        result = re.sub(r'\{\d+\}', save_placeholder, result)

        # 1. Сначала применяем точные обычные совпадения (самый высокий приоритет)
        # ✅ Сортировка с приоритетом фраз:
        # 1. Сначала по длине строки (самые длинные фразы ВСЕГДА первые)
        # 2. Затем по количеству слов
        # Это 100% гарантирует что "Kurin Apparel" обработается до "Kurin"
        for original, translation in sorted(
            self._entries.items(),
            key=lambda x: (len(x[0]), x[0].count(' ')),
            reverse=True
        ):
            # 🛡️ Защита: пропускаем термины из черного списка
            original_lower = original.lower()
            if original_lower in self._protected_terms:
                continue

            flags = re.IGNORECASE

            pattern = re.compile(rf'\b{re.escape(original)}\b', flags)

            def replace_with_case(match):
                original_word = match.group(0)
                # ✅ Автоматическое сохранение регистра
                if original_word.isupper():
                    # ВСЕ БОЛЬШИЕ БУКВЫ
                    return translation.upper()
                elif original_word.istitle():
                    # Первая буква большая
                    return translation.capitalize()
                elif original_word.islower():
                    # Все маленькие
                    return translation.lower()
                else:
                    # Смешанный регистр - возвращаем как есть
                    return translation

            # ✅ Логирование сработавших правил для отладки
            if self.logger and pattern.search(result):
                self.logger.debug(f"📕 Глоссарий: '{original}' → '{translation}' | в тексте: {text[:50]}...")

            result = pattern.sub(replace_with_case, result)

        # 2. Затем применяем регулярные выражения (более низкий приоритет)
        for pattern, translation in self._regex_entries:
            # ✅ Логирование сработавших regex правил
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

        # 🛡️ Восстанавливаем переменные обратно
        for i, placeholder in enumerate(placeholders):
            result = result.replace(f"__PLACEHOLDER_{i}__", placeholder)

        return result

    def load(self, filepath: str) -> None:
        """Загружает глоссарий из JSON-файла.
        ✅ Если файл не существует - автоматически создаст пустой файл глоссария

        Args:
            filepath: Путь к JSON-файлу глоссария
        """
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                self._entries = data.get("entries", {})
                self._case_sensitive = data.get("case_sensitive", False)
                self.filepath = filepath
        else:
            # ✅ Автоматическое создание файла если он отсутствует
            self.filepath = filepath
            self.save(filepath)
            if self.logger:
                self.logger.info(f"📘 Создан новый пустой файл глоссария: {filepath}")

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
            "entries": self._entries,
            "case_sensitive": self._case_sensitive,
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

    def clear(self) -> None:
        """Очищает глоссарий."""
        self._entries.clear()
        self._regex_entries.clear()

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
