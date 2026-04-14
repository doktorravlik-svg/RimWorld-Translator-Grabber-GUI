# verification/xml_parser.py
"""
Модуль парсинга XML файлов переводов RimWorld.

Основные функции:
- safe_parse_xml: безопасный парсинг с обработкой BOM и ошибок
- XMLParser: класс-обёртка с расширенными возможностями
- validate_xml_structure: валидация структуры XML
- write_tree_pretty: красивая запись XML
- get_xml_content_hash: получение хеша содержимого
- find_duplicate_xml_files: поиск дубликатов файлов
"""

import os
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
import logging


# ============================================================================
# КОНСТАНТЫ И ТИПЫ ДАННЫХ
# ============================================================================

# Типы XML файлов RimWorld
XML_FILE_TYPES = {
    'KEYED': ['Keyed', 'keyed'],
    'DEF_INJECTED': ['DefInjected', 'DefIsjected'],
    'LANGUAGE_DATA': ['LanguageData', 'LanguageData', 'Language'],
    'ABOUT': ['About', 'ModMetaData'],
}

# Корневые теги для разных типов файлов
VALID_ROOT_TAGS = {
    'keyed': ['Keyed', 'keyed'],
    'def_injected': ['DefInjected', 'DefIsjected', 'LanguageData'],
    'about': ['ModMetaData', 'About'],
}


@dataclass
class XMLParseResult:
    """Результат парсинга XML файла"""
    success: bool
    root: Optional[ET.Element] = None
    file_path: str = ""
    error: Optional[str] = None
    file_type: Optional[str] = None
    entries: Dict[str, str] = None  # key -> value

    def __post_init__(self):
        if self.entries is None:
            self.entries = {}


@dataclass
class XMLValidationResult:
    """Результат валидации XML файла"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    file_path: str


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ПАРСИНГА
# ============================================================================

def safe_parse_xml(file_path: str) -> Optional[ET.Element]:
    """
    Безопасный парсинг XML файла с обработкой BOM и ошибок.
    Исправляет распространённые проблемы с XML (неэкранированные &).

    Args:
        file_path: Путь к XML файлу

    Returns:
        Корневой элемент XML или None при ошибке
    """
    import re
    
    # Читаем файл и подготавливаем текст
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Удаляем UTF-8 BOM если есть
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
        
        # Декодируем
        text = content.decode('utf-8')
        
        # Исправляем неэкранированные &
        # Заменяем & на &amp; кроме тех что уже в entity (&amp;, &lt;, &gt;, &quot;, &apos;, &#...;)
        text = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)', '&amp;', text)
        
        # Парсим исправленный текст
        root = ET.fromstring(text)
        return root
        
    except ET.ParseError as e:
        logging.error(f"Не удалось распарсить XML файл {file_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Ошибка при чтении файла {file_path}: {e}")
        return None


def parse_xml_file(file_path: str, logger: Optional[logging.Logger] = None) -> Optional[ET.ElementTree]:
    """
    Парсинг XML файла с использованием safe_parse_xml.

    Args:
        file_path: Путь к XML файлу
        logger: Опциональный логгер

    Returns:
        Объект ElementTree или None при ошибке
    """
    try:
        root = safe_parse_xml(file_path)
        if root is not None:
            return ET.ElementTree(root)
    except Exception as e:
        if logger:
            logger.debug(f"XML parse failed for {file_path}: {e}")
        return None


def get_entries_from_xml(root: ET.Element) -> Dict[str, str]:
    """
    Извлекает все записи (ключ -> значение) из XML элемента.

    Args:
        root: Корневой элемент XML

    Returns:
        Словарь {ключ: значение}
    """
    entries = {}
    for child in root:
        if child.text:
            entries[child.tag] = child.text.strip()
        else:
            entries[child.tag] = ""
    return entries


def detect_xml_file_type(root: ET.Element) -> Optional[str]:
    """
    Определяет тип XML файла RimWorld по корневому тегу.

    Args:
        root: Корневой элемент XML

    Returns:
        Тип файла или None если не распознан
    """
    tag = root.tag.lower()

    if tag in ['keyed']:
        return 'keyed'
    elif tag in ['definjected', 'defisinjected', 'languagedata']:
        return 'def_injected'
    elif tag in ['about', 'modmetadata']:
        return 'about'
    elif tag in ['languages', 'languagemeta']:
        return 'language'

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

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger
        self._parsed_files: Dict[str, XMLParseResult] = {}

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
                success=False,
                file_path=file_path,
                error="Не удалось распарсить XML файл"
            )
        else:
            file_type = detect_xml_file_type(root)
            entries = get_entries_from_xml(root)

            result = XMLParseResult(
                success=True,
                root=root,
                file_path=file_path,
                file_type=file_type,
                entries=entries
            )

        # Кэшируем результат
        self._parsed_files[file_path] = result
        return result

    def parse_directory(self, directory: str, pattern: str = "*.xml") -> List[XMLParseResult]:
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
                if filename.endswith('.xml'):
                    file_path = os.path.join(root_dir, filename)
                    result = self.parse(file_path)
                    results.append(result)

        return results

    def validate_structure(self, file_path: str, required_tags: Optional[List[str]] = None) -> XMLValidationResult:
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
                file_path=file_path
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
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_path=file_path
        )

    def clear_cache(self):
        """Очищает кэш распарсенных файлов"""
        self._parsed_files.clear()


# ============================================================================
# ФУНКЦИИ ЗАПИСИ XML
# ============================================================================

def write_tree_pretty(tree: ET.ElementTree, target_path: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Записывает XML дерево в файл с красивым форматированием.

    Args:
        tree: XML ElementTree
        target_path: Путь для записи
        logger: Опциональный логгер

    Returns:
        True при успехе, False при ошибке
    """
    _d = os.path.dirname(target_path)
    if _d:
        os.makedirs(_d, exist_ok=True)

    def indent(elem: ET.Element, level: int = 0):
        i = "\n" + level * "    "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "    "
            children = list(elem)
            for child in children:
                indent(child, level + 1)
            if children and (not children[-1].tail or not children[-1].tail.strip()):
                children[-1].tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    root = tree.getroot()
    indent(root)

    try:
        xml_bytes = ET.tostring(root, encoding="utf-8")
        with open(target_path, "wb") as fw:
            fw.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            fw.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            fw.write(xml_bytes)
        if logger:
            logger.debug(f"Wrote pretty XML: {target_path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Write error {target_path}: {e}")
        return False


