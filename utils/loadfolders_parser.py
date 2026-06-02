"""
Парсер LoadFolders.xml - определяет реальные пути контента мода.

Поддерживает:
- LoadFolders.xml с версиями (v1.4, v1.5, v1.6)
- Условную загрузку (IfModActive, IfModNotActive, IfModActiveAll)
- Корневую директиву (/)
- Папку Common/

Пример LoadFolders.xml:
    <loadFolders>
        <v1.5>
            <li>Common</li>
            <li>1.5</li>
        </v1.5>
        <v1.6>
            <li>Common</li>
            <li>1.6</li>
        </v1.6>
    </loadFolders>
"""

import os
import lxml.etree as etree
from verification.xml_parser import safe_parse_xml

# Версии для которых ищем LoadFolders
SUPPORTED_VERSIONS = ["1.6", "1.5", "1.4", "1.3"]


def parse_loadfolders(mod_path: str, target_version: str = None) -> list[str]:
    """
    Парсит LoadFolders.xml и возвращает список папок контента.

    Args:
        mod_path: Путь к моду
        target_version: Целевая версия (например "1.6"). Если None - определяет автоматически.

    Returns:
        Список папок контента (например ["Common", "1.6"])
    """
    loadfolders_path = os.path.join(mod_path, "LoadFolders.xml")
    if not os.path.exists(loadfolders_path):
        return []

    try:
        root = safe_parse_xml(loadfolders_path)
        if root is None:
            return []
    except Exception:
        return []

    # Определяем целевую версию
    if target_version is None:
        target_version = _detect_version(mod_path)

    # Ищем секцию для целевой версии
    for version_tag in [f"v{target_version}"]:
        version_elem = root.find(version_tag)
        if version_elem is not None:
            folders = []
            for li in version_elem.findall("li"):
                if li.text:
                    folder = li.text.strip()
                    # "/" означает корневую директорию мода
                    if folder == "/":
                        folders.append("")
                    else:
                        folders.append(folder)
            return folders

    # Если не нашли секцию для версии - пробуем любую
    for child in root:
        if child.tag.startswith("v"):
            folders = []
            for li in child.findall("li"):
                if li.text:
                    folder = li.text.strip()
                    if folder == "/":
                        folders.append("")
                    else:
                        folders.append(folder)
            return folders

    return []


def _find_all_defs_folders_universal(mod_path: str) -> list[str]:
    """
    Универсальный поиск всех папок Defs в моде (как Text-grabber).

    Сканирует ВСЕ папки в корне мода и ищет Defs в каждой.
    Поддерживает: Common/Defs, 1.6/Defs, Assemblies/Defs, Compatabilities/*/Defs, и т.д.

    Оптимизировано:
    - Использует set для отслеживания уже найденных путей
    - Объединены вложенные сканирования
    """
    defs_folders = set()

    if not os.path.exists(mod_path):
        return list(defs_folders)

    for item in os.listdir(mod_path):
        item_path = os.path.join(mod_path, item)
        if not os.path.isdir(item_path):
            continue

        # Пропускаем скрытые папки
        if item.startswith(".") or item.startswith("$"):
            continue

        # Проверяем наличие Defs в этой папке
        defs_path = os.path.join(item_path, "Defs")
        if os.path.exists(defs_path):
            defs_folders.add(defs_path)

        # Проверяем вложенные папки (например Compatabilities/CE/Defs)
        try:
            for sub_item in os.listdir(item_path):
                sub_path = os.path.join(item_path, sub_item)
                if os.path.isdir(sub_path) and not sub_item.startswith((".", "$")):
                    sub_defs = os.path.join(sub_path, "Defs")
                    if os.path.exists(sub_defs):
                        defs_folders.add(sub_defs)
        except (PermissionError, OSError):
            pass

    return list(defs_folders)


