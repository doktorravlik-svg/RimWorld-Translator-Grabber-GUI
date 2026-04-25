"""
Модуль разрешения наследования ParentName/Name в RimWorld XML.

RimWorld использует систему наследования через атрибуты:
- Name="SomeName" - определяет имя элемента для наследования
- ParentName="SomeName" - наследует содержимое родителя
- Abstract="true" - абстрактный элемент (не создаёт Def в игре)

Этот модуль разрешает цепочки наследования и объединяет содержимое.
"""

from copy import deepcopy

from lxml import etree


def resolve_parent_chains(
    defs_folder_paths: list[str], logger=None, max_depth: int = 10
) -> dict[str, dict[str, etree._Element]]:
    """
    Разрешает все цепочки наследования в указанной папке Defs.

    Args:
        defs_folder_paths: Список путей к папкам Defs или XML файлам
        logger: Логгер (опционально)
        max_depth: Максимальная глубина обхода папок

    Returns:
        Словарь {file_path: {element_name: resolved_element}}
    """
    import os

    from verification.xml_parser import safe_parse_xml

    # Шаг 1: Собираем все элементы с атрибутом Name
    name_registry: dict[str, dict[str, etree._Element]] = {}  # {file_path: {name: element}}

    all_xml_files = []
    for folder_path in defs_folder_paths:
        if not os.path.exists(folder_path):
            continue
        for root, dirs, files in os.walk(folder_path):
            # Проверка глубины
            rel_root = os.path.relpath(root, folder_path)
            depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
            if depth > max_depth:
                continue

            for fn in files:
                if fn.lower().endswith(".xml"):
                    all_xml_files.append(os.path.join(root, fn))

    for file_path in all_xml_files:
        root = safe_parse_xml(file_path)
        if root is None:
            if logger:
                logger.debug(f"Не удалось распарсить: {file_path}")
            continue

        file_names: dict[str, etree._Element] = {}
        for element in root:
            name_attr = element.get("Name")
            if name_attr:
                file_names[name_attr] = element

        if file_names:
            name_registry[file_path] = file_names

    return name_registry


def resolve_def_inheritance(
    def_element: etree._Element,
    name_registry: dict[str, dict[str, etree._Element]],
    visited: set[str] | None = None,
) -> etree._Element:
    """
    Разрешает наследование для одного Def элемента.

    Рекурсивно проходит по цепочке ParentName и объединяет
    содержимое родителей с содержимым ребёнка.

    Args:
        def_element: XML элемент Def для разрешения
        name_registry: Реестр всех именованных элементов
        visited: Множество уже посещённых имён (защита от циклов)

    Returns:
        Разрешённый XML элемент (копия оригинала с унаследованными полями)
    """
    if visited is None:
        visited = set()

    parent_name = def_element.get("ParentName")
    if not parent_name:
        # Нет родителя - возвращаем как есть
        return def_element

    # Защита от бесконечных циклов
    if parent_name in visited:
        return def_element

    visited.add(parent_name)

    # Ищем родителя в реестре
    parent_element = _find_parent_element(parent_name, name_registry)
    if parent_element is None:
        # Родитель не найден - возможно это Core дефолт или ошибка
        return def_element

    # Рекурсивно разрешаем родителя
    resolved_parent = resolve_def_inheritance(parent_element, name_registry, visited)

    # Объединяем: родитель + ребёнок (ребёнок перезаписывает)
    return _merge_elements(resolved_parent, def_element)


def _find_parent_element(
    name: str, name_registry: dict[str, dict[str, etree._Element]]
) -> etree._Element | None:
    """
    Ищет элемент с указанным Name во всех файлах.

    Args:
        name: Имя для поиска
        name_registry: Реестр всех именованных элементов

    Returns:
        Найденный XML элемент или None
    """
    # Проходим по всем файлам (обратный порядок - последние приоритетнее)
    for file_path in reversed(list(name_registry.keys())):
        if name in name_registry[file_path]:
            return deepcopy(name_registry[file_path][name])

    return None


