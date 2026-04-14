"""
Модуль обработки XML патчей RimWorld.

Поддерживаемые типы PatchOperation:
- PatchOperationAdd - добавляет элементы
- PatchOperationReplace - заменяет элементы
- PatchOperationRemove - удаляет элементы
- PatchOperationSequence - последовательность операций
- PatchOperationConditional - условная операция
- PatchOperationFindMod - проверка наличия мода
- PatchOperationName - переименование
- PatchOperationAddModExtension - добавляет extension

Этот модуль извлекает переводимые строки из патчей
и применяет их к существующим Def-ам.
"""

import xml.etree.ElementTree as ET


def process_patches(
    patches_folder: str,
    defs_index: dict[str, dict],
    logger=None,
    max_depth: int = 5,
    filters_config: dict = None,
) -> dict[str, dict]:
    """
    Обрабатывает все патчи и применяет их к defs_index.

    Args:
        patches_folder: Путь к папке с патчами
        defs_index: Существующий индекс Def-ов (будет изменён)
        logger: Логгер (опционально)
        max_depth: Максимальная глубина обхода папок
        filters_config: Конфигурация фильтров (для enable_mod_settings_framework)

    Returns:
        Обновлённый defs_index с применёнными патчами
    """
    from utils.fs_utils import safe_walk
    from verification.xml_parser import safe_parse_xml

    patch_files = []
    for root_dir, dirs, files in safe_walk(patches_folder, max_depth=max_depth):
        for fn in files:
            if fn.lower().endswith(".xml"):
                patch_files.append(f"{root_dir}/{fn}")

    if not patch_files:
        if logger:
            logger.debug("Патч-файлы не найдены")
        return defs_index

    if logger:
        logger.info(f"  Найдено {len(patch_files)} патч-файлов")

    for patch_file in patch_files:
        root = safe_parse_xml(patch_file)
        if root is None:
            if logger:
                logger.debug(f"Не удалось распарсить патч: {patch_file}")
            continue

        for operation in root:
            try:
                _apply_operation(operation, defs_index, logger, filters_config)
            except Exception as e:
                if logger:
                    logger.debug(f"Ошибка применения патча {patch_file}: {e}")

    return defs_index


def _apply_operation(
    operation: ET.Element, defs_index: dict[str, dict], logger=None, filters_config: dict = None
) -> None:
    """
    Применяет одну PatchOperation к defs_index.

    Args:
        operation: XML элемент операции
        defs_index: Индекс Def-ов (будет изменён)
        logger: Логгер
        filters_config: Конфигурация фильтров
    """
    op_tag = operation.tag

    # Обработка составных операций
    if op_tag == "PatchOperationSequence":
        _handle_sequence(operation, defs_index, logger, filters_config)
        return

    if op_tag == "PatchOperationConditional":
        for child in operation:
            if child.tag.startswith("PatchOperation"):
                _apply_operation(child, defs_index, logger, filters_config)
        return

    if op_tag == "PatchOperationFindMod":
        return

    # Одиночные операции
    if op_tag in ("PatchOperationAdd", "PatchOperationAddModExtension"):
        _handle_add(operation, defs_index, logger, filters_config)
    elif op_tag == "PatchOperationReplace":
        _handle_replace(operation, defs_index, logger, filters_config)
    elif op_tag == "PatchOperationRemove":
        _handle_remove(operation, defs_index, logger)
    elif op_tag == "PatchOperationName":
        _handle_name(operation, defs_index, logger)
    # ✅ НОВОЕ: Обработка ModSettingsFramework - извлекаем Keyed строки
    elif op_tag.startswith("ModSettingsFramework.") or op_tag.startswith("XmlExtensions."):
        _handle_mod_settings_framework(operation, defs_index, logger, filters_config)
    else:
        _extract_text_from_unknown(operation, defs_index, logger)


def _handle_sequence(
    sequence: ET.Element, defs_index: dict[str, dict], logger=None, filters_config: dict = None
) -> None:
    """Обрабатывает PatchOperationSequence."""
    for operation in sequence:
        if operation.tag.startswith("PatchOperation"):
            _apply_operation(operation, defs_index, logger, filters_config)


def _handle_add(
    operation: ET.Element, defs_index: dict[str, dict], logger=None, filters_config: dict = None
) -> None:
    """
    Обрабатывает PatchOperationAdd - добавляет элементы.

    XPath в <match> указывает куда добавлять.
    XML в <add> указывает что добавлять.
    """
    match_elem = operation.find("match")
    add_elem = operation.find("add")

    if match_elem is None or add_elem is None:
        return

    xpath = match_elem.text or ""
    if not xpath:
        return

    # Извлекаем переводимые строки из добавляемых элементов
    if add_elem.text and add_elem.text.strip():
        # Простой текст - добавляем как значение
        _add_to_defs_index(xpath, add_elem.tag, add_elem.text.strip(), defs_index)

    # Рекурсивно извлекаем все дочерние элементы
    for child in add_elem:
        _extract_element_text_recursive(child, xpath, defs_index)


def _handle_replace(
    operation: ET.Element, defs_index: dict[str, dict], logger=None, filters_config: dict = None
) -> None:
    """
    Обрабатывает PatchOperationReplace - заменяет элементы.
    """
    match_elem = operation.find("match")
    replace_elem = operation.find("replace")

    if match_elem is None or replace_elem is None:
        return

    xpath = match_elem.text or ""
    if not xpath:
        return

    # Заменяем/добавляем переводимые строки
    if replace_elem.text and replace_elem.text.strip():
        _add_to_defs_index(xpath, replace_elem.tag, replace_elem.text.strip(), defs_index)

    for child in replace_elem:
        _extract_element_text_recursive(child, xpath, defs_index)


