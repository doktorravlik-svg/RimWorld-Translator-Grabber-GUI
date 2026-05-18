# verification/__init__.py
"""
Система верификации переводов RimWorld модов.

Модульная архитектура для проверки и валидации переводов модов RimWorld.

Основные модули:
- xml_parser: Парсинг XML файлов переводов
- dependency_checker: Проверка зависимостей между модами
- conflict_detector: Обнаружение конфликтов переводов
- translation_validator: Валидация качества переводов
- report_generator: Генерация отчетов
- verification_coordinator: Центральный координатор системы

Пример использования:
    from verification import VerificationCoordinator, ReportGenerator

    # Запуск верификации
    coordinator = VerificationCoordinator("C:/RimWorld/Mods")
    results = coordinator.run_verification()

    # Генерация отчета
    generator = ReportGenerator()
    report = generator.generate(coordinator.get_report_data(), 'html')
"""

# Импорты базовых модулей
from .conflict_detector import (
    ConflictDetector,
    ConflictInfo,
    ConflictSeverity,
    ConflictType,
    ResolutionStrategy,
    TranslationEntry,
    detect_translation_conflicts,
    find_duplicate_keys,
)
from .dependency_checker import (
    DependencyChecker,
    DependencyCheckResult,
    DependencyInfo,
    DependencySeverity,
    DependencyType,
    ModDependencyReport,
    check_mod_dependencies,
    find_missing_dependencies,
    verify_version_compatibility,
)
from .report_generator import (
    ReportGenerator,
    ReportSection,
    ReportStatistics,
    generate_html_report,
    generate_json_report,
    generate_markdown_report,
    generate_text_report,
)

# Translation Status Checker
from .translation_status_checker import (
    TranslationDependencyInfo,
    TranslationDependencyReport,
    TranslationStatus,
    TranslationStatusChecker,
    TranslationType,
    check_translation_statuses,
    get_translation_tree,
)
from .translation_validator import (
    QualityLevel,
    TranslationValidationReport,
    TranslationValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    check_translation_quality_detailed,
    validate_newlines,
    validate_placeholders,
)

# Центральный координатор
from .verification_coordinator import (
    CheckResult,
    VerificationCheck,
    VerificationCoordinator,
    VerificationListener,
    VerificationResult,
    run_verification,
)
from .xml_parser import (
    XMLParser,
    detect_xml_file_type,
    find_duplicate_xml_files,
    get_entries_from_xml,
    get_xml_content_hash,
    parse_xml_file,
    safe_parse_xml,
    validate_xml_structure,
    write_tree_pretty,
)

__all__ = [
    # XML Parser
    "XMLParser",
    "safe_parse_xml",
    "parse_xml_file",
    "validate_xml_structure",
    "write_tree_pretty",
    "get_xml_content_hash",
    "find_duplicate_xml_files",
    "get_entries_from_xml",
    "detect_xml_file_type",
    # Dependency Checker
    "DependencyChecker",
    "DependencyInfo",
    "DependencyCheckResult",
    "ModDependencyReport",
    "check_mod_dependencies",
    "find_missing_dependencies",
    "verify_version_compatibility",
    "DependencySeverity",
    "DependencyType",
    # Conflict Detector
    "ConflictDetector",
    "ConflictInfo",
    "TranslationEntry",
    "detect_translation_conflicts",
    "find_duplicate_keys",
    "ConflictType",
    "ConflictSeverity",
    "ResolutionStrategy",
    # Translation Validator
    "TranslationValidator",
    "ValidationResult",
    "ValidationIssue",
    "TranslationValidationReport",
    "validate_placeholders",
    "validate_newlines",
    "check_translation_quality_detailed",
    "ValidationSeverity",
    "QualityLevel",
    # Report Generator
    "ReportGenerator",
    "ReportStatistics",
    "ReportSection",
    "generate_text_report",
    "generate_json_report",
    "generate_html_report",
    "generate_markdown_report",
    # Verification Coordinator
    "VerificationCoordinator",
    "VerificationListener",
    "VerificationCheck",
    "VerificationResult",
    "CheckResult",
    "run_verification",
    # Translation Status Checker
    "TranslationStatusChecker",
    "TranslationStatus",
    "TranslationType",
    "TranslationDependencyInfo",
    "TranslationDependencyReport",
    "check_translation_statuses",
    "get_translation_tree",
]

__version__ = "1.0.0"