def _merge_elements(parent: etree._Element, child: etree._Element) -> etree._Element:
    """
    Объединяет родителя и ребёнка. Поля ребёнка перезаписывают родительские.

    Алгоритм:
    1. Копируем все атрибуты родителя
    2. Перезаписываем атрибутами ребёнка
    3. Копируем все дочерние элементы родителя
    4. Для каждого дочернего элемента ребёнка:
       - Если такой же есть у родителя -> заменяем
       - Если нет -> добавляем

    Args:
        parent: Родительский элемент
        child: Дочерний элемент (приоритетнее)

    Returns:
        Объединённый XML элемент
    """
    # Создаём новый элемент с атрибутами ребёнка (приоритетнее)
    merged = etree.Element(child.tag)

    # Копируем атрибуты родителя
    for key, value in parent.attrib.items():
        merged.set(key, value)

    # Перезаписываем атрибутами ребёнка
    for key, value in child.attrib.items():
        merged.set(key, value)

    # Удаляем ParentName из результата (он уже разрешён)
    merged.attrib.pop("ParentName", None)

    # Копируем дочерние элементы родителя
    for child_elem in parent:
        merged.append(deepcopy(child_elem))

    # Обрабатываем дочерние элементы ребёнка
    for child_elem in child:
        tag = child_elem.tag

        # Проверяем есть ли такой же тег у родителя
        existing = merged.find(tag)
        if existing is not None:
            # Тег существует - нужно решить: заменить или объединить
            # Если у ребёнка есть атрибут Name и у родителя тоже -> возможно это список
            if child_elem.get("Name") and existing.get("Name"):
                # Ищем по Name
                found_by_name = _find_by_name(merged, child_elem.get("Name"))
                if found_by_name is not None:
                    # Заменяем элемент с таким же Name
                    idx = list(merged).index(found_by_name)
                    merged.remove(found_by_name)
                    merged.insert(idx, deepcopy(child_elem))
                    continue
                else:
                    # Name не найден - добавляем как новый
                    merged.append(deepcopy(child_elem))
                    continue
            elif child_elem.get("li"):
                # Это список (li элементы) - нужно объединить
                _merge_list_elements(existing, child_elem)
                continue
            else:
                # Просто заменяем текст/содержимое
                merged.remove(existing)

        merged.append(deepcopy(child_elem))

    # Копируем текст элемента если есть
    if child is not None:
        if child.text and child.text.strip():
            merged.text = child.text
        if child.tail:
            merged.tail = child.tail

    return merged


def _find_by_name(parent: etree._Element, name: str) -> etree._Element | None:
    """
    Ищет дочерний элемент по атрибуту Name.

    Args:
        parent: Родительский элемент
        name: Имя для поиска

    Returns:
        Найденный элемент или None
    """
    for child in parent:
        if child.get("Name") == name:
            return child
    return None


def _merge_list_elements(existing: etree._Element, new: etree._Element) -> None:
    """
    Объединяет li элементы списков.

    Элементы с одинаковыми индексами или Name заменяются,
    новые добавляются.

    Args:
        existing: Существующий список (будет изменён)
        new: Новый список для объединения
    """
    # Собираем существующие li
    existing_lis = list(existing.findall("li"))

    # Обрабатываем новые li
    for new_li in new.findall("li"):
        li_name = new_li.get("Name")

        if li_name:
            # Ищем по Name
            found = None
            for existing_li in existing_lis:
                if existing_li.get("Name") == li_name:
                    found = existing_li
                    break

            if found:
                # Заменяем
                idx = list(existing).index(found)
                existing.remove(found)
                existing.insert(idx, deepcopy(new_li))
            else:
                # Добавляем
                existing.append(deepcopy(new_li))
        else:
            # Без Name - добавляем в конец
            existing.append(deepcopy(new_li))


def collect_all_parents_recursive(
    parent_name: str,
    name_registry: dict[str, dict[str, etree._Element]],
    visited: set[str] | None = None,
) -> list[etree._Element]:
    """
    Рекурсивно собирает всех предков элемента.

    Args:
        parent_name: Имя начального родителя
        name_registry: Реестр всех именованных элементов
        visited: Множество посещённых (защита от циклов)

    Returns:
        Список всех предков от самого старого к родителю
    """
    if visited is None:
        visited = set()

    if parent_name in visited:
        return []

    visited.add(parent_name)

    parent = _find_parent_element(parent_name, name_registry)
    if parent is None:
        return []

    # Рекурсивно собираем предков
    grandparents_name = parent.get("ParentName")
    if grandparents_name:
        ancestors = collect_all_parents_recursive(grandparents_name, name_registry, visited)
        ancestors.append(parent)
        return ancestors

    return [parent]
