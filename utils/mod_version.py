"""
Утилита для получения версии мода из About.xml
"""

import os
import lxml.etree as etree
from verification.xml_parser import safe_parse_xml


def get_mod_version(mod_path: str) -> str | None:
    """
    Извлекает версию мода из About/About.xml.

    Args:
        mod_path: Путь к папке мода

    Returns:
        Версия мода (например "1.6.0") или None
    """
    about_file = os.path.join(mod_path, "About", "About.xml")
    if not os.path.exists(about_file):
        # Проверяем корневую папку
        about_file = os.path.join(mod_path, "About.xml")
        if not os.path.exists(about_file):
            return None

    try:
        root = safe_parse_xml(about_file)
        if root is None:
            return None

        # Ищем version
        for version_tag in root.iter("version"):
            if version_tag.text:
                return version_tag.text.strip()

        # Ищем modVersion
        for version_tag in root.iter("modVersion"):
            if version_tag.text:
                return version_tag.text.strip()

        # Ищем packageId (если нет версии)
        for package_id_tag in root.iter("packageId"):
            if package_id_tag.text:
                return f"PackageID: {package_id_tag.text.strip()}"

    except Exception:
        pass

    return None


def get_mod_name(mod_path: str) -> str:
    """
    Извлекает имя мода из About/About.xml.

    Args:
        mod_path: Путь к папке мода

    Returns:
        Имя мода или название папки
    """
    about_file = os.path.join(mod_path, "About", "About.xml")
    if not os.path.exists(about_file):
        about_file = os.path.join(mod_path, "About.xml")
        if not os.path.exists(about_file):
            return sanitize_folder_name(os.path.basename(mod_path))

    try:
        root = safe_parse_xml(about_file)
        if root is None:
            return sanitize_folder_name(os.path.basename(mod_path))

        name_elem = root.find("name")
        if name_elem is not None and name_elem.text:
            return sanitize_folder_name(name_elem.text.strip())

    except Exception:
        pass

    return sanitize_folder_name(os.path.basename(mod_path))


def sanitize_folder_name(name: str) -> str:
    """
    Очищает имя для использования в качестве имени папки.
    Удаляет недопустимые символы: / \\ : * ? " < > |

    Args:
        name: Исходное имя

    Returns:
        Очищенное имя, безопасное для использования в пути
    """
    import re
    # Заменяем недопустимые символы на _
    sanitized = re.sub(r'[\\/*?:"<>|]', '_', name)
    # Удаляем лишние пробелы и _ в начале и конце
    sanitized = sanitized.strip().strip('_')
    # Если имя пустое после очистки, возвращаем дефолтное
    if not sanitized:
        return "Mod"
    return sanitized
