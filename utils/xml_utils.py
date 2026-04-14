# utils/xml_utils.py
"""
Утилиты для работы с XML.

Единый модуль для парсинга, создания и модификации XML файлов.
Делегирует verification/xml_parser.py для основной функциональности.
"""

import os
import xml.etree.ElementTree as ET
from typing import Optional

# Импортируем основные функции из verification/xml_parser.py
from verification.xml_parser import (
    safe_parse_xml,
    parse_xml_file,
    XMLParser,
    XMLParseResult,
    write_tree_pretty,
    add_or_preserve,
    get_entries_from_xml,
    detect_xml_file_type,
    validate_xml_structure,
)


def read_xml_text(file_path: str) -> Optional[ET.ElementTree]:
    """
    Читает XML файл и возвращает ElementTree.
    
    Args:
        file_path: Путь к XML файлу
    
    Returns:
        ElementTree или None при ошибке
    """
    return parse_xml_file(file_path)


def write_xml_text(tree: ET.ElementTree, file_path: str) -> bool:
    """
    Записывает XML дерево в файл с красивым форматированием.
    
    Args:
        tree: XML ElementTree
        file_path: Путь для записи
    
    Returns:
        True при успехе, False при ошибке
    """
    return write_tree_pretty(tree, file_path)


def safe_copy_xml(source_path: str, dest_path: str) -> bool:
    """
    Копирует XML файл с сохранением структуры.
    
    Args:
        source_path: Путь к исходному файлу
        dest_path: Путь к целевому файлу
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        tree = parse_xml_file(source_path)
        if tree is not None:
            return write_tree_pretty(tree, dest_path)
        return False
    except Exception:
        return False


def get_xml_entries(file_path: str) -> dict[str, str]:
    """
    Извлекает все записи (ключ -> значение) из XML файла.
    
    Args:
        file_path: Путь к XML файлу
    
    Returns:
        Словарь {ключ: значение}
    """
    root = safe_parse_xml(file_path)
    if root is None:
        return {}
    return get_entries_from_xml(root)


def create_keyed_xml(entries: dict[str, str], file_path: str) -> bool:
    """
    Создаёт Keyed XML файл из словаря.
    
    Args:
        entries: Словарь {ключ: значение}
        file_path: Путь для записи
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        root = ET.Element("Keyed")
        for key, value in entries.items():
            elem = ET.SubElement(root, key)
            elem.text = value
        
        tree = ET.ElementTree(root)
        return write_tree_pretty(tree, file_path)
    except Exception:
        return False


def safe_walk(*args, **kwargs):
    """
    Безопасный walk для XML элементов (обратная совместимость).
    """
    return ET.ElementTree(*args).getroot()