def find_all_defs_folders_with_loadfolders(mod_path: str) -> list[str]:
    """
    Находит все папки Defs с учётом LoadFolders.xml и универсальным сканированием.

    Оптимизировано:
    - Использует set для отслеживания дубликатов
    - Уменьшено количество вызовов os.path.exists
    """
    defs_folders = set()

    # Шаг 1: Парсим LoadFolders.xml
    loadfolders = parse_loadfolders(mod_path)
    if loadfolders:
        for folder in loadfolders:
            base = mod_path if folder == "" else os.path.join(mod_path, folder)
            defs_path = os.path.join(base, "Defs")
            if os.path.exists(defs_path):
                defs_folders.add(defs_path)

    # Шаг 2: Универсальное сканирование ВСЕХ папок
    universal_defs = _find_all_defs_folders_universal(mod_path)
    defs_folders.update(universal_defs)

    # Шаг 3: Корневая Defs
    root_defs = os.path.join(mod_path, "Defs")
    if os.path.exists(root_defs):
        defs_folders.add(root_defs)

    # Шаг 4: Рекурсивный поиск как fallback (если ничего не нашли)
    if not defs_folders:
        recursive_defs = _find_all_defs_folders_recursive(mod_path)
        defs_folders.update(recursive_defs)

    return list(defs_folders)


def _find_all_defs_folders_recursive(mod_path: str, max_depth: int = 3) -> list[str]:
    """
    Рекурсивный поиск папок Defs с ограничением глубины.
    Используется как fallback если универсальный поиск ничего не нашёл.
    """
    defs_folders = []

    def _scan(current_dir: str, depth: int):
        if depth > max_depth:
            return
        try:
            for item in os.listdir(current_dir):
                if item.startswith(".") or item.startswith("$"):
                    continue
                item_path = os.path.join(current_dir, item)
                if not os.path.isdir(item_path):
                    continue
                if item == "Defs":
                    defs_folders.append(item_path)
                else:
                    _scan(item_path, depth + 1)
        except (PermissionError, OSError):
            pass

    if os.path.exists(mod_path):
        _scan(mod_path, 0)

    return defs_folders


def _find_all_languages_folders_universal(mod_path: str) -> list[str]:
    """
    Универсальный поиск всех папок Languages в моде (как Text-grabber).

    Сканирует ВСЕ папки в корне мода и ищет Languages в каждой.
    Поддерживает: Common/Languages, 1.6/Languages, и т.д.

    Оптимизировано:
    - Использует set для отслеживания
    """
    langs_folders = set()

    if not os.path.exists(mod_path):
        return list(langs_folders)

    for item in os.listdir(mod_path):
        item_path = os.path.join(mod_path, item)
        if not os.path.isdir(item_path):
            continue

        if item.startswith(".") or item.startswith("$"):
            continue

        langs_path = os.path.join(item_path, "Languages")
        if os.path.exists(langs_path):
            langs_folders.add(langs_path)

    return list(langs_folders)


def _find_all_languages_folders_recursive(mod_path: str, max_depth: int = 3) -> list[str]:
    """
    Рекурсивный поиск папок Languages с ограничением глубины.
    Используется как fallback если универсальный поиск ничего не нашёл.
    """
    langs_folders = set()

    def _scan(current_dir: str, depth: int):
        if depth > max_depth:
            return
        try:
            for item in os.listdir(current_dir):
                if item.startswith(".") or item.startswith("$"):
                    continue
                item_path = os.path.join(current_dir, item)
                if not os.path.isdir(item_path):
                    continue
                if item == "Languages":
                    langs_folders.add(item_path)
                else:
                    _scan(item_path, depth + 1)
        except (PermissionError, OSError):
            pass

    if os.path.exists(mod_path):
        _scan(mod_path, 0)

    return list(langs_folders)


