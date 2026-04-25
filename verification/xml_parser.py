# verification/xml_parser.py
"""
Модуль парсинга XML файлов переводов RimWorld.

Основные функции:
- safe_parse_xml: безопасный парсинг с обработкой BOM и ошибок (использует lxml с recover=True)
- XMLParser: класс-обёртка с расширенными возможностями
- validate_xml_structure: валидация структуры XML
- write_tree_pretty: красивая запись XML
- get_xml_content_hash: получение хеша содержимого
- find_duplicate_xml_files: поиск дубликатов файлов
"""

import logging
import os
import re
from dataclasses import dataclass, field

# Используем lxml (recover=True для поврежденных XML)
from lxml import etree

# ============================================================================
# КОНСТАНТЫ И ТИПЫ ДАННЫХ
# ============================================================================

# Типы XML файлов RimWorld
XML_FILE_TYPES = {
    "KEYED": ["Keyed", "keyed"],
    "DEF_INJECTED": ["DefInjected", "DefInjected"],
    "LANGUAGE_DATA": ["LanguageData", "LanguageData", "Language"],
    "ABOUT": ["About", "ModMetaData"],
}

# Корневые теги для разных типов файлов
VALID_ROOT_TAGS = {
    "keyed": ["Keyed", "keyed"],
    "def_injected": ["DefInjected", "DefInjected", "LanguageData"],
    "about": ["ModMetaData", "About"],
}


@dataclass
class XMLParseResult:
    """Результат парсинга XML файла"""

    success: bool
    root: etree._Element | None = None
    file_path: str = ""
    error: str | None = None
    file_type: str | None = None
    entries: dict[str, str] = field(default_factory=dict)


@dataclass
class XMLValidationResult:
    """Результат валидации XML файла"""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    file_path: str


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ КОДИРОВОК
# ============================================================================


def _rebuild_xml_declaration(text: str) -> bytes:
    """
    Удаляет старую XML declaration и добавляет UTF-8 declaration,
    чтобы lxml корректно обработал перекодированный контент.
    """
    # Убираем старую декларацию, если есть
    text = re.sub(r"<\?xml[^?]*\?>\s*", "", text, count=1)
    # Добавляем UTF-8 declaration
    text = '<?xml version="1.0" encoding="utf-8"?>\n' + text
    return text.encode("utf-8")


def get_xml_root(tree_or_root: etree._Element | etree._ElementTree | None) -> etree._Element | None:
    """
    ✅ Универсальная функция получения корневого элемента.
    Работает и с Element, и с ElementTree.
    Решает проблему обратной совместимости во всём проекте.
    """
    if tree_or_root is None:
        return None
    if isinstance(tree_or_root, etree._ElementTree):
        return tree_or_root.getroot()
    return tree_or_root


def _decode_xml_bytes(raw_bytes: bytes) -> bytes:
    """
    Пробует декодировать XML-байты из различных кодировок в UTF-8 bytes для парсера.

    Поддерживает UTF-8, UTF-16 (LE/BE), CP1252, Latin-1, ISO-8859-1.
    При неудаче использует UTF-8 с заменой недопустимых символов.
    """
    # Удаляем UTF-8 BOM если есть
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        raw_bytes = raw_bytes[3:]

    # Если пустой — возвращаем пустой
    if not raw_bytes.strip():
        return b""

    # Пробуем UTF-8
    try:
        raw_bytes.decode("utf-8")
        return raw_bytes
    except UnicodeDecodeError:
        pass

    # Пробуем UTF-16 с BOM
    if raw_bytes.startswith(b"\xff\xfe"):
        try:
            text = raw_bytes.decode("utf-16-le")
            return _rebuild_xml_declaration(text)
        except UnicodeDecodeError:
            pass
    elif raw_bytes.startswith(b"\xfe\xff"):
        try:
            text = raw_bytes.decode("utf-16-be")
            return _rebuild_xml_declaration(text)
        except UnicodeDecodeError:
            pass

    # Пробуем однобайтовые кодировки (типичные для старых переводов)
    for encoding in ("cp1252", "latin-1", "iso-8859-1"):
        try:
            text = raw_bytes.decode(encoding)
            return _rebuild_xml_declaration(text)
        except UnicodeDecodeError:
            continue

    # Последняя попытка — UTF-8 с заменой
    text = raw_bytes.decode("utf-8", errors="replace")
    return _rebuild_xml_declaration(text)


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ПАРСИНГА
# ============================================================================


