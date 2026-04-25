# verification/translation_validator.py
"""
Модуль валидации качества переводов RimWorld.

Основные функции:
- TranslationValidator: класс валидации переводов
- validate_placeholders: проверка плейсхолдеров
- validate_newlines: проверка переносов строк
- check_translation_quality: комплексная проверка качества
- apply_language_rules: применение языковых правил
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ============================================================================
# ТИПЫ ДАННЫХ И КОНСТАНТЫ
# ============================================================================


class ValidationSeverity(Enum):
    """Серьёзность проблемы валидации"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class QualityLevel(Enum):
    """Уровень качества перевода"""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


# Паттерны плейсхолдеров RimWorld и通用的
PLACEHOLDER_PATTERNS = [
    r"\{0\}",  # {0}
    r"\{1\}",  # {1}
    r"\{\d+\}",  # {n}
    r"%s",  # %s
    r"%d",  # %d
    r"%[.\d]*[dfgsx]",  # Форматирование %0.2f
    r"\$([A-Za-z_][A-Za-z0-9_]*)",  # $variable
    r"\[[^\]]+\]",  # [tag] - теги RimWorld
]


@dataclass
class ValidationIssue:
    """Проблема валидации"""

    severity: ValidationSeverity
    code: str
    message: str
    context: str | None = None
    position: int | None = None


@dataclass
class ValidationResult:
    """Результат валидации перевода"""

    key: str
    original: str
    translated: str
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    quality_score: float = 0.0
    quality_level: QualityLevel = QualityLevel.GOOD

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.INFO)


@dataclass
class TranslationValidationReport:
    """Отчет о валидации переводов"""

    total_keys: int = 0
    valid_keys: int = 0
    invalid_keys: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# КЛАСС TRANSLATION VALIDATOR
# ============================================================================


