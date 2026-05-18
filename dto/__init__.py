# dto/__init__.py
"""
DTO-пакет для изоляции GUI от внутренней логики верификации.

Этот пакет предоставляет плоские DTO-классы и функции маппинга,
которые позволяют GUI работать с данными верификации без прямой
зависимости от внутренних структур модулей verification/.

Пример использования:

    from dto import (
        VerificationResultDTO,
        map_verification_result,
        map_verification_summary,
    )

    # Получение внутренних результатов
    results = coordinator.run_verification()

    # Преобразование для GUI
    dto_results = [map_verification_result(r) for r in results]

    # Использование в GUI
    for dto in dto_results:
        print(f"{dto.mod_name}: {dto.error_count} errors")
"""

# DTO классы
from .verification_dto import (
    # Enum DTO
    SeverityDTO,
    ConflictTypeDTO,
    QualityLevelDTO,
    
    # Основные DTO
    ModInfoDTO,
    ConflictDTO,
    ValidationIssueDTO,
    ValidationResultDTO,
    CheckResultDTO,
    DependencyIssueDTO,
    VerificationResultDTO,
    VerificationSummaryDTO,
)

# Функции маппинга
from .mappers import (
    # Маппинг конфликтов
    map_conflict,
    map_conflicts,
    
    # Маппинг валидации
    map_validation_issue,
    map_validation_issues,
    map_validation_result,
    map_validation_results,
    
    # Маппинг проверок
    map_check_result,
    map_check_results,
    
    # Маппинг зависимостей
    map_dependency_issue,
    map_dependency_issues,
    
    # Маппинг результатов верификации
    map_verification_result,
    map_verification_results,
    
    # Маппинг сводки
    map_verification_summary,
    
    # Утилиты
    create_mod_info_dto,
)

__all__ = [
    # Enum DTO
    'SeverityDTO',
    'ConflictTypeDTO',
    'QualityLevelDTO',
    
    # DTO классы
    'ModInfoDTO',
    'ConflictDTO',
    'ValidationIssueDTO',
    'ValidationResultDTO',
    'CheckResultDTO',
    'DependencyIssueDTO',
    'VerificationResultDTO',
    'VerificationSummaryDTO',
    
    # Маппинг конфликтов
    'map_conflict',
    'map_conflicts',
    
    # Маппинг валидации
    'map_validation_issue',
    'map_validation_issues',
    'map_validation_result',
    'map_validation_results',
    
    # Маппинг проверок
    'map_check_result',
    'map_check_results',
    
    # Маппинг зависимостей
    'map_dependency_issue',
    'map_dependency_issues',
    
    # Маппинг результатов верификации
    'map_verification_result',
    'map_verification_results',
    
    # Маппинг сводки
    'map_verification_summary',
    
    # Утилиты
    'create_mod_info_dto',
]

__version__ = '1.0.0'