def add_or_preserve(root: ET.Element, tagname: str, value: str, logger: Optional[logging.Logger] = None) -> ET.Element:
    """
    Добавляет тег в XML элемент или заполняет существующий пустой тег.

    Args:
        root: Корневой элемент
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
        el = ET.SubElement(root, tagname)
        el.text = value
        if logger:
            logger.debug(f"Added tag {tagname}")
    else:
        if not el.text or not el.text.strip():
            el.text = value
            if logger:
                logger.debug(f"Filled empty tag {tagname}")
        else:
            if logger:
                logger.debug(f"Preserved existing non-empty tag {tagname}")

    return el


# ============================================================================
# ФУНКЦИИ СРАВНЕНИЯ И ХЕШИРОВАНИЯ
# ============================================================================

def get_xml_content_hash(element: ET.Element) -> str:
    """
    Создает хеш содержимого XML элемента для сравнения.

    Args:
        element: XML элемент

    Returns:
        Строка хеша
    """
    def _normalize(elem: ET.Element) -> str:
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


def find_duplicate_xml_files(directory: str, logger: Optional[logging.Logger] = None) -> Dict[str, List[str]]:
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
            if fname.endswith('.xml'):
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

def validate_xml_structure(root: ET.Element, required_tags: List[str]) -> bool:
    """
    Валидация наличия обязательных тегов в XML.

    Args:
        root: Корневой элемент XML
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


def validate_xml_files(directory: str, file_type: str, logger: Optional[logging.Logger] = None) -> List[XMLValidationResult]:
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
            if fname.endswith('.xml'):
                fpath = os.path.join(root_dir, fname)
                result = XMLParser(logger).validate_structure(fpath, required_tags)
                results.append(result)

    return results


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Тестирование xml_parser")
    print("=" * 60)

    # Тест определения типа файла
    print("\n[ТЕСТ] Определение типа файла:")

    # Создаем тестовые элементы
    keyed_root = ET.fromstring('<Keyed><Test>Value</Test></Keyed>')
    print(f"  Keyed -> {detect_xml_file_type(keyed_root)}")

    def_injected_root = ET.fromstring('<DefInjected><Test>Value</Test></DefInjected>')
    print(f"  DefInjected -> {detect_xml_file_type(def_injected_root)}")

    about_root = ET.fromstring('<ModMetaData><Test>Value</Test></ModMetaData>')
    print(f"  ModMetaData -> {detect_xml_file_type(about_root)}")

    # Тест извлечения записей
    print("\n[ТЕСТ] Извлечение записей:")
    entries = get_entries_from_xml(keyed_root)
    print(f"  Записи: {entries}")

    # Тест парсера
    print("\n[ТЕСТ] XMLParser:")
    parser = XMLParser()
    print(f"  Создан парсер")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