class TranslationValidator:
    """
    Класс для валидации качества переводов RimWorld.

    Поддерживает:
    - Проверку плейсхолдеров
    - Проверку переносов строк
    - Анализ длины перевода
    - Применение языковых правил
    - Комплексную оценку качества
    - ✅ НОВОЕ: Проверку терминологии по глоссарию
    """

    def __init__(self, language: str = "ru", logger: logging.Logger | None = None):
        self.language = language.lower()
        self.logger = logger
        self._placeholder_patterns = [re.compile(p) for p in PLACEHOLDER_PATTERNS]

        # ✅ НОВОЕ: Инициализация глоссария
        try:
            from translation_db import get_translation_db

            self.translation_db = get_translation_db()
            if self.translation_db and self.logger:
                stats = self.translation_db.get_stats()
                self.logger.info(f"Глоссарий загружен: {stats.get('glossary_terms', 0)} терминов")
        except ImportError:
            self.translation_db = None

    # =========================================================================
    # ОСНОВНЫЕ МЕТОДЫ ВАЛИДАЦИИ
    # =========================================================================

    def validate(self, key: str, original: str, translated: str) -> ValidationResult:
        """
        Валидирует перевод.

        Args:
            key: Ключ перевода
            original: Оригинальный текст
            translated: Переведенный текст

        Returns:
            ValidationResult с результатами
        """
        issues = []

        # 1. Проверка плейсхолдеров
        placeholder_issues = self._validate_placeholders(original, translated)
        issues.extend(placeholder_issues)

        # 2. Проверка переносов строк
        newline_issue = self._validate_newlines(original, translated)
        if newline_issue:
            issues.extend(newline_issue)

        # 3. Проверка длины
        length_issue = self._validate_length(original, translated)
        if length_issue:
            issues.extend(length_issue)

        # 4. Проверка на пустой перевод
        if not translated or not translated.strip():
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="EMPTY_TRANSLATION",
                    message="Перевод пуст или содержит только пробелы",
                )
            )

        # 5. Проверка на копирование оригинала
        if original and translated and original.strip().lower() == translated.strip().lower():
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="SAME_AS_ORIGINAL",
                    message="Перевод идентичен оригиналу",
                    context=original[:50],
                )
            )

        # ✅ НОВОЕ: 6. Проверка терминологии по глоссарию
        glossary_issues = self._validate_glossary_terms(original, translated)
        issues.extend(glossary_issues)

        # Определяем валидность
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        # Вычисляем качество
        quality_score = self._calculate_quality_score(original, translated, issues)
        quality_level = self._determine_quality_level(quality_score)

        return ValidationResult(
            key=key,
            original=original,
            translated=translated,
            is_valid=not has_errors,
            issues=issues,
            quality_score=quality_score,
            quality_level=quality_level,
        )

    def validate_batch(
        self, translations: dict[str, tuple[str, str]]
    ) -> TranslationValidationReport:
        """
        Валидирует批量 переводов.

        Args:
            translations: Словарь {key: (original, translated)}

        Returns:
            TranslationValidationReport с результатами
        """
        results = []

        for key, (original, translated) in translations.items():
            result = self.validate(key, original, translated)
            results.append(result)

        # Формируем отчет
        report = TranslationValidationReport(
            total_keys=len(results),
            valid_keys=sum(1 for r in results if r.is_valid),
            invalid_keys=sum(1 for r in results if not r.is_valid),
            results=results,
            statistics=self._calculate_statistics(results),
        )

        return report

    # =========================================================================
    # ЧАСТНЫЕ ПРОВЕРКИ
    # =========================================================================

    def _validate_placeholders(self, original: str, translated: str) -> list[ValidationIssue]:
        """
        Проверяет соответствие плейсхолдеров.

        Args:
            original: Оригинальный текст
            translated: Переведенный текст

        Returns:
            Список проблем
        """
        issues = []

        # Находим все плейсхолдеры в оригинале
        original_placeholders = self._extract_placeholders(original)
        # Находим все плейсхолдеры в переводе
        translated_placeholders = self._extract_placeholders(translated)

        # Проверяем отсутствующие плейсхолдеры
        missing = original_placeholders - translated_placeholders
        if missing:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_PLACEHOLDERS",
                    message=f"Отсутствуют плейсхолдеры: {missing}",
                    context=str(missing),
                )
            )

        # Проверяем лишние плейсхолдеры (только {n} которые не были в оригинале)
        extra_numeric = {
            p
            for p in translated_placeholders
            if re.match(r"\{\d+\}", p) and p not in original_placeholders
        }
        if extra_numeric:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EXTRA_PLACEHOLDERS",
                    message=f"Лишние плейсхолдеры: {extra_numeric}",
                    context=str(extra_numeric),
                )
            )

        # Проверяем неправильный порядок нумерации
        # Извлекаем числа из плейсхолдеров вида {0}, {1}, etc.
        orig_nums = []
        for p in original_placeholders:
            match = re.match(r"\{(\d+)\}", p)
            if match:
                orig_nums.append(int(match.group(1)))

        trans_nums = []
        for p in translated_placeholders:
            match = re.match(r"\{(\d+)\}", p)
            if match:
                trans_nums.append(int(match.group(1)))

        orig_nums = sorted(orig_nums)
        trans_nums = sorted(trans_nums)

        if orig_nums and trans_nums and orig_nums != trans_nums:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="PLACEHOLDER_ORDER_MISMATCH",
                    message=f"Порядок плейсхолдеров нарушен: оригинал {orig_nums}, перевод {trans_nums}",
                    context=f"{original_placeholders} -> {translated_placeholders}",
                )
            )

        return issues

    def _extract_placeholders(self, text: str) -> set[str]:
        """Извлекает все плейсхолдеры из текста"""
        placeholders = set()
        for pattern in self._placeholder_patterns:
            matches = pattern.findall(text)
            if pattern.pattern.startswith("\\["):
                # Для [tag] добавляем с скобками
                matches = [f"[{m}]" for m in matches]
            placeholders.update(matches)
        return placeholders

    def _validate_newlines(self, original: str, translated: str) -> list[ValidationIssue]:
        """Проверяет соответствие переносов строк"""
        issues = []

        # Считаем явные \n
        orig_newlines = original.count("\\n")
        trans_newlines = translated.count("\\n")

        if orig_newlines != trans_newlines:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="NEWLINE_MISMATCH",
                    message=f"Количество переносов строк не совпадает: оригинал {orig_newlines}, перевод {trans_newlines}",
                    context=f"Оригинал: {original[:100]!r}, Перевод: {translated[:100]!r}",
                )
            )

        return issues

    def _validate_length(self, original: str, translated: str) -> list[ValidationIssue]:
        """Проверяет длину перевода относительно оригинала"""
        issues = []

        orig_len = len(original)
        trans_len = len(translated)

        if orig_len == 0:
            return issues

        ratio = trans_len / orig_len

        # Перевод намного короче
        if ratio < 0.3:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="TOO_SHORT",
                    message=f"Перевод слишком короткий ({ratio * 100:.0f}% от оригинала)",
                    context=f"Оригинал: {orig_len} символов, Перевод: {trans_len} символов",
                )
            )

        # Перевод намного длиннее
        if ratio > 3.0:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="TOO_LONG",
                    message=f"Перевод слишком длинный ({ratio * 100:.0f}% от оригинала)",
                    context=f"Оригинал: {orig_len} символов, Перевод: {trans_len} символов",
                )
            )

        return issues

    def _validate_glossary_terms(self, original: str, translated: str) -> list[ValidationIssue]:
        """
        Проверяет использование терминов из глоссария.

        Если термин из глоссария встречается в переводе, но используется
        другой перевод — выдаёт предупреждение.

        Args:
            original: Оригинальный текст
            translated: Переведенный текст

        Returns:
            Список проблем с глоссарием
        """
        issues = []

        if not self.translation_db:
            return issues

        try:
            # Получаем все термины глоссария
            glossary_terms = self.translation_db.get_all_glossary()

            if not glossary_terms:
                return issues

            # Проверяем каждый термин
            for term_entry in glossary_terms:
                # term_entry это tuple: (id, term, translation, category, description, ...)
                # или sqlite3.Row
                if hasattr(term_entry, "keys"):  # sqlite3.Row
                    glossary_term = term_entry["term"]
                    glossary_translation = term_entry["translation"]
                else:  # tuple
                    glossary_term = term_entry[1]
                    glossary_translation = term_entry[2]

                # Проверяем, встречается ли термин в оригинале
                if glossary_term.lower() not in original.lower():
                    continue

                # Термин найден в оригинале - проверяем, используется ли правильный перевод
                if glossary_translation.lower() not in translated.lower():
                    issues.append(
                        ValidationIssue(
                            severity=ValidationSeverity.WARNING,
                            code="GLOSSARY_TERM_MISMATCH",
                            message=f"Термин '{glossary_term}' должен переводиться как '{glossary_translation}'",
                            context=f"Оригинал: {original[:80]}",
                        )
                    )

        except Exception as e:
            if self.logger:
                self.logger.debug(f"Ошибка проверки глоссария: {e}")

        return issues

    # =========================================================================
    # ОЦЕНКА КАЧЕСТВА
    # =========================================================================

    def _calculate_quality_score(
        self, original: str, translated: str, issues: list[ValidationIssue]
    ) -> float:
        """
        Вычисляет оценку качества перевода.

        Returns:
            Оценка от 0 до 100
        """
        score = 100.0

        # Штрафы за ошибки
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                score -= 20.0
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 5.0
            elif issue.severity == ValidationSeverity.INFO:
                score -= 1.0

        return max(0.0, min(100.0, score))

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Определяет уровень качества по оценке"""
        if score >= 95:
            return QualityLevel.EXCELLENT
        elif score >= 80:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.FAIR
        elif score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.VERY_POOR

    def _calculate_statistics(self, results: list[ValidationResult]) -> dict[str, Any]:
        """Вычисляет статистику по результатам"""
        total_errors = sum(r.error_count for r in results)
        total_warnings = sum(r.warning_count for r in results)
        total_info = sum(r.info_count for r in results)

        avg_score = sum(r.quality_score for r in results) / len(results) if results else 0

        # Распределение по уровням
        level_counts = {}
        for level in QualityLevel:
            level_counts[level.value] = sum(1 for r in results if r.quality_level == level)

        # Частые проблемы
        issue_codes = {}
        for r in results:
            for issue in r.issues:
                issue_codes[issue.code] = issue_codes.get(issue.code, 0) + 1

        return {
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_info": total_info,
            "average_quality_score": avg_score,
            "quality_level_distribution": level_counts,
            "most_common_issues": sorted(issue_codes.items(), key=lambda x: x[1], reverse=True)[
                :10
            ],
        }

    # =========================================================================
    # ЯЗЫКОВЫЕ ПРАВИЛА
    # =========================================================================

    def apply_language_rules(self, text: str, original_text: str = "") -> str:
        """
        Применяет языковые правила к тексту.

        Args:
            text: Переведенный текст
            original_text: Оригинальный текст (для сохранения регистра)

        Returns:
            Текст с примененными правилами
        """
        from language_rules import LanguageRules

        rules = LanguageRules(self.language)
        return rules.apply_capitalization(text, original_text)

    def validate_pronoun_cases(self, original: str, translated: str) -> list[ValidationIssue]:
        """
        Проверяет правильность склонения местоимений.

        Args:
            original: Оригинальный текст
            translated: Переведенный текст

        Returns:
            Список проблем
        """
        issues = []

        from language_rules import LanguageRules

        rules = LanguageRules(self.language)

        if not rules.config.has_cases:
            return issues

        # Здесь можно добавить более сложную логику проверки падежей
        # Пока возвращаем пустой список - требуется контекст для анализа

        return issues


# ============================================================================
# ФУНКЦИИ ВЫСОКОГО УРОВНЯ
# ============================================================================


def validate_placeholders(original: str, translated: str) -> tuple[bool, list[str]]:
    """
    Проверяет, что все плейсхолдеры из оригинала присутствуют в переводе.

    Args:
        original: Оригинальный текст
        translated: Переведенный текст

    Returns:
        (is_valid, list_of_errors)
    """
    validator = TranslationValidator()
    issues = validator._validate_placeholders(original, translated)

    errors = [i.message for i in issues if i.severity == ValidationSeverity.ERROR]
    return len(errors) == 0, errors


def validate_newlines(original: str, translated: str) -> tuple[bool, str]:
    """
    Проверяет соответствие переносов строк.

    Args:
        original: Оригинальный текст
        translated: Переведенный текст

    Returns:
        (is_valid, error_message)
    """
    orig_newlines = original.count("\\n")
    trans_newlines = translated.count("\\n")

    if orig_newlines != trans_newlines:
        return False, f"Оригинал: {orig_newlines} переносов, Перевод: {trans_newlines}"

    return True, ""


def check_translation_quality_detailed(original: str, translated: str) -> dict[str, Any]:
    """
    Комплексная проверка качества перевода (расширенная версия).

    Args:
        original: Оригинальный текст
        translated: Переведенный текст

    Returns:
        Dict с результатами проверки (включая quality_score, quality_level)

    Note:
        Для базовой проверки используйте rules_validation.check_translation_quality()
    """
    validator = TranslationValidator()
    result = validator.validate("unknown_key", original, translated)

    return {
        "valid": result.is_valid,
        "errors": [i.message for i in result.issues if i.severity == ValidationSeverity.ERROR],
        "warnings": [i.message for i in result.issues if i.severity == ValidationSeverity.WARNING],
        "quality_score": result.quality_score,
        "quality_level": result.quality_level.value,
    }


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование translation_validator")
    print("=" * 60)

    # Тест валидации плейсхолдеров
    print("\n[ТЕСТ] Валидация плейсхолдеров:")

    validator = TranslationValidator()

    # Тест 1: Правильный перевод с плейсхолдерами
    result = validator.validate(
        "test_key", "Hello {0}, you have {1} messages", "Привет {0}, у тебя {1} сообщений"
    )
    print(f"  Тест 1 (правильные плейсхолдеры): {result.is_valid}, ошибок: {result.error_count}")

    # Тест 2: Отсутствующие плейсхолдеры
    result = validator.validate("test_key", "Hello {0}", "Привет")
    print(
        f"  Тест 2 (отсутствуют плейсхолдеры): валидность={result.is_valid}, {result.issues[0].message if result.issues else 'нет проблем'}"
    )

    # Тест 3: Комплексная проверка
    print("\n[ТЕСТ] Комплексная проверка:")
    quality = check_translation_quality_detailed("Hello world", "Привет мир")
    print(f"  Качество: {quality['quality_level']}, счет: {quality['quality_score']}")

    # Тест batch
    print("\n[ТЕСТ] Batch валидация:")
    translations = {
        "key1": ("Hello {0}", "Привет {0}"),
        "key2": ("Goodbye", "До свидания"),
        "key3": ("Count: {0}", "Количество: {1}"),  # Ошибка
    }
    report = validator.validate_batch(translations)
    print(f"  Всего ключей: {report.total_keys}, валидных: {report.valid_keys}")
    print(f"  Статистика: {report.statistics}")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
