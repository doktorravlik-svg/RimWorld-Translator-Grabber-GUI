# per_def.py
# Основной модуль генерации DefInjected файлов.
# Является точкой входа для обратной совместимости.
# Функционал разбит на перенаправления:
# - per_def_utils.py: вспомогательные функции
# - per_def_generator.py: основная логика генерации

from translation.per_def_generator import generate_or_update_per_def_files_v2
from translation.per_def_utils import (
    cleanup_orphan_translations,
    ensure_dir,
    find_matching_translation_file,
    scan_existing_translations,
)

__all__ = [
    "generate_or_update_per_def_files_v2",
    "ensure_dir",
    "find_matching_translation_file",
    "scan_existing_translations",
    "cleanup_orphan_translations",
]