def find_all_languages_folders_with_loadfolders(mod_path: str) -> list[str]:
    """
    Находит все папки Languages с учётом LoadFolders.xml и универсальным сканированием.

    Оптимизировано:
    - Использует set для отслеживания дубликатов
    - Возвращает список, отсортированный по приоритету:
      не-версионные (Contents, Common, корневая) > версионные (1.6, 1.5, ...)
    """
    langs_folders = set()

    # Шаг 1: Корневая Languages (высший приоритет)
    root_langs = os.path.join(mod_path, "Languages")
    if os.path.exists(root_langs):
        langs_folders.add(root_langs)

    # Шаг 2: LoadFolders.xml
    loadfolders = parse_loadfolders(mod_path)
    if loadfolders:
        for folder in loadfolders:
            base = mod_path if folder == "" else os.path.join(mod_path, folder)
            langs_path = os.path.join(base, "Languages")
            if os.path.exists(langs_path):
                langs_folders.add(langs_path)

    # Шаг 3: Универсальное сканирование ВСЕХ папок (как Text-grabber)
    universal_langs = _find_all_languages_folders_universal(mod_path)
    langs_folders.update(universal_langs)

    # Шаг 4: Рекурсивный поиск как fallback (если ничего не нашли)
    if not langs_folders:
        recursive_langs = _find_all_languages_folders_recursive(mod_path)
        langs_folders.update(recursive_langs)

    # Сортируем по приоритету: не-версионные (Contents, Common, корневая) > версионные
    return _prioritize_languages_folders(list(langs_folders), mod_path)


def _prioritize_languages_folders(folders: list[str], mod_path: str) -> list[str]:
    """
    Сортирует папки Languages по приоритету:
    не-версионные (Contents, Common, корневая) > версионные (1.6, 1.5, ...).

    Внутри каждой группы порядок сохраняется.

    Args:
        folders: Список путей к папкам Languages
        mod_path: Путь к папке мода

    Returns:
        Отсортированный список (приоритетные первыми)
    """
    if not folders:
        return []

    non_versioned = []   # Contents/Languages, Common/Languages, Languages
    versioned = []       # 1.6/Languages, 1.5/Languages

    for folder in folders:
        try:
            rel_path = os.path.relpath(folder, mod_path)
        except ValueError:
            rel_path = folder
        path_parts = rel_path.replace("\\", "/").split("/")
        is_versioned = any(part in SUPPORTED_VERSIONS for part in path_parts)

        if is_versioned:
            versioned.append(folder)
        else:
            non_versioned.append(folder)

    return non_versioned + versioned


def _detect_version(mod_path: str) -> str | None:
    """
    Определяет версию мода по наличию папок или About.xml.

    Args:
        mod_path: Путь к моду

    Returns:
        Версия (например "1.6") или None
    """
    # Проверяем наличие версионных папок
    for version in SUPPORTED_VERSIONS:
        if os.path.exists(os.path.join(mod_path, version)):
            return version

    # Проверяем About.xml на supportedVersions
    about_path = os.path.join(mod_path, "About", "About.xml")
    if os.path.exists(about_path):
        try:
            root = safe_parse_xml(about_path)
            if root is not None:
                sv = root.find("supportedVersions")
                if sv is not None:
                    versions = [li.text.strip() for li in sv.findall("li") if li.text]
                    # Возвращаем самую новую версию
                    for version in SUPPORTED_VERSIONS:
                        if version in versions:
                            return version
                    # Или последнюю из списка
                    if versions:
                        return versions[-1]
        except Exception:
            pass

    return None


def get_mod_content_folders(mod_path: str, target_version: str = None) -> dict[str, list[str]]:
    """
    Получает все папки контента мода.

    Args:
        mod_path: Путь к моду
        target_version: Целевая версия

    Returns:
        Словарь {"defs": [...], "languages": [...], "patches": [...], "assemblies": [...]}
    """
    # Определяем папки контента
    content_folders = []

    loadfolders = parse_loadfolders(mod_path, target_version)
    if loadfolders:
        for folder in loadfolders:
            base = mod_path if folder == "" else os.path.join(mod_path, folder)
            if os.path.exists(base):
                content_folders.append(base)
    else:
        content_folders.append(mod_path)

    result = {
        "defs": [],
        "languages": [],
        "patches": [],
        "assemblies": [],
    }

    for base in content_folders:
        for sub in ["Defs", "Languages", "Patches", "Assemblies"]:
            path = os.path.join(base, sub)
            if os.path.exists(path):
                result[sub.lower()].append(path)

    # Дополнительно проверяем Common
    common = os.path.join(mod_path, "Common")
    if os.path.exists(common):
        for sub in ["Defs", "Languages", "Patches", "Assemblies"]:
            path = os.path.join(common, sub)
            if os.path.exists(path) and path not in result[sub.lower()]:
                result[sub.lower()].append(path)

    return result
