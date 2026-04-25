# per_def_utils.py
"""
Вспомогательные функции для генерации DefInjected файлов.
Выделено из per_def.py для соблюдения лимита строк (80 на функцию/файл).
"""

import os
import lxml.etree as etree

from translation.obsolete_detector import process_obsolete_tags
from verification.xml_parser import (
    add_or_preserve,
    get_xml_content_hash,
    safe_parse_xml,
    write_tree_pretty,
)


def ensure_dir(path: str) -> None:
    """Создает папку, если она не существует."""
    if not os.path.exists(path):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        os.makedirs(path, exist_ok=True)


def find_matching_translation_file(
    target_dir: str, def_name: str, tagname: str, logger=None
) -> str | None:
    """
    Ищет существующий файл перевода с отличающимся именем, который содержит нужный тег.

    Returns:
        path к найденному файлу или None
    """
    if not os.path.exists(target_dir):
        return None

    for filename in os.listdir(target_dir):
        if not filename.endswith(".xml"):
            continue

        filepath = os.path.join(target_dir, filename)
        try:
            root = safe_parse_xml(filepath)
            if root is None:
                continue

            for child in root:
                if child.tag == tagname or child.tag.startswith(tagname.split(".")[0] + "."):
                    if logger:
                        logger.debug(f"Found matching tag {tagname} in {filename}")
                    return filepath
        except Exception as e:
            if logger:
                logger.debug(f"Error reading {filepath}: {e}")

    return None


def scan_existing_translations(target_dir: str, logger=None) -> dict[str, str]:
    """
    Сканирует папку и создает карту: тег -> файл.

    Returns:
        dict: {tagname: filepath}
    """
    tag_to_file: dict[str, str] = {}

    if not os.path.exists(target_dir):
        return tag_to_file

    for root_dir, _dirs, files in os.walk(target_dir):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root_dir, filename)
            try:
                root = safe_parse_xml(filepath)
                if root is None:
                    continue

                for child in root:
                    if child.tag and child.tag not in ("LanguageData", "Keyed"):
                        tag_to_file[child.tag] = filepath
            except Exception as e:
                if logger:
                    logger.debug(f"Error scanning {filepath}: {e}")

    return tag_to_file


def cleanup_orphan_translations(
    target_dir: str, created_files: list[str], logger=None
) -> list[str]:
    """
    Удаляет осиротевшие файлы переводов, которые не соответствуют оригинальным Def файлам.

    Args:
        target_dir: папка DefInjected
        created_files: список файлов, которые были созданы/обновлены

    Returns:
        Список осиротевших файлов
    """
    if not os.path.exists(target_dir):
        return []

    # Карта: имя файла без .xml -> путь
    valid_files = set()
    for f in created_files:
        basename = os.path.basename(f)
        if basename.endswith(".xml"):
            valid_files.add(basename)

    orphans = []
    for root_dir, _dirs, files in os.walk(target_dir):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            if filename not in valid_files:
                filepath = os.path.join(root_dir, filename)
                orphans.append(filepath)
                if logger:
                    logger.debug(f"Orphan file found: {filepath}")

    return orphans
