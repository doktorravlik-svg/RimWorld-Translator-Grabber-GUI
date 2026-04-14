# verification/verification_coordinator.py
"""
Центральный координатор системы верификации переводов RimWorld.

Этот модуль объединяет все компоненты системы верификации:
- Сканирование и анализ модов
- Проверка зависимостей
- Обнаружение конфликтов
- Валидация переводов
- Генерация отчетов

Плагинная система позволяет добавлять новые проверки без изменения основной структуры.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from .conflict_detector import ConflictDetector, ConflictInfo, ConflictSeverity, ConflictType
from .dependency_checker import DependencyChecker
from .report_generator import ReportGenerator, ReportStatistics
from .translation_validator import (
    TranslationValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

# Импорт модулей системы

# ============================================================================
# БАЗОВЫЕ ИНТЕРФЕЙСЫ (для расширяемости)
# ============================================================================


class VerificationListener(ABC):
    """
    Абстрактный listener для событий верификации.

    Позволяет подписаться на события в процессе верификации.
    """

    @abstractmethod
    def on_mod_discovered(self, mod_info: dict) -> None:
        """Вызывается при обнаружении мода"""
        pass

    @abstractmethod
    def on_mod_verified(self, result: "VerificationResult") -> None:
        """Вызывается после верификации мода"""
        pass

    @abstractmethod
    def on_conflict_detected(self, conflict: ConflictInfo) -> None:
        """Вызывается при обнаружении конфликта"""
        pass

    @abstractmethod
    def on_error(self, error: str, context: dict) -> None:
        """Вызывается при ошибке"""
        pass

    @abstractmethod
    def on_progress(self, current: int, total: int, message: str) -> None:
        """Вызывается при изменении прогресса"""
        pass


class VerificationCheck(ABC):
    """
    Абстрактный класс для проверок верификации.

    Наследуйте этот класс для создания собственных проверок.

    Пример:
        class MyCustomCheck(VerificationCheck):
            @property
            def name(self) -> str:
                return "my_custom_check"

            @property
            def description(self) -> str:
                return "Моя кастомная проверка"

            def run(self, mod_info: Dict, context: Dict) -> CheckResult:
                # Логика проверки
                return CheckResult(...)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Уникальное имя проверки"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Описание проверки"""
        pass

    @property
    def severity(self) -> str:
        """Серьёзность по умолчанию"""
        return "warning"

    @abstractmethod
    def run(self, mod_info: dict, context: dict) -> "CheckResult":
        """
        Выполнить проверку.

        Args:
            mod_info: Информация о моде
            context: Контекст верификации

        Returns:
            CheckResult с результатом проверки
        """
        pass


# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================


@dataclass
class CheckResult:
    """Результат отдельной проверки"""

    check_name: str
    passed: bool
    severity: str  # 'error', 'warning', 'info'
    message: str
    details: dict = field(default_factory=dict)

    def to_validation_issue(self) -> ValidationIssue:
        """Конвертировать в ValidationIssue"""
        return ValidationIssue(
            severity=ValidationSeverity.ERROR
            if self.severity == "error"
            else ValidationSeverity.WARNING
            if self.severity == "warning"
            else ValidationSeverity.INFO,
            code=self.check_name,
            message=self.message,
            context=str(self.details),
        )


