# folder_utils.py
"""
Общий модуль для поиска папок в модах RimWorld.

⚠️ ДЕЛЕГИРОВАНИЕ: Большинство функций теперь делегируют
в utils.languages_path_resolver для единообразия.

Этот файл сохраняется для обратной совместимости.
"""

# ✅ Импортируем из нового модуля
from utils.languages_path_resolver import (
    SUPPORTED_VERSIONS,
)
from utils.languages_path_resolver import (
    find_all_defs_folders as find_defs_folders,
)
from utils.languages_path_resolver import (
    find_all_language_folders as find_language_folders,
)

# Псевдонимы для обратной совместимости
PRIORITY_VERSIONS = SUPPORTED_VERSIONS


def has_defs_folder(mod_path: str) -> bool:
    """Проверяет наличие папки Defs в моде."""
    return len(find_defs_folders(mod_path)) > 0


def get_first_language_folder(mod_path: str, lang_name: str) -> str | None:
    """Возвращает первую найденную папку с языком."""
    folders = find_language_folders(mod_path, lang_name)
    return folders[0] if folders else None


def get_first_defs_folder(mod_path: str) -> str | None:
    """Возвращает первую найденную папку Defs."""
    folders = find_defs_folders(mod_path)
    return folders[0] if folders else None