def safe_parse_xml(file_path: str) -> etree._Element | None:
    """
    Безопасный парсинг XML файла с обработкой BOM, ошибок кодировки и повреждений.
    Использует lxml с recover=True для парсинга повреждённых XML (как в Text-Grabber).

    Args:
        file_path: Путь к XML файлу

    Returns:
        Корневой Element или None при ошибке
    """
    try:
        # Парсер как в Text-Grabber: remove_comments=True, recover=True
        parser = etree.XMLParser(remove_comments=True, recover=True)

        with open(file_path, "rb") as f:
            content = f.read()

        # Декодируем в UTF-8 bytes с поддержкой разных исходных кодировок
        content = _decode_xml_bytes(content)

        # Проверяем, не пустой ли файл
        if not content.strip():
            logging.debug(f"XML файл пустой, пропускаем: {file_path}")
            return None

        # Парсим через lxml с recover=True (исправляет многие ошибки автоматически)
        root = etree.fromstring(content, parser)

        if root is None:
            # Вероятно, файл содержит только комментарии (remove_comments=True удалил их)
            # Это не ошибка, а ожидаемое поведение для файлов-заглушек
            logging.warning(f"Пропуск XML файла (заглушка): {os.path.basename(file_path)}")
            return None

        return root

    except Exception as e:
        logging.error(f"Ошибка при чтении XML файла {file_path}: {e}")
        return None


def parse_xml_file(file_path: str, logger: logging.Logger | None = None) -> etree._Element | None:
    """
    Парсинг XML файла с использованием safe_parse_xml.

    Args:
        file_path: Путь к XML файлу
        logger: Опциональный логгер

    Returns:
        Корневой Element или None при ошибке
    """
    try:
        return safe_parse_xml(file_path)
    except Exception as e:
        if logger:
            logger.debug(f"XML parse failed for {file_path}: {e}")
        return None
    except Exception as e:
        if logger:
            logger.debug(f"XML parse failed for {file_path}: {e}")
        return None


def get_entries_from_xml(root: etree._Element, prefix: str = "") -> dict[str, str]:
    """
    Рекурсивно извлекает все записи (ключ -> значение) из XML элемента.
    Обрабатывает вложенные структуры (например, <li> внутри списков).

    Args:
        root: Корневой элемент XML (lxml)
        prefix: Префикс для вложенных тегов (например, "parent.child")

    Returns:
        Словарь {ключ: значение}
    """
    entries = {}

    for child in root:
        # Формируем полное имя тега с учётом иерархии
        full_tag = f"{prefix}.{child.tag}" if prefix else child.tag

        # Если есть текстовое значение, сохраняем
        if child.text and child.text.strip():
            entries[full_tag] = child.text.strip()
        else:
            entries[full_tag] = ""

        # Рекурсивно обрабатываем вложенные элементы
        # Особенно важно для <li> элементов в списках DefInjected
        if len(child) > 0:
            nested = get_entries_from_xml(child, prefix=full_tag)
            entries.update(nested)

    return entries


def detect_xml_file_type(root: etree._Element) -> str | None:
    """
    Определяет тип XML файла RimWorld по корневому тегу.

    Args:
        root: Корневой элемент XML

    Returns:
        Тип файла или None если не распознан
    """
    tag = root.tag.lower()

    if tag in ["keyed"]:
        return "keyed"
    elif tag in ["definjected", "definjected", "languagedata"]:
        return "def_injected"
    elif tag in ["about", "modmetadata"]:
        return "about"
    elif tag in ["languages", "languagemeta"]:
        return "language"

    return None


# ============================================================================
# КЛАСС XML PARSER
# ============================================================================