@dataclass
class VerificationResult:
    """
    Результат верификации одного мода.

    Содержит все результаты проверок, конфликты и ошибки.
    """

    mod_id: str
    mod_name: str
    mod_path: str
    is_translation: bool
    parent_mod_id: str | None = None

    # Результаты проверок
    checks: list[CheckResult] = field(default_factory=list)
    conflicts: list[ConflictInfo] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Статус
    is_valid: bool = True
    validated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    files_with_errors: list[str] = field(default_factory=list)  # Файлы с ошибками

    def add_check(self, result: CheckResult, file_path: str = "") -> None:
        """Добавить результат проверки"""
        self.checks.append(result)
        if not result.passed:
            if result.severity == "error":
                self.is_valid = False
                self.errors.append(f"{result.check_name}: {result.message}")
                if file_path and file_path not in self.files_with_errors:
                    self.files_with_errors.append(file_path)
            else:
                self.warnings.append(f"{result.check_name}: {result.message}")

    def add_conflict(self, conflict: ConflictInfo, file_path: str = "") -> None:
        """Добавить конфликт"""
        self.conflicts.append(conflict)
        if conflict.severity.value == "error":
            self.is_valid = False
            self.errors.append(f"Конфликт: {conflict.description}")
            if file_path and file_path not in self.files_with_errors:
                self.files_with_errors.append(file_path)

    def add_validation_result(self, result: ValidationResult, file_path: str = "") -> None:
        """Добавить результат валидации перевода"""
        self.validation_results.append(result)
        if not result.is_valid:
            for issue in result.issues:
                if issue.severity == ValidationSeverity.ERROR:
                    self.errors.append(f"Валидация: {issue.message}")
                    if file_path and file_path not in self.files_with_errors:
                        self.files_with_errors.append(file_path)
                elif issue.severity == ValidationSeverity.WARNING:
                    self.warnings.append(f"Валидация: {issue.message}")

    def get_summary(self) -> dict:
        """Получить сводку результатов"""
        return {
            "mod_id": self.mod_id,
            "mod_name": self.mod_name,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "conflict_count": len(self.conflicts),
            "checks_passed": sum(1 for c in self.checks if c.passed),
            "checks_failed": sum(1 for c in self.checks if not c.passed),
        }


# ============================================================================
# ВСТРОЕННЫЕ ПРОВЕРКИ
# ============================================================================


class AboutXmlCheck(VerificationCheck):
    """Проверка корректности About.xml"""

    @property
    def name(self) -> str:
        return "about_xml"

    @property
    def description(self) -> str:
        return "Проверка корректности About.xml"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        about_data = mod_info.get("about_data", {})

        errors = []
        if not about_data.get("mod_id"):
            errors.append("Отсутствует packageId")
        if not about_data.get("name"):
            errors.append("Отсутствует название мода")

        version = about_data.get("version", "0.0.0")
        if not self._is_valid_version(version):
            errors.append(f"Некорректный формат версии: {version}")

        passed = len(errors) == 0
        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity="error",
            message="; ".join(errors) if errors else "About.xml корректен",
            details={"errors": errors},
        )

    def _is_valid_version(self, version: str) -> bool:
        try:
            parts = version.split(".")
            return len(parts) >= 2 and all(p.isdigit() for p in parts)
        except (AttributeError, ValueError):
            return False


class DependenciesCheck(VerificationCheck):
    """Проверка зависимостей мода"""

    @property
    def name(self) -> str:
        return "dependencies"

    @property
    def description(self) -> str:
        return "Проверка зависимостей мода"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        all_mods = context.get("all_mods", {})
        dependencies = mod_info.get("dependencies", [])

        missing = []
        for dep in dependencies:
            dep_id = dep.get("packageId") if isinstance(dep, dict) else str(dep)
            if dep_id and dep_id not in all_mods:
                missing.append(dep_id)

        passed = len(missing) == 0
        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity="warning",
            message=f"Отсутствуют зависимости: {', '.join(missing)}"
            if missing
            else "Все зависимости найдены",
            details={"missing": missing},
        )


class TranslationStructureCheck(VerificationCheck):
    """Проверка структуры переводов"""

    @property
    def name(self) -> str:
        return "translation_structure"

    @property
    def description(self) -> str:
        return "Проверка структуры файлов переводов"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_path = mod_info.get("mod_path", "")

        # Проверяем наличие Languages
        langs_path = os.path.join(mod_path, "Languages")
        has_languages = os.path.exists(langs_path)

        # Проверяем наличие Defs
        defs_path = os.path.join(mod_path, "Defs")
        has_defs = os.path.exists(defs_path)

        warnings = []
        if mod_info.get("is_translation") and not has_languages:
            warnings.append("Переводной мод не содержит папку Languages")
        if not has_defs and not has_languages:
            warnings.append("Мод не содержит ни Defs, ни Languages")

        return CheckResult(
            check_name=self.name,
            passed=len(warnings) == 0,
            severity="warning",
            message="; ".join(warnings) if warnings else "Структура переводов корректна",
            details={"warnings": warnings},
        )


