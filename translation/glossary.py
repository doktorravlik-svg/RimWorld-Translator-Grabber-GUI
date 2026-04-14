# translation/glossary.py
"""
Глоссарий — пользовательские термины с приоритетом.

Позволяет задать собственные переводы для конкретных слов/фраз,
которые будут применяться перед автоматическим переводом.
"""

import json
import os


class Glossary:
    """
    Глоссарий переводов.

    Хранит пары оригинал->перевод и применяет их
    до/после автоматического перевода.

    Args:
        filepath: Путь к JSON-файлу глоссария
    """

    def __init__(self, filepath: str | None = None):
        self.filepath = filepath
        self._entries: dict[str, str] = {}
        self._case_sensitive: bool = False

        if filepath and os.path.exists(filepath):
            self.load(filepath)

    def add(self, original: str, translation: str) -> None:
        """
        Добавляет запись в глоссарий.

        Args:
            original: Оригинальный текст
            translation: Перевод
        """
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

        Args:
            text: Исходный текст

        Returns:
            Текст с применёнными терминами глоссария
        """
        result = text
        # Сортируем по длине (сначала длинные термины)
        for original, translation in sorted(
            self._entries.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if self._case_sensitive:
                result = result.replace(original, translation)
            else:
                # Case-insensitive замена
                import re

                pattern = re.compile(re.escape(original), re.IGNORECASE)
                result = pattern.sub(translation, result)
        return result

    def load(self, filepath: str) -> None:
        """Загружает глоссарий из JSON-файла.

        Args:
            filepath: Путь к JSON-файлу глоссария
        """
        if os.path.exists(filepath):
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                self._entries = data.get("entries", {})
                self._case_sensitive = data.get("case_sensitive", False)
                self.filepath = filepath

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

    def export_dict(self) -> dict[str, str]:
        """
        Экспортирует в словарь.

        Returns:
            Копия всех записей глоссария
        """
        return self._entries.copy()

    def import_dict(self, data: dict[str, str]) -> None:
        """
        Импортирует из словаря.

        Args:
            data: Словарь с записями для импорта
        """
        self._entries.update(data)