class XMLParser:
    """
    Расширенный класс для парсинга XML файлов RimWorld.

    Поддерживает:
    - Парсинг Keyed файлов
    - Парсинг DefInjected файлов
    - Валидацию структуры
    - Извлечение переводов
    """

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger
        self._parsed_files: dict[str, XMLParseResult] = {}

    def parse(self, file_path: str) -> XMLParseResult:
        """
        Парсит XML файл и возвращает результат.

        Args:
            file_path: Путь к XML файлу

        Returns:
            XMLParseResult с результатами парсинга
        """
        # Проверяем кэш
        if file_path in self._parsed_files:
            return self._parsed_files[file_path]

        root = safe_parse_xml(file_path)

        if root is None:
            result = XMLParseResult(
                success=False, file_path=file_path, error="Не удалось распарсить XML файл"
            )
        else:
            file_type = detect_xml_file_type(root)
            entries = get_entries_from_xml(root)

            result = XMLParseResult(
                success=True, root=root, file_path=file_path, file_type=file_type, entries=entries
            )

        # Кэшируем результат
        self._parsed_files[file_path] = result
        return result

    def parse_directory(self, directory: str, pattern: str = "*.xml") -> list[XMLParseResult]:
        """
        Парсит все XML файлы в директории.

        Args:
            directory: Путь к директории
            pattern: Паттерн для поиска файлов

        Returns:
            Список результатов парсинга
        """
        results = []

        if not os.path.exists(directory):
            if self.logger:
                self.logger.warning(f"Директория не существует: {directory}")
            return results

        for root_dir, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".xml"):
                    file_path = os.path.join(root_dir, filename)
                    result = self.parse(file_path)
                    results.append(result)

        return results

    def validate_structure(
        self, file_path: str, required_tags: list[str] | None = None
    ) -> XMLValidationResult:
        """
        Валидирует структуру XML файла.

        Args:
            file_path: Путь к XML файлу
            required_tags: Список обязательных тегов

        Returns:
            XMLValidationResult с результатами валидации
        """
        errors = []
        warnings = []

        root = safe_parse_xml(file_path)
        if root is None:
            return XMLValidationResult(
                is_valid=False,
                errors=[f"Не удалось распарсить файл: {file_path}"],
                warnings=[],
                file_path=file_path,
            )

        # Проверяем корневой тег
        file_type = detect_xml_file_type(root)
        if file_type is None:
            warnings.append(f"Неизвестный тип XML файла: {root.tag}")

        # Проверяем обязательные теги
        if required_tags:
            for tag in required_tags:
                if root.find(tag) is None:
                    errors.append(f"Отсутствует обязательный тег: {tag}")

        # Проверяем наличие содержимого
        if len(root) == 0:
            warnings.append("XML файл не содержит дочерних элементов")

        return XMLValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings, file_path=file_path
        )

    def clear_cache(self):
        """Очищает кэш распарсенных файлов"""
        self._parsed_files.clear()


# ============================================================================
# ФУНКЦИИ ЗАПИСИ XML
# ============================================================================


def write_tree_pretty(
    tree_or_root: etree._Element | etree._ElementTree, target_path: str, logger: logging.Logger | None = None
) -> bool:
    """
    Записывает XML элемент в файл с красивым форматированием.

    Использует lxml (как в Text-Grabber) с pretty_print=True.

    Args:
        root: Корневой элемент lxml
        target_path: Путь для записи
        logger: Опциональный логгер

    Returns:
        True при успехе, False при ошибке
    """
    _d = os.path.dirname(target_path)
    if _d:
        os.makedirs(_d, exist_ok=True)

    try:
        # Поддерживаем и Element, и ElementTree
        # ✅ Исправление: у _Element тоже есть атрибут getroot, но это не вызываемый метод!
        if isinstance(tree_or_root, etree._ElementTree):
            root = tree_or_root.getroot()
        else:
            root = tree_or_root
        # ✅ Полный сброс всего существующего форматирования
        # Это единственный надёжный способ исправить все баги lxml с форматированием
        for elem in root.iter():
            elem.tail = None
            if elem is root:
                # В корневом теге LanguageData никогда не должно быть прямого текста!
                # Если есть - это остатки битых тегов, мусор, эскейпы и т.д. УДАЛЯЕМ ПОЛНОСТЬЮ
                elem.text = None
            elif elem.text:
                stripped = elem.text.strip()
                elem.text = stripped if stripped else None

        # Правильное форматирование от дерева
        etree.indent(root, space="  ")

        # Генерация XML
        xml_bytes = etree.tostring(
            root,
            encoding="utf-8",
            pretty_print=True,
            xml_declaration=True,
            with_tail=False
        )

        with open(target_path, "wb") as fw:
            fw.write(b"\xef\xbb\xbf")  # UTF-8 BOM
            fw.write(xml_bytes)
        if logger:
            logger.debug(f"Wrote pretty XML: {target_path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Write error {target_path}: {e}")
        return False