# ============================================================================
# КООРДИНАТОР ВЕРИФИКАЦИИ
# ============================================================================


class VerificationCoordinator:
    """
    Центральный координатор системы верификации.

    Управляет процессом верификации, координирует работу всех модулей,
    собирает результаты и генерирует отчеты.

    Поддерживает плагинную систему для добавления новых проверок.

    Пример использования:
        coordinator = VerificationCoordinator("C:/RimWorld/Mods")

        # Добавление кастомной проверки
        coordinator.register_check(MyCustomCheck())

        # Добавление listener
        coordinator.add_listener(MyListener())

        # Запуск верификации
        results = coordinator.run_verification()

        # Генерация отчета
        report = coordinator.generate_report(format='html')
    """

    def __init__(self, mods_path: str, logger: logging.Logger | None = None, language: str = "ru"):
        self.mods_path = mods_path
        self.logger = logger or logging.getLogger(__name__)
        self.language = language

        # Слушатели событий
        self.listeners: list[VerificationListener] = []

        # Зарегистрированные проверки
        self.checks: list[VerificationCheck] = []

        # Кэш данных
        self._mods_cache: dict[str, dict] = {}

        # Результаты
        self.results: list[VerificationResult] = []
        self.global_conflicts: list[ConflictInfo] = []

        # Модули системы
        self._dependency_checker: DependencyChecker | None = None
        self._conflict_detector: ConflictDetector | None = None
        self._translation_validator: TranslationValidator | None = None
        self._report_generator: ReportGenerator | None = None

        # Регистрируем встроенные проверки
        self._register_default_checks()

    # =========================================================================
    # РЕГИСТРАЦИЯ РАСШИРЕНИЙ
    # =========================================================================

    def _register_default_checks(self) -> None:
        """Регистрирует встроенные проверки"""
        self.register_check(AboutXmlCheck())
        self.register_check(DependenciesCheck())
        self.register_check(TranslationStructureCheck())
        self.logger.info("Зарегистрированы встроенные проверки")

    def add_listener(self, listener: VerificationListener) -> None:
        """Добавить listener для событий"""
        self.listeners.append(listener)

    def remove_listener(self, listener: VerificationListener) -> None:
        """Удалить listener"""
        if listener in self.listeners:
            self.listeners.remove(listener)

    def register_check(self, check: VerificationCheck) -> None:
        """Зарегистрировать новую проверку"""
        self.checks.append(check)
        self.logger.info(f"Зарегистрирована проверка: {check.name}")

    def unregister_check(self, check_name: str) -> None:
        """Удалить проверку по имени"""
        self.checks = [c for c in self.checks if c.name != check_name]

    # =========================================================================
    # ОСНОВНОЙ ПРОЦЕСС ВЕРИФИКАЦИИ
    # =========================================================================

    def run_verification(self) -> list[VerificationResult]:
        """
        Запустить полную верификацию.

        Returns:
            Список результатов верификации для каждого мода
        """
        self.logger.info(f"Начало верификации модов в: {self.mods_path}")

        try:
            # Этап 1: Сканирование модов
            self._scan_mods()

            # Этап 2: Инициализация модулей
            self._init_modules()

            # Этап 3: Выполнение проверок
            self._run_checks()

            # Этап 4: Обнаружение конфликтов
            self._detect_conflicts()

            # Этап 5: Валидация переводов
            self._validate_translations()

            self.logger.info(f"Верификация завершена. Проверено модов: {len(self.results)}")

        except Exception as e:
            self.logger.error(f"Ошибка верификации: {e}")
            self._notify_error(f"Ошибка верификации: {e}", {"error": str(e)})

        return self.results

    def run_verification_for_mod(self, mod_id: str) -> VerificationResult | None:
        """
        Запустить верификацию для конкретного мода.

        Args:
            mod_id: ID мода

        Returns:
            Результат верификации или None
        """
        if mod_id not in self._mods_cache:
            self.logger.warning(f"Мод не найден: {mod_id}")
            return None

        # Сканируем если еще не сканировано
        if not self._mods_cache:
            self._scan_mods()
            self._init_modules()

        mod_info = self._mods_cache[mod_id]
        result = self._verify_mod(mod_info)

        return result

    # =========================================================================
    # ЭТАПЫ ВЕРИФИКАЦИИ
    # =========================================================================

    def _scan_mods(self) -> None:
        """Сканирование и первичный анализ модов"""
        from scanner.mod_scanner import find_about_xml, parse_about_xml

        if not os.path.exists(self.mods_path):
            self._notify_error(f"Путь не существует: {self.mods_path}", {})
            return

        total_items = len(
            [
                i
                for i in os.listdir(self.mods_path)
                if os.path.isdir(os.path.join(self.mods_path, i))
            ]
        )
        processed = 0

        for item in os.listdir(self.mods_path):
            mod_path = os.path.join(self.mods_path, item)
            if not os.path.isdir(mod_path):
                continue

            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            about_data = parse_about_xml(about_path)
            mod_id = about_data.get("mod_id")

            if not mod_id:
                continue

            # Определение типа мода
            is_translation = self._is_translation_mod(about_data)

            mod_info = {
                "mod_id": mod_id,
                "mod_name": about_data.get("name", "Unknown"),
                "mod_path": mod_path,
                "about_path": about_path,
                "about_data": about_data,
                "is_translation": is_translation,
                "parent_mod_id": about_data.get("target_mod_id"),
                "dependencies": about_data.get("dependencies", []),
                "version": about_data.get("version"),
                "supported_languages": about_data.get("supported_languages", []),
            }

            self._mods_cache[mod_id] = mod_info

            # Уведомляем listeners
            for listener in self.listeners:
                listener.on_mod_discovered(mod_info)

            processed += 1
            for listener in self.listeners:
                listener.on_progress(
                    processed, total_items, f"Сканирование: {mod_info['mod_name']}"
                )

        self.logger.info(f"Сканирование завершено: найдено {len(self._mods_cache)} модов")

    def _init_modules(self) -> None:
        """Инициализация модулей системы"""
        self._dependency_checker = DependencyChecker(self.mods_path, self.logger)
        self._dependency_checker.load_mods()

        self._conflict_detector = ConflictDetector(self.mods_path, self.logger)
        self._conflict_detector.load_mods()
        # ✅ ИСПРАВЛЕНО: Передаём язык для загрузки переводов
        self._conflict_detector.load_translations(language=self.language)

        self._translation_validator = TranslationValidator(self.language, self.logger)

        self._report_generator = ReportGenerator(self.logger)

        self.logger.info("Модули системы инициализированы")

    def _run_checks(self) -> None:
        """Выполнение всех зарегистрированных проверок"""
        total = len(self._mods_cache)
        processed = 0

        for mod_id, mod_info in self._mods_cache.items():
            result = self._verify_mod(mod_info)
            self.results.append(result)

            # Уведомляем listeners
            for listener in self.listeners:
                listener.on_mod_verified(result)

            processed += 1
            for listener in self.listeners:
                listener.on_progress(processed, total, f"Проверка: {mod_info['mod_name']}")

        self.logger.info(f"Проверки завершены: обработано {len(self.results)} модов")

    def _verify_mod(self, mod_info: dict) -> VerificationResult:
        """Верификация одного мода"""
        result = VerificationResult(
            mod_id=mod_info["mod_id"],
            mod_name=mod_info["mod_name"],
            mod_path=mod_info["mod_path"],
            is_translation=mod_info["is_translation"],
            parent_mod_id=mod_info.get("parent_mod_id"),
        )

        context = {"mod_info": mod_info, "all_mods": self._mods_cache, "mods_path": self.mods_path}

        # Получаем файл для контекста
        file_path = mod_info.get("about_path", "")  # Путь к About.xml

        # Выполняем каждую проверку
        for check in self.checks:
            try:
                check_result = check.run(mod_info, context)
                result.add_check(check_result, file_path)
            except Exception as e:
                self.logger.error(f"Ошибка проверки {check.name}: {e}")
                result.add_check(
                    CheckResult(
                        check_name=check.name,
                        passed=False,
                        severity="error",
                        message=f"Ошибка выполнения: {e}",
                    ),
                    file_path,
                )

        return result

    def _detect_conflicts(self) -> None:
        """Обнаружение глобальных конфликтов"""
        # Конфликты от dependency checker
        if self._dependency_checker:
            missing_deps = self._dependency_checker.find_missing_dependencies()
            for mod_id, deps in missing_deps.items():
                if mod_id in self._mods_cache:
                    mod_info = self._mods_cache[mod_id]
                    for dep_id in deps:
                        conflict = ConflictInfo(
                            conflict_type=ConflictType.MISSING_PARENT,
                            key_or_file=mod_id,
                            mod_a=mod_id,
                            mod_b=dep_id,
                            severity=ConflictSeverity.ERROR,
                            description=f"Отсутствует обязательная зависимость: {dep_id}",
                            resolution=f"Установите мод {dep_id}",
                        )
                        self.global_conflicts.append(conflict)

                        # Добавляем конфликт в результат мода
                        for result in self.results:
                            if result.mod_id == mod_id:
                                result.add_conflict(conflict, mod_info.get("about_path", ""))

        # Конфликты от conflict detector
        if self._conflict_detector:
            duplicate_conflicts = self._conflict_detector.find_duplicate_keys()
            for conflict in duplicate_conflicts:
                self.global_conflicts.append(conflict)

                # Добавляем в соответствующие моды
                for mod_id in [conflict.mod_a, conflict.mod_b]:
                    for result in self.results:
                        if result.mod_id == mod_id:
                            result.add_conflict(
                                conflict,
                                conflict.file_path if hasattr(conflict, "file_path") else "",
                            )

        # Уведомляем listeners о конфликтах
        for conflict in self.global_conflicts:
            for listener in self.listeners:
                listener.on_conflict_detected(conflict)

        self.logger.info(f"Обнаружено конфликтов: {len(self.global_conflicts)}")

    def _validate_translations(self) -> None:
        """Валидация переводов только для выбранного языка"""
        # Получаем переводы для валидации
        if not self._conflict_detector:
            return

        translations = self._conflict_detector._translations

        # Фильтруем переводы по выбранному языку
        language_folder = self._get_language_folder(self.language)
        self.logger.info(f"Валидация переводов для языка: {language_folder}")

        # ✅ ИСПРАВЛЕНО: Загружаем оригиналы из английского мода
        english_originals = self._load_english_originals(translations)

        # Валидируем ключи с несколькими значениями только для выбранного языка
        for key, entries in translations.items():
            if len(entries) <= 1:
                continue

            # Фильтруем по языку
            filtered_entries = [e for e in entries if language_folder in e.file_path]
            if len(filtered_entries) <= 1:
                continue

            # Валидируем только выбранный язык
            for entry in filtered_entries:
                if entry.value:
                    # ✅ ИСПРАВЛЕНО: Берем оригинал из английского мода
                    original_text = english_originals.get(key, "")

                    # Если оригинал не найден, пропускаем (нет смысла проверять без оригинала)
                    if not original_text:
                        continue

                    result = self._translation_validator.validate(
                        key,
                        original_text,  # ✅ Теперь передаем реальный оригинал
                        entry.value,  # Перевод
                    )

                    # Находим результат верификации мода
                    for vr in self.results:
                        if vr.mod_id == entry.mod_id:
                            vr.add_validation_result(result, entry.file_path)

        self.logger.info("Валидация переводов завершена")

    def _load_english_originals(self, translations: dict) -> dict:
        """
        Загружает английские оригиналы из модов.

        Args:
            translations: Словарь переводов из ConflictDetector

        Returns:
            Словарь {key: english_text}
        """
        english_originals = {}
        english_folder = self._get_language_folder("English")

        # Ищем английские оригиналы в каждом моде
        for mod_id, mod_info in self._mods_cache.items():
            mod_path = mod_info.get("mod_path", "")
            if not mod_path:
                continue

            # Проверяем наличие английной папки
            keyed_path = os.path.join(mod_path, "Languages", english_folder, "Keyed")
            if not os.path.exists(keyed_path):
                continue

            # Парсим все XML файлы
            try:
                from verification.xml_parser import XMLParser

                parser = XMLParser()
                for filename in os.listdir(keyed_path):
                    if filename.endswith(".xml"):
                        file_path = os.path.join(keyed_path, filename)
                        entries = parser.parse_keyed_file(file_path)
                        for entry in entries:
                            if entry.value and entry.value.strip():
                                english_originals[entry.key] = entry.value
            except Exception as e:
                self.logger.debug(f"Ошибка загрузки английных оригиналов для {mod_id}: {e}")

        self.logger.info(f"Загружено {len(english_originals)} английных оригиналов")
        return english_originals

    def _get_language_folder(self, language: str) -> str:
        """
        Получить название папки языка для поиска в Languages.

        Args:
            language: Название языка ('Russian', 'English', etc.)

        Returns:
            Название папки ('Russian', 'Russian (Русский)', etc.)
        """
        # Стандартные соответствия
        lang_map = {
            "Russian": ["Russian", "Russian (Русский)", "Русский"],
            "English": ["English", "English (English)", "English (US)"],
            "German": ["German", "German (Deutsch)", "Deutsch"],
            "French": ["French", "French (Français)", "Français"],
            "Spanish": ["Spanish", "Spanish (Español)", "Español"],
            "Chinese": ["Chinese", "Chinese (简体中文)", "简体中文"],
            "Japanese": ["Japanese", "Japanese (日本語)", "日本語"],
            "Korean": ["Korean", "Korean (한국어)", "한국어"],
        }

        # Возвращаем первый вариант или сам язык
        return lang_map.get(language, [language])[0]

    # =========================================================================
    # ГЕНЕРАЦИЯ ОТЧЕТОВ
    # =========================================================================

    def generate_report(self, format: str = "text") -> str:
        """
        Генерирует отчет о результатах верификации.

        Args:
            format: Формат отчета ('text', 'json', 'html', 'markdown')

        Returns:
            Строка с отчетом
        """
        data = self.get_report_data()
        return self._report_generator.generate(data, format)

    def save_report(self, output_path: str, format: str = "text") -> bool:
        """
        Генерирует и сохраняет отчет.

        Args:
            output_path: Путь для сохранения
            format: Формат отчета

        Returns:
            True при успехе
        """
        content = self.generate_report(format)
        return self._report_generator.save(content, output_path)

    def get_report_data(self) -> dict:
        """Получить данные для отчета"""
        # Вычисляем статистику
        stats = ReportStatistics()
        stats.total_mods = len(self.results)
        stats.translation_mods = sum(1 for r in self.results if r.is_translation)
        stats.regular_mods = stats.total_mods - stats.translation_mods
        stats.mods_with_errors = sum(1 for r in self.results if not r.is_valid)
        stats.total_errors = sum(len(r.errors) for r in self.results)
        stats.total_warnings = sum(len(r.warnings) for r in self.results)
        stats.total_conflicts = len(self.global_conflicts)

        # Формируем результаты
        results_data = []
        for result in self.results:
            results_data.append(
                {
                    "mod_id": result.mod_id,
                    "mod_name": result.mod_name,
                    "mod_path": result.mod_path,
                    "is_translation": result.is_translation,
                    "parent_mod_id": result.parent_mod_id,
                    "is_valid": result.is_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "conflicts": [str(c) for c in result.conflicts],
                    "checks": [
                        {
                            "name": c.check_name,
                            "passed": c.passed,
                            "severity": c.severity,
                            "message": c.message,
                        }
                        for c in result.checks
                    ],
                }
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "mods_path": self.mods_path,
            "statistics": {
                "total_mods": stats.total_mods,
                "translation_mods": stats.translation_mods,
                "regular_mods": stats.regular_mods,
                "mods_with_errors": stats.mods_with_errors,
                "total_errors": stats.total_errors,
                "total_warnings": stats.total_warnings,
                "total_conflicts": stats.total_conflicts,
            },
            "results": results_data,
            "global_conflicts": [
                {
                    "conflict_type": c.conflict_type.value,
                    "key_or_file": c.key_or_file,
                    "mod_a": c.mod_a,
                    "mod_b": c.mod_b,
                    "severity": c.severity.value,
                    "description": c.description,
                    "resolution": c.resolution,
                }
                for c in self.global_conflicts
            ],
        }

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def _is_translation_mod(self, about_data: dict) -> bool:
        """Определение переводного мода (использует единый модуль классификации)"""
        from utils.mod_classifier import is_translation_mod

        return is_translation_mod(about_data)

    def _notify_error(self, error: str, context: dict) -> None:
        """Уведомление об ошибке"""
        for listener in self.listeners:
            listener.on_error(error, context)

    def get_mod_info(self, mod_id: str) -> dict | None:
        """Получить информацию о моде"""
        return self._mods_cache.get(mod_id)

    def get_results_for_mod(self, mod_id: str) -> VerificationResult | None:
        """Получить результаты верификации для конкретного мода"""
        for result in self.results:
            if result.mod_id == mod_id:
                return result
        return None

    def get_conflicts_for_mod(self, mod_id: str) -> list[ConflictInfo]:
        """Получить конфликты для конкретного мода"""
        conflicts = []
        for conflict in self.global_conflicts:
            if conflict.mod_a == mod_id or conflict.mod_b == mod_id:
                conflicts.append(conflict)
        return conflicts

    def get_statistics(self) -> dict:
        """Получить статистику верификации"""
        return {
            "total_mods": len(self.results),
            "valid_mods": sum(1 for r in self.results if r.is_valid),
            "invalid_mods": sum(1 for r in self.results if not r.is_valid),
            "total_errors": sum(len(r.errors) for r in self.results),
            "total_warnings": sum(len(r.warnings) for r in self.results),
            "total_conflicts": len(self.global_conflicts),
            "checks_registered": len(self.checks),
        }


# ============================================================================
# ФУНКЦИИ ВЫСОКОГО УРОВНЯ
# ============================================================================


def run_verification(
    mods_path: str,
    output_path: str = None,
    format: str = "html",
    language: str = "ru",
    logger: logging.Logger = None,
) -> list[VerificationResult]:
    """
    Удобная функция для запуска верификации.

    Args:
        mods_path: Путь к папке модов
        output_path: Путь для сохранения отчета (опционально)
        format: Формат отчета
        language: Язык валидации
        logger: Логгер

    Returns:
        Список результатов верификации
    """
    coordinator = VerificationCoordinator(mods_path, logger, language)
    results = coordinator.run_verification()

    if output_path:
        coordinator.save_report(output_path, format)

    return results


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование VerificationCoordinator")
    print("=" * 60)

    # Простой тест структуры
    coordinator = VerificationCoordinator("C:/Test/Mods")

    print("\n[ТЕСТ] Создан координатор:")
    print(f"  Путь: {coordinator.mods_path}")
    print(f"  Зарегистрировано проверок: {len(coordinator.checks)}")

    # Выводим имена проверок
    print("\n[ТЕСТ] Зарегистрированные проверки:")
    for check in coordinator.checks:
        print(f"  - {check.name}: {check.description}")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
