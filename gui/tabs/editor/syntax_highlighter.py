"""
Syntax Highlighter - подсветка синтаксиса XML для редактора переводов.

Отвечает за:
- Подсветку XML тегов
- Подсветку атрибутов
- Подсветку комментариев
- Подсветку орфографических ошибок (pyspellchecker)
"""

import re
from typing import Dict, List, Optional


class XMLSyntaxHighlighter:
    """Подсветка синтаксиса XML."""

    # Паттерны XML
    PATTERNS = [
        # Комментарии <!-- ... -->
        (r"(&lt;!--.*?--&gt;)", "comment"),
        # XML теги <tag> и </tag>
        (r"(&lt;/?[a-zA-Z][a-zA-Z0-9_.-]*)", "tag"),
        # Закрывающие части тегов >
        (r"(/?&gt;)", "tag"),
        # Атрибуты name="value"
        (r'(\b[a-zA-Z][a-zA-Z0-9_.-]*)\s*=', "attribute"),
        # Строки в кавычках
        (r'(".*?")', "string"),
        # EN комментарии <!-- EN: ... -->
        (r"(&lt;!--\s*EN:\s*(.*?)\s*--&gt;)", "en_comment"),
    ]

    def __init__(self, text_widget):
        """
        Args:
            text_widget: Текстовый виджет для подсветки
        """
        self.text_widget = text_widget
        self._tags_configured = False

    def _configure_tags(self, colors: Optional[Dict[str, str]] = None) -> None:
        """
        Настраивает теги подсветки.

        Args:
            colors: Словарь цветов {имя_тега: цвет}
        """
        if self._tags_configured:
            return

        default_colors = {
            "tag": "#569CD6",          # Синий для тегов
            "attribute": "#9CDCFE",     # Голубой для атрибутов
            "string": "#CE9178",        # Оранжевый для строк
            "comment": "#6A9955",       # Зелёный для комментариев
            "en_comment": "#808080",    # Серый для EN комментариев
            "spell_error": "#FF0000",   # Красный для орфографических ошибок
        }

        colors = colors or {}
        for tag_name, default_color in default_colors.items():
            color = colors.get(tag_name, default_color)
            self.text_widget.tag_configure(tag_name, foreground=color)

        # Подчёркивание для орфографических ошибок
        self.text_widget.tag_configure("spell_error", underline=True)

        self._tags_configured = True

    def highlight(self, text: str, colors: Optional[Dict[str, str]] = None) -> None:
        """
        Подсвечивает синтаксис XML.

        Args:
            text: Текст для подсветки
            colors: Словарь цветов
        """
        self._configure_tags(colors)

        # Удаляем старые теги
        for tag_name in ["tag", "attribute", "string", "comment", "en_comment"]:
            self.text_widget.tag_remove(tag_name, "1.0", "end")

        # Применяем подсветку по паттернам
        for pattern, tag_name in self.PATTERNS:
            for match in re.finditer(pattern, text):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.text_widget.tag_add(tag_name, start, end)


class SpellingChecker:
    """Проверка орфографии с использованием pyspellchecker."""

    def __init__(self, language: str = "en"):
        """
        Args:
            language: Язык проверки (en, ru, и т.д.)
        """
        self.language = language
        self.spell_checker = None
        self._initialize_checker()

    def _initialize_checker(self) -> None:
        """Инициализирует проверщик орфографии."""
        try:
            from spellchecker import SpellChecker
            self.spell_checker = SpellChecker(language=self.language)
        except ImportError:
            self.spell_checker = None
        except Exception:
            self.spell_checker = None

    def check_spelling(self, text: str) -> List[str]:
        """
        Проверяет орфографию в тексте.

        Args:
            text: Текст для проверки

        Returns:
            Список слов с ошибками
        """
        if not self.spell_checker:
            return []

        # Разбиваем на слова и проверяем
        words = re.findall(r'\b[a-zA-Zа-яА-Я]+\b', text)
        misspelled = self.spell_checker.unknown(words)
        return list(misspelled)

    def highlight_spelling_errors(
        self,
        text_widget,
        text: str,
        tag_name: str = "spell_error"
    ) -> int:
        """
        Подсвечивает орфографические ошибки.

        Args:
            text_widget: Текстовый виджет
            text: Текст для проверки
            tag_name: Имя тега для подсветки

        Returns:
            Количество найденных ошибок
        """
        if not self.spell_checker:
            return 0

        # Удаляем старые теги
        text_widget.tag_remove(tag_name, "1.0", "end")

        words = re.finditer(r'\b[a-zA-Zа-яА-Я]+\b', text)
        error_count = 0

        for match in words:
            word = match.group()
            if word.lower() not in self.spell_checker:
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                text_widget.tag_add(tag_name, start, end)
                error_count += 1

        return error_count

    @property
    def available(self) -> bool:
        """Доступен ли проверщик орфографии."""
        return self.spell_checker is not None
