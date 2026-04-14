"""
Утилита для получения версии мода из About.xml
"""

import os
import xml.etree.ElementTree as ET


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
        tree = ET.parse(about_file)
        root = tree.getroot()

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
            return os.path.basename(mod_path)

    try:
        tree = ET.parse(about_file)
        root = tree.getroot()

        for name_tag in root.iter("name"):
            if name_tag.text:
                return name_tag.text.strip()

    except Exception:
        pass

    return os.path.basename(mod_path)