def add_or_preserve(
    root: etree._Element, tagname: str, value: str, logger: logging.Logger | None = None
) -> etree._Element:
    """
    Добавляет тег в XML элемент или заполняет существующий пустой тег.

    Args:
        root: Корневой элемент (lxml)
        tagname: Имя тега
        value: Значение для установки
        logger: Опциональный логгер

    Returns:
        Элемент который был добавлен или обновлен
    """
    el = None
    for child in list(root):
        try:
            if child.tag == tagname:
                el = child
                break
        except Exception:
            continue

    if el is None:
        el = etree.SubElement(root, tagname)
        el.text = value
        if logger:
            logger.debug(f"Added tag {tagname}")
    elif not el.text or not el.text.strip():
        el.text = value
        if logger:
            logger.debug(f"Filled empty tag {tagname}")
    elif logger:
        logger.debug(f"Preserved existing non-empty tag {tagname}")

    return el


def add_with_anchor(parent: etree._Element, tag_name: str, original_text: str, translated_text: str) -> tuple[etree._Comment, etree._Element]:
    """
    Добавляет тег вместе с якорем оригинала.
    ✅ Всегда добавляет комментарий EN: даже если тег существует.
    Используется для самообучения системы якорей.

    Args:
        parent: Родительский XML элемент
        tag_name: Имя тега для перевода
        original_text: Оригинальный текст на английском
        translated_text: Переведенный текст

    Returns:
        Кортеж (созданный_комментарий, созданный_элемент)
    """
    # 1. Создаем комментарий-якорь
    comment = etree.Comment(f" EN: {original_text} ")

    # ✅ ИСПРАВЛЕНИЕ: Добавляем комментарий ИМЕННО ПЕРЕД новым тегом, а не в конец
    # Находим индекс куда вставляется SubElement по умолчанию
    insert_pos = len(parent)
    parent.insert(insert_pos, comment)

    # 2. Создаем элемент перевода
    node = etree.SubElement(parent, tag_name)
    node.text = translated_text

    # Форматирование, чтобы не слипалось
    comment.tail = "\n    "
    node.tail = "\n    "

    return comment, node


def add_or_update_translation(root: etree._Element, tag_name: str, original_text: str, translated_text: str, logger: logging.Logger | None = None) -> etree._Element:
    """
    Добавляет или обновляет перевод с комментарием оригинала.
    Использует нативный etree.Comment для корректного экранирования символов.

    Args:
        root: Корневой элемент XML
        tag_name: Имя тега для перевода
        original_text: Оригинальный текст на английском
        translated_text: Переведенный текст
        logger: Опциональный логгер

    Returns:
        Созданный или обновленный элемент перевода
    """
    # Ищем, есть ли уже такой тег
    existing_node = root.find(tag_name)

    if existing_node is not None:
        # Если тег есть, просто обновляем текст перевода
        existing_node.text = translated_text
        if logger:
            logger.debug(f"Updated translation for tag {tag_name}")
        return existing_node
    else:
        # Используем универсальную функцию с якорем
        _, new_node = add_with_anchor(root, tag_name, original_text, translated_text)

        if logger:
            logger.debug(f"Added new translation tag {tag_name} with original comment")
        return new_node


# ============================================================================
# ФУНКЦИИ СРАВНЕНИЯ И ХЕШИРОВАНИЯ
# ============================================================================


