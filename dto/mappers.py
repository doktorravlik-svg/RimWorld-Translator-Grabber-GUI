# dto/mappers.py
"""
Функции маппинга между внутренними моделями verification и DTO.

Эти функции преобразуют сложные структуры данных модулей verification
в простые DTO-классы для использования в GUI.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

# Импорт DTO
from .verification_dto import (
    VerificationResultDTO,
    ConflictDTO,
    ValidationIssueDTO,
    ValidationResultDTO,
    CheckResultDTO,
    DependencyIssueDTO,
    ModInfoDTO,
    VerificationSummaryDTO,
)

# Импорт внутренних моделей verification (обратная совместимость)
from verification import (
    VerificationResult,
    ConflictInfo,
    ValidationIssue,
    ValidationResult as ValidationResultInternal,
    CheckResult,
    DependencyCheckResult,
)


# ============================================================================
# МАППЕРЫ КОНФЛИКТОВ
# ============================================================================

def map_conflict(conflict: ConflictInfo) -> ConflictDTO:
    """
    Преобразует ConflictInfo в ConflictDTO.
    
    Args:
        conflict: Внутренняя модель ConflictInfo
        
    Returns:
        ConflictDTO - DTO представление конфликта
    """
    return ConflictDTO(
        conflict_type=conflict.conflict_type.value,
        key_or_file=conflict.key_or_file,
        mod_a=conflict.mod_a,
        mod_b=conflict.mod_b,
        severity=conflict.severity.value,
        description=conflict.description,
        resolution=conflict.resolution,
        affected_keys=conflict.affected_keys,
        file_paths=conflict.file_paths,
    )


def map_conflicts(conflicts: List[ConflictInfo]) -> List[ConflictDTO]:
    """
    Преобразует список ConflictInfo в список ConflictDTO.
    
    Args:
        conflicts: Список внутренних моделей ConflictInfo
        
    Returns:
        List[ConflictDTO] - список DTO представлений конфликтов
    """
    return [map_conflict(c) for c in conflicts]


# ============================================================================
# МАППЕРЫ ВАЛИДАЦИИ
# ============================================================================

def map_validation_issue(issue: ValidationIssue) -> ValidationIssueDTO:
    """
    Преобразует ValidationIssue в ValidationIssueDTO.
    
    Args:
        issue: Внутренняя модель ValidationIssue
        
    Returns:
        ValidationIssueDTO - DTO представление проблемы валидации
    """
    return ValidationIssueDTO(
        severity=issue.severity.value,
        code=issue.code,
        message=issue.message,
        context=issue.context,
        position=issue.position,
    )


def map_validation_issues(issues: List[ValidationIssue]) -> List[ValidationIssueDTO]:
    """
    Преобразует список ValidationIssue в список ValidationIssueDTO.
    """
    return [map_validation_issue(i) for i in issues]


def map_validation_result(result: ValidationResultInternal) -> ValidationResultDTO:
    """
    Преобразует ValidationResult в ValidationResultDTO.
    
    Args:
        result: Внутренняя модель ValidationResult
        
    Returns:
        ValidationResultDTO - DTO представление результата валидации
    """
    return ValidationResultDTO(
        key=result.key,
        original=result.original,
        translated=result.translated,
        is_valid=result.is_valid,
        issues=map_validation_issues(result.issues),
        quality_score=result.quality_score,
        quality_level=result.quality_level.value,
    )


def map_validation_results(results: List[ValidationResultInternal]) -> List[ValidationResultDTO]:
    """
    Преобразует список ValidationResult в список ValidationResultDTO.
    """
    return [map_validation_result(r) for r in results]


# ============================================================================
# МАППЕРЫ ПРОВЕРОК
# ============================================================================

def map_check_result(check: CheckResult) -> CheckResultDTO:
    """
    Преобразует CheckResult в CheckResultDTO.
    
    Args:
        check: Внутренняя модель CheckResult
        
    Returns:
        CheckResultDTO - DTO представление результата проверки
    """
    return CheckResultDTO(
        check_name=check.check_name,
        passed=check.passed,
        severity=check.severity,
        message=check.message,
        details=check.details,
    )


def map_check_results(checks: List[CheckResult]) -> List[CheckResultDTO]:
    """
    Преобразует список CheckResult в список CheckResultDTO.
    """
    return [map_check_result(c) for c in checks]


# ============================================================================
# МАППЕРЫ ЗАВИСИМОСТЕЙ
# ============================================================================

def map_dependency_issue(dep: DependencyCheckResult) -> DependencyIssueDTO:
    """
    Преобразует DependencyCheckResult в DependencyIssueDTO.
    
    Args:
        dep: Внутренняя модель DependencyCheckResult
        
    Returns:
        DependencyIssueDTO - DTO представление проблемы с зависимостью
    """
    return DependencyIssueDTO(
        package_id=dep.package_id,
        severity=dep.severity.value,
        dependency_type=dep.dependency_type.value,
        message=dep.message,
        is_resolved=dep.is_resolved,
        installed_version=dep.installed_version,
        required_version=dep.required_version,
    )


def map_dependency_issues(deps: List[DependencyCheckResult]) -> List[DependencyIssueDTO]:
    """
    Преобразует список DependencyCheckResult в список DependencyIssueDTO.
    """
    return [map_dependency_issue(d) for d in deps]


# ============================================================================
# МАППЕРЫ РЕЗУЛЬТАТОВ ВЕРИФИКАЦИИ
# ============================================================================

def map_verification_result(result: VerificationResult) -> VerificationResultDTO:
    """
    Преобразует VerificationResult в VerificationResultDTO.
    
    Основная функция маппинга результатов верификации мода.
    
    Args:
        result: Внутренняя модель VerificationResult
        
    Returns:
        VerificationResultDTO - DTO представление результата верификации
    """
    # Подсчитываем статистику
    error_count = len(result.errors)
    warning_count = len(result.warnings)
    conflict_count = len(result.conflicts)
    validation_issue_count = sum(
        len(vr.issues) for vr in result.validation_results
    )
    checks_passed = sum(1 for c in result.checks if c.passed)
    checks_failed = sum(1 for c in result.checks if not c.passed)
    
    return VerificationResultDTO(
        # Идентификация
        mod_id=result.mod_id,
        mod_name=result.mod_name,
        mod_path=result.mod_path,
        is_translation=result.is_translation,
        parent_mod_id=result.parent_mod_id,
        
        # Статус
        is_valid=result.is_valid,
        validated_at=result.validated_at,
        
        # Результаты проверок
        check_results=map_check_results(result.checks),
        
        # Конфликты
        conflicts=map_conflicts(result.conflicts),
        
        # Результаты валидации переводов
        validation_results=map_validation_results(result.validation_results),
        
        # Списки ошибок и предупреждений
        errors=result.errors,
        warnings=result.warnings,
        files_with_errors=result.files_with_errors if hasattr(result, 'files_with_errors') else [],

        # Зависимости (заполняется отдельно если нужно)
        dependency_issues=[],
        
        # Статистика
        error_count=error_count,
        warning_count=warning_count,
        conflict_count=conflict_count,
        validation_issue_count=validation_issue_count,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
    )


def map_verification_results(results: List[VerificationResult]) -> List[VerificationResultDTO]:
    """
    Преобразует список VerificationResult в список VerificationResultDTO.
    
    Args:
        results: Список внутренних моделей VerificationResult
        
    Returns:
        List[VerificationResultDTO] - список DTO результатов верификации
    """
    return [map_verification_result(r) for r in results]


# ============================================================================
# МАППЕРЫ СВОДКИ
# ============================================================================

def map_verification_summary(
    results: List[VerificationResult],
    global_conflicts: Optional[List[ConflictInfo]] = None,
    mods_path: str = ""
) -> VerificationSummaryDTO:
    """
    Преобразует результаты верификации в сводку.
    
    Args:
        results: Список результатов верификации
        global_conflicts: Список глобальных конфликтов
        mods_path: Путь к директории модов
        
    Returns:
        VerificationSummaryDTO - сводка по верификации
    """
    if global_conflicts is None:
        global_conflicts = []
    
    # Вычисляем статистику
    total_mods = len(results)
    translation_mods = sum(1 for r in results if r.is_translation)
    regular_mods = total_mods - translation_mods
    mods_with_errors = sum(1 for r in results if not r.is_valid)
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    total_conflicts = sum(len(r.conflicts) for r in results) + len(global_conflicts)
    validation_issues = sum(
        len(vr.issues) for r in results for vr in r.validation_results
    )
    
    # Преобразуем результаты
    dto_results = map_verification_results(results)
    
    # Преобразуем глобальные конфликты
    dto_global_conflicts = map_conflicts(global_conflicts)
    
    # Вычисляем is_valid
    is_valid = (mods_with_errors == 0 and len(global_conflicts) == 0)

    return VerificationSummaryDTO(
        total_mods=total_mods,
        translation_mods=translation_mods,
        regular_mods=regular_mods,
        mods_with_errors=mods_with_errors,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_conflicts=total_conflicts,
        validation_issues=validation_issues,
        is_valid=is_valid,

        results=dto_results,
        global_conflicts=dto_global_conflicts,
    )


# ============================================================================
# УТИЛИТЫ
# ============================================================================

def create_mod_info_dto(
    mod_id: str,
    mod_name: str,
    mod_path: str,
    is_translation: bool = False,
    parent_mod_id: Optional[str] = None,
    version: Optional[str] = None,
    supported_languages: Optional[List[str]] = None,
) -> ModInfoDTO:
    """
    Создает ModInfoDTO из переданных данных.
    
    Утилита для создания DTO информации о моде.
    
    Args:
        mod_id: ID мода
        mod_name: Название мода
        mod_path: Путь к моду
        is_translation: Является ли мод переводом
        parent_mod_id: ID родительского мода (для переводов)
        version: Версия мода
        supported_languages: Поддерживаемые языки
        
    Returns:
        ModInfoDTO - DTO представление информации о моде
    """
    return ModInfoDTO(
        mod_id=mod_id,
        mod_name=mod_name,
        mod_path=mod_path,
        is_translation=is_translation,
        parent_mod_id=parent_mod_id,
        version=version,
        supported_languages=supported_languages or [],
    )
