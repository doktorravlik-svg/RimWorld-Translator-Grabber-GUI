# utils/json_utils.py
"""
Утилиты для работы с JSON файлами.

Единый модуль для чтения и записи JSON с обработкой ошибок.
"""

import json
import os
from typing import Any, Optional


def load_json_file(file_path: str, default: Any = None) -> Any:
    """
    Загружает JSON файл.
    
    Args:
        file_path: Путь к JSON файлу
        default: Значение по умолчанию при ошибке
    
    Returns:
    Распакованные JSON данные или default при ошибке
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON {file_path}: {e}")
        return default
    except Exception as e:
        print(f"Ошибка чтения JSON {file_path}: {e}")
        return default


def save_json_file(file_path: str, data: Any, indent: int = 2, ensure_ascii: bool = False) -> bool:
    """
    Сохраняет данные в JSON файл.
    
    Args:
        file_path: Путь к JSON файлу
        data: Данные для сохранения
        indent: Отступ для форматирования
        ensure_ascii: Экранировать не-ASCII символы
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        # Создаём директорию если нужно
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        return True
    except Exception as e:
        print(f"Ошибка записи JSON {file_path}: {e}")
        return False


def update_json_file(file_path: str, updates: dict, merge: bool = True) -> bool:
    """
    Обновляет JSON файл новыми данными.
    
    Args:
        file_path: Путь к JSON файлу
        updates: Словарь с обновлениями
        merge: Объединять данные (True) или перезаписывать (False)
    
    Returns:
        True при успехе, False при ошибке
    """
    if merge:
        existing = load_json_file(file_path, default={})
        if not isinstance(existing, dict):
            existing = {}
        existing.update(updates)
        data = existing
    else:
        data = updates
    
    return save_json_file(file_path, data)


def merge_json_files(file_paths: list[str], output_path: str, deep_merge: bool = False) -> bool:
    """
    Объединяет несколько JSON файлов в один.
    
    Args:
        file_paths: Список путей к файлам
        output_path: Путь к выходному файлу
        deep_merge: Глубокое объединение словарей
    
    Returns:
        True при успехе, False при ошибке
    """
    merged = {}
    
    for path in file_paths:
        data = load_json_file(path)
        if data is None:
            continue
        
        if isinstance(data, dict):
            if deep_merge:
                merged = _deep_merge(merged, data)
            else:
                merged.update(data)
        elif isinstance(data, list):
            if isinstance(merged, list):
                merged.extend(data)
            else:
                merged = data
        else:
            # Простые значения - последний wins
            merged = data
    
    return save_json_file(output_path, merged)


def _deep_merge(dict1: dict, dict2: dict) -> dict:
    """Глубокое объединение двух словарей."""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def json_to_dict(json_string: str, default: Optional[dict] = None) -> dict:
    """
    Парсит JSON строку в словарь.
    
    Args:
        json_string: JSON строка
        default: Значение по умолчанию
    
    Returns:
        Словарь или default при ошибке
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return default or {}


def dict_to_json_string(data: dict, indent: Optional[int] = None) -> str:
    """
    Сериализует словарь в JSON строку.
    
    Args:
        data: Словарь
        indent: Отступ для форматирования (None = компактный)
    
    Returns:
        JSON строка
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)
