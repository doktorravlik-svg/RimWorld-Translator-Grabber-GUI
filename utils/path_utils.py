# utils/path_utils.py
"""
Утилиты для работы с путями.

Единый модуль для получения корневой директории проекта
и добавления её в sys.path.
"""

import os
import sys


def get_project_root() -> str:
    """
    Возвращает абсолютный путь к корневой директории проекта.

    Returns:
        Абсолютный путь к корню проекта
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_project_root_in_path() -> None:
    """
    Добавляет корневую директорию проекта в sys.path,
    если её там ещё нет.

    Это необходимо для работы импортов из корня проекта.
    """
    project_root = get_project_root()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def change_to_project_root() -> None:
    """
    Меняет текущую директорию на корень проекта.
    """
    os.chdir(get_project_root())
