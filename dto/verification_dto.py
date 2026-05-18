# dto/verification_dto.py
"""
DTO-классы для изоляции GUI от внутренней логики верификации.

Эти классы предоставляют плоский API для GUI, скрывая внутреннюю
структуру модулей verification/.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ============================================================================
# ENUM DTO
# ============================================================================

class SeverityDTO(str, Enum):
    """DTO для уровня серьёзности"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ConflictTypeDTO(str, Enum):
    """DTO для типа конфликта"""
    DUPLICATE_KEY = "duplicate_key"
    MISSING_PARENT = "missing_parent"
    VERSION_MISMATCH = "version_mismatch"
    TRANSLATION_MISSING = "translation_missing"
    TRANSLATION_CONFLICT = "translation_conflict"


class QualityLevelDTO(str, Enum):
    """DTO для уровня качества перевода"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


# ============================================================================
# ОСНОВНЫЕ DTO КЛАССЫ
# ============================================================================

@dataclass
class ModInfoDTO:
    """
    DTO - информация о моде.

    Используется для передачи базовой информации о моде в GUI.
    """
    mod_id: str
    mod_name: str
    mod_path: str
    is_translation: bool
    parent_mod_id: Optional[str] = None
    version: Optional[str] = None
    supported_languages: List[str] = field(default_factory=list)


@dataclass
class ConflictDTO:
    """
    DTO - конфликт перевода.

    Плоское представление конфликта для GUI.
    """
    conflict_type: str
    key_or_file: str
    mod_a: str
    mod_b: str
    severity: str
    description: str
    resolution: Optional[str] = None
    affected_keys: List[str] = field(default_factory=list)
    file_paths: List[str] = field(default_factory=list)


@dataclass
class ValidationIssueDTO:
    """
    DTO - проблема валидации.

    Плоское представление проблемы валидации перевода.
    """
    severity: str
    code: str
    message: str
    context: Optional[str] = None
    position: Optional[int] = None


@dataclass
class ValidationResultDTO:
    """
    DTO - результат валидации перевода.

    Содержит результаты валидации одной записи перевода.
    """
    key: str
    original: str
    translated: str
    is_valid: bool
    issues: List[ValidationIssueDTO] = field(default_factory=list)
    quality_score: float = 0.0
    quality_level: str = "good"


@dataclass
class CheckResultDTO:
    """
    DTO - результат проверки верификации.

    Представляет результат отдельной проверки (About.xml, зависимости и т.д.).
    """
    check_name: str
    passed: bool
    severity: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyIssueDTO:
    """
    DTO - проблема с зависимостью мода.
    """
    package_id: str
    severity: str
    dependency_type: str
    message: str
    is_resolved: bool = True
    installed_version: Optional[str] = None
    required_version: Optional[str] = None


@dataclass
class VerificationResultDTO:
    """
    DTO - результат верификации мода.

    Основной DTO класс, агрегирующий все результаты верификации.
    Плоский и простой для использования в GUI.
    """
    # Идентификация
    mod_id: str
    mod_name: str
    mod_path: str
    is_translation: bool
    parent_mod_id: Optional[str] = None
    
    # Статус
    is_valid: bool = True
    validated_at: str = ""
    
    # Результаты проверок
    check_results: List[CheckResultDTO] = field(default_factory=list)
    
    # Конфликты
    conflicts: List[ConflictDTO] = field(default_factory=list)
    
    # Результаты валидации переводов
    validation_results: List[ValidationResultDTO] = field(default_factory=list)
    
    # Списки ошибок и предупреждений (для простого отображения)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files_with_errors: List[str] = field(default_factory=list)  # Файлы с ошибками

    # Зависимости
    dependency_issues: List[DependencyIssueDTO] = field(default_factory=list)
    
    # Статистика
    error_count: int = 0
    warning_count: int = 0
    conflict_count: int = 0
    validation_issue_count: int = 0
    checks_passed: int = 0
    checks_failed: int = 0


@dataclass
class VerificationSummaryDTO:
    """
    DTO - сводка по всей верификации.

    Используется для отображения общей статистики верификации.
    """
    total_mods: int = 0
    translation_mods: int = 0
    regular_mods: int = 0
    mods_with_errors: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_conflicts: int = 0
    validation_issues: int = 0
    is_valid: bool = True  # Флаг валидности общей верификации

    # Список модов с результатами
    results: List[VerificationResultDTO] = field(default_factory=list)

    # Глобальные конфликты
    global_conflicts: List[ConflictDTO] = field(default_factory=list)