def get_xml_content_hash(element: etree._Element) -> str:
    """
    Создает хеш содержимого XML элемента для сравнения.

    Args:
        element: XML элемент

    Returns:
        Строка хеша
    """

    def _normalize(elem: etree._Element) -> str:
        parts = []
        # Учитываем имя тега
        parts.append(f"tag:{elem.tag}")
        # Учитываем атрибуты (отсортированные)
        if elem.attrib:
            attrs = sorted(elem.attrib.items())
            for k, v in attrs:
                parts.append(f"attr:{k}={v}")
        # Учитываем текстовое значение
        if elem.text and elem.text.strip():
            parts.append(f"text:{elem.text.strip()}")
        # Учитываем tail (текст после закрывающего тега)
        if elem.tail and elem.tail.strip():
            parts.append(f"tail:{elem.tail.strip()}")
        # Рекурсивно обрабатываем дочерние элементы
        for child in elem:
            parts.append(_normalize(child))
        return "|".join(parts)

    return _normalize(element)


def find_duplicate_xml_files(
    directory: str, logger: logging.Logger | None = None
) -> dict[str, list[str]]:
    """
    Сканирует директорию и находит XML файлы с идентичным содержимым.

    Args:
        directory: Путь к директории
        logger: Опциональный логгер

    Returns:
        Словарь: хеш -> список файлов с этим содержимым
    """
    hash_to_files = {}

    if not os.path.exists(directory):
        return hash_to_files

    for root_dir, _, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".xml"):
                fpath = os.path.join(root_dir, fname)
                try:
                    root = safe_parse_xml(fpath)
                    if root is not None:
                        content_hash = get_xml_content_hash(root)
                        if content_hash not in hash_to_files:
                            hash_to_files[content_hash] = []
                        hash_to_files[content_hash].append(fpath)
                except Exception as e:
                    if logger:
                        logger.debug(f"Не удалось обработать файл {fpath}: {e}")

    # Оставляем только дубликаты (больше 1 файла)
    duplicates = {k: v for k, v in hash_to_files.items() if len(v) > 1}
    return duplicates


# ============================================================================
# ВАЛИДАЦИЯ XML
# ============================================================================


def validate_xml_structure(root: etree._Element, required_tags: list[str]) -> bool:
    """
    Валидация наличия обязательных тегов в XML.

    Args:
        root: Корневой элемент XML (lxml)
        required_tags: Список обязательных тегов

    Returns:
        True если все теги присутствуют
    """
    if root is None:
        return False
    for tag in required_tags:
        if root.find(tag) is None:
            return False
    return True


def validate_xml_files(
    directory: str, file_type: str, logger: logging.Logger | None = None
) -> list[XMLValidationResult]:
    """
    Валидирует все XML файлы указанного типа в директории.

    Args:
        directory: Путь к директории
        file_type: Тип файлов ('keyed', 'def_injected', 'about')
        logger: Опциональный логгер

    Returns:
        Список результатов валидации
    """
    results = []
    required_tags = VALID_ROOT_TAGS.get(file_type, [])

    for root_dir, _, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".xml"):
                fpath = os.path.join(root_dir, fname)
                result = XMLParser(logger).validate_structure(fpath, required_tags)
                results.append(result)

    return results


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование xml_parser")
    print("=" * 60)

    # Тест определения типа файла
    print("\n[ТЕСТ] Определение типа файла:")

    # Создаем тестовые элементы с помощью lxml
    keyed_root = etree.fromstring("<Keyed><Test>Value</Test></Keyed>")
    print(f"  Keyed -> {detect_xml_file_type(keyed_root)}")

    def_injected_root = etree.fromstring("<DefInjected><Test>Value</Test></DefInjected>")
    print(f"  DefInjected -> {detect_xml_file_type(def_injected_root)}")

    about_root = etree.fromstring("<ModMetaData><Test>Value</Test></ModMetaData>")
    print(f"  ModMetaData -> {detect_xml_file_type(about_root)}")

    # Тест извлечения записей
    print("\n[ТЕСТ] Извлечение записей:")
    entries = get_entries_from_xml(keyed_root)
    print(f"  Записи: {entries}")

    # Тест парсера
    print("\n[ТЕСТ] XMLParser:")
    parser = XMLParser()
    print("  Создан парсер")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
