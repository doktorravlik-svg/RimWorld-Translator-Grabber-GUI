"""
Quality Checker - проверка качества переводов для редактора.

Отвечает за:
- Проверку пустых переводов
- Проверку совпадения оригинала и перевода
- Проверку конечных пробелов
- Проверку пунктуации
- Проверку заглавных букв
- Проверку специальных тегов {0}, %s, и т.д.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class QualityIssue:
    """Проблема качества перевода."""
    key: str
    issue_type: str
    description: str
    severity: str  # "error", "warning", "info"
    original: str = ""
    translation: str = ""


class TranslationQualityChecker:
    """Проверка качества переводов."""

    def __init__(self):
        self.issues: List[QualityIssue] = []

    def check_entry(
        self,
        key: str,
        original: str,
        translation: str
    ) -> List[QualityIssue]:
        """
        Проверяет одну запись перевода.

        Args:
            key: Ключ перевода
            original: Оригинальный текст
            translation: Переведённый текст

        Returns:
            Список найденных проблем
        """
        self.issues = []

        self._check_empty_translation(key, translation)
        self._check_identical_texts(key, original, translation)
        self._check_trailing_spaces(key, original, translation)
        self._check_punctuation(key, original, translation)
        self._check_capitalization(key, original, translation)
        self._check_special_tags(key, original, translation)
        self._check_length_ratio(key, original, translation)

        return self.issues

    def check_all_entries(
        self,
        entries: List[dict]
    ) -> List[QualityIssue]:
        """
        Проверяет все записи перевода.

        Args:
            entries: Список {key, original, translation}

        Returns:
            Список всех найденных проблем
        """
        all_issues = []
        for entry in entries:
            issues = self.check_entry(
                entry.get("key", ""),
                entry.get("original", ""),
                entry.get("translation", "")
            )
            all_issues.extend(issues)
        return all_issues

    def _check_empty_translation(self, key: str, translation: str) -> None:
        """Проверяет пустые переводы."""
        if not translation or not translation.strip():
            self.issues.append(QualityIssue(
                key=key,
                issue_type="empty_translation",
                description="Перевод пустой",
                severity="error",
                translation=translation
            ))

    def _check_identical_texts(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет совпадение оригинала и перевода."""
        if original.strip() and original.strip() == translation.strip():
            self.issues.append(QualityIssue(
                key=key,
                issue_type="identical_texts",
                description="Перевод идентичен оригиналу",
                severity="warning",
                original=original,
                translation=translation
            ))

    def _check_trailing_spaces(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет конечные пробелы."""
        orig_trailing = len(original) - len(original.rstrip())
        trans_trailing = len(translation) - len(translation.rstrip())

        if orig_trailing != trans_trailing:
            self.issues.append(QualityIssue(
                key=key,
                issue_type="trailing_spaces",
                description=f"Несовпадение конечных пробелов (оригинал: {orig_trailing}, перевод: {trans_trailing})",
                severity="info",
                original=original,
                translation=translation
            ))

    def _check_punctuation(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет совпадение конечной пунктуации."""
        if not original or not translation:
            return

        orig_punct = original[-1] if original[-1] in ".!?;:" else ""
        trans_punct = translation[-1] if translation[-1] in ".!?;:" else ""

        if orig_punct and not trans_punct:
            self.issues.append(QualityIssue(
                key=key,
                issue_type="missing_punctuation",
                description="Отсутствует пунктуация в конце перевода",
                severity="warning",
                original=original,
                translation=translation
            ))

    def _check_capitalization(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет заглавные буквы в начале."""
        if not original or not translation:
            return

        orig_upper = original[0].isupper() if original[0].isalpha() else None
        trans_upper = translation[0].isupper() if translation[0].isalpha() else None

        if orig_upper is not None and trans_upper is not None:
            if orig_upper != trans_upper:
                self.issues.append(QualityIssue(
                    key=key,
                    issue_type="capitalization",
                    description="Несовпадение заглавных букв в начале",
                    severity="info",
                    original=original,
                    translation=translation
                ))

    def _check_special_tags(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет специальные теги {0}, %s, и т.д."""
        # Теги вида {0}, {1}, %s, %d
        orig_tags = set(re.findall(r'\{\d+\}|%[sd]|<[^>]+>', original))
        trans_tags = set(re.findall(r'\{\d+\}|%[sd]|<[^>]+>', translation))

        missing_tags = orig_tags - trans_tags
        extra_tags = trans_tags - orig_tags

        if missing_tags:
            self.issues.append(QualityIssue(
                key=key,
                issue_type="missing_tags",
                description=f"Отсутствуют теги: {', '.join(missing_tags)}",
                severity="error",
                original=original,
                translation=translation
            ))

        if extra_tags:
            self.issues.append(QualityIssue(
                key=key,
                issue_type="extra_tags",
                description=f"Лишние теги: {', '.join(extra_tags)}",
                severity="warning",
                original=original,
                translation=translation
            ))

    def _check_length_ratio(
        self,
        key: str,
        original: str,
        translation: str
    ) -> None:
        """Проверяет соотношение длин оригинала и перевода."""
        if not original or not translation:
            return

        orig_len = len(original)
        trans_len = len(translation)

        if orig_len > 0:
            ratio = trans_len / orig_len
            if ratio > 2.5:
                self.issues.append(QualityIssue(
                    key=key,
                    issue_type="too_long",
                    description=f"Перевод слишком длинный ({ratio:.1f}x от оригинала)",
                    severity="warning",
                    original=original,
                    translation=translation
                ))
            elif ratio < 0.3:
                self.issues.append(QualityIssue(
                    key=key,
                    issue_type="too_short",
                    description=f"Перевод слишком короткий ({ratio:.1f}x от оригинала)",
                    severity="warning",
                    original=original,
                    translation=translation
                ))

    def get_statistics(self, issues: List[QualityIssue]) -> dict:
        """
        Получает статистику проблем.

        Args:
            issues: Список проблем

        Returns:
            Словарь статистики
        """
        stats = {
            "total": len(issues),
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
            "info": sum(1 for i in issues if i.severity == "info"),
            "by_type": {},
        }

        for issue in issues:
            stats["by_type"][issue.issue_type] = stats["by_type"].get(issue.issue_type, 0) + 1

        return stats