def _handle_remove(operation: ET.Element, defs_index: dict[str, dict], logger=None) -> None:
    """
    Обрабатывает PatchOperationRemove - удаляет элементы.
    """
    match_elem = operation.find("match")
    if match_elem is None:
        return

    xpath = match_elem.text or ""
    if not xpath:
        return

    # Удаляем из индекса все Def-ы соответствующие xpath
    keys_to_remove = []
    for key, fields in defs_index.items():
        if _xpath_matches_key(xpath, key):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        defs_index.pop(key, None)


def _handle_name(operation: ET.Element, defs_index: dict[str, dict], logger=None) -> None:
    """
    Обрабатывает PatchOperationName - переименование Def.
    """
    match_elem = operation.find("match")
    name_elem = operation.find("name")

    if match_elem is None or name_elem is None:
        return

    old_name = match_elem.text or ""
    new_name = name_elem.text or ""

    if not old_name or not new_name:
        return

    # Переименовываем в индексе
    if old_name in defs_index:
        defs_index[new_name] = defs_index.pop(old_name)


def _extract_text_from_unknown(
    operation: ET.Element, defs_index: dict[str, dict], logger=None
) -> None:
    """Извлекает текст из неизвестных типов операций."""
    for child in operation:
        if child.tag in ("match", "add", "replace", "remove"):
            continue  # Уже обработано

        if child.text and child.text.strip():
            _extract_element_text_recursive(child, "patch", defs_index)


def _extract_element_text_recursive(
    element: ET.Element, parent_path: str, defs_index: dict[str, dict], current_path: str = ""
) -> None:
    """
    Рекурсивно извлекает весь переводимый текст из элемента.

    Args:
        element: XML элемент
        parent_path: XPath родительского элемента
        defs_index: Индекс Def-ов
        current_path: Текущий путь внутри элемента
    """
    from utils.rimworld_xml import TRANSLATABLE_TAGS

    if current_path:
        full_path = f"{parent_path}.{current_path}"
    else:
        full_path = parent_path

    # Проверяем является ли тег переводимым
    if element.tag in TRANSLATABLE_TAGS:
        if element.text and element.text.strip() and len(element.text.strip()) >= 2:
            _add_to_defs_index(full_path, element.tag, element.text.strip(), defs_index)

    # Рекурсивно обрабатываем детей
    for i, child in enumerate(element):
        child_path = f"{current_path}.{child.tag}" if current_path else child.tag

        # Обработка списков
        if child.tag == "li":
            child_path = f"{current_path}.{i}" if current_path else str(i)

        _extract_element_text_recursive(child, parent_path, defs_index, child_path)


def _add_to_defs_index(path: str, tag: str, text: str, defs_index: dict[str, dict]) -> None:
    """
    Добавляет текст в defs_index.

    Args:
        path: Путь к элементу
        tag: Тег элемента
        text: Текст для добавления
        defs_index: Индекс Def-ов
    """
    # Используем path как ключ
    if path not in defs_index:
        defs_index[path] = {}

    defs_index[path][tag] = text


def _xpath_matches_key(xpath: str, key: str) -> bool:
    """
    Проверяет соответствует ли ключ XPath.

    Упрощённая проверка - ищем совпадение частей пути.

    Args:
        xpath: XPath выражение
        key: Ключ Def-а

    Returns:
        True если ключ соответствует XPath
    """
    # Извлекаем последнюю часть XPath (после последнего /)
    parts = xpath.split("/")
    last_part = parts[-1] if parts else xpath

    # Удаляем XPath специфичные символы
    clean_part = last_part.replace("*", "").replace("@", "").replace("li", "").strip(".")

    if not clean_part:
        return False

    # Проверяем вхождение
    return clean_part.lower() in key.lower()


def _handle_mod_settings_framework(
    operation: ET.Element, defs_index: dict[str, dict], logger=None, filters_config: dict = None
) -> None:
    """
    Обрабатывает ModSettingsFramework и XmlExtensions патчи.
    Извлекает Keyed строки из элементов настроек.

    Проверяет enable_mod_settings_framework из filters_config.
    """
    # Проверяем включена ли функция
    if filters_config and not filters_config.get("enable_mod_settings_framework", True):
        return

    # Извлекаем все текстовые элементы из операции
    for child in operation:
        if not isinstance(child.tag, str):
            continue

        # ModSettingsFramework использует специальные теги для перевода
        if child.tag in ("tKey", "tKeyTip", "label", "description", "tooltip"):
            if child.text and child.text.strip() and len(child.text.strip()) >= 2:
                # Добавляем как Keyed строку
                keyed_key = f"MSF_{child.tag}"
                if keyed_key not in defs_index:
                    defs_index[keyed_key] = {}
                defs_index[keyed_key][child.tag] = child.text.strip()

        # Рекурсивно обрабатываем вложенные элементы
        for sub_child in child:
            if isinstance(sub_child.tag, str) and sub_child.text and sub_child.text.strip():
                if len(sub_child.text.strip()) >= 2:
                    tag_key = f"MSF_{sub_child.tag}"
                    if tag_key not in defs_index:
                        defs_index[tag_key] = {}
                    defs_index[tag_key][sub_child.tag] = sub_child.text.strip()
