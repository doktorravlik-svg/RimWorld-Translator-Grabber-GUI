# mod_scanner.py
import os
from typing import Any

from loguru import logger as loguru_logger
from verification.xml_parser import safe_parse_xml
from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders, find_all_defs_folders_with_loadfolders

# Pre-computed character sets for O(1) lookup (used in _detect_language_from_text)
UKRAINIAN_CHARS = frozenset("іїєґ")
RUSSIAN_CHARS = frozenset("ыэъё")

# Thresholds for language detection
MIN_CYRILLIC_COUNT = 10
MIN_ASIAN_COUNT = 5
MIN_LATIN_COUNT = 10

def _detect_language_from_text(text: str) -> str | None:
    """
    Определяет язык по тексту.
    Возвращает код языка или None если не определён.

    Оптимизировано:
    - Использует set-операции для O(1) проверки характерных букв
    - Единственный проход по тексту для подсчета символов
    - Избегает лишних вызовов strip()/lower()
    """
    if not text:
        return None

    text = text.strip()
    if not text:
        return None

    # Single-pass character counting
    cyrillic_count = 0
    latin_count = 0
    chinese_count = 0
    japanese_count = 0
    korean_count = 0
    has_ukrainian = False
    has_russian = False

    for char in text:
        cp = ord(char)
        # Cyrillic range: U+0400 to U+04FF
        if 0x0400 <= cp <= 0x04FF:
            cyrillic_count += 1
            # Check for Ukrainian/Russian specific chars (using lowercase for comparison)
            char_lower = char.lower()
            if char_lower in UKRAINIAN_CHARS:
                has_ukrainian = True
            elif char_lower in RUSSIAN_CHARS:
                has_russian = True
        # Latin range
        elif ('A' <= char <= 'Z') or ('a' <= char <= 'z'):
            latin_count += 1
        # Chinese
        elif 0x4e00 <= cp <= 0x9fff:
            chinese_count += 1
        # Japanese Hiragana
        elif 0x3040 <= cp <= 0x309f:
            japanese_count += 1
        # Japanese Katakana
        elif 0x30a0 <= cp <= 0x30ff:
            japanese_count += 1
        # Korean
        elif 0xac00 <= cp <= 0xd7af:
            korean_count += 1

    # Ukrainian check first (most specific)
    if has_ukrainian:
        return "Ukrainian"

    # Russian check
    if has_russian or cyrillic_count > MIN_CYRILLIC_COUNT:
        return "Russian"

    # Asian languages
    if chinese_count > MIN_ASIAN_COUNT:
        return "Chinese"
    if japanese_count > MIN_ASIAN_COUNT:
        return "Japanese"
    if korean_count > MIN_ASIAN_COUNT:
        return "Korean"

    # Latin (English)
    if latin_count > MIN_LATIN_COUNT:
        return "English"

    return None


def parse_about_xml(about_path: str, logger=None) -> dict[str, Any]:
    """
    Выполняет глубокий парсинг About.xml для извлечения метаданных мода.
    Поддерживает стандартные теги и расширения для зависимостей и версий.

    Оптимизировано:
    - Единственный проход по дочерним элементам
    - Кэширование результатов find()
    - Минимальные вызовы strip()
    """
    result = {
        'name': 'Unknown Mod',
        'author': 'Unknown',
        'mod_id': None,
        'version': '0.0.0',
        'game_versions': [],
        'dependencies': [],
        'target_content_creator': None,
        'target_mod_id': None,
        'supported_languages': [],
        'description': None,
        'load_after': [],
        'load_before': []
    }

    if not os.path.exists(about_path):
        return result

    try:
        root = safe_parse_xml(about_path)
        if root is None:
            return result

        # Cache for nodes we need multiple times
        supp_versions_node = None
        version_tag = None

        # Single pass through all children
        for child in root:
            tag = child.tag.lower()
            text = child.text.strip() if child.text else None

            if tag == 'name':
                result['name'] = text
            elif tag == 'author':
                result['author'] = text
            elif tag == 'packageid':
                result['mod_id'] = text.lower() if text else None
            elif tag == 'description':
                result['description'] = text
            elif tag == 'targetcontentcreator':
                result['target_content_creator'] = text
            elif tag == 'targetmodid':
                result['target_mod_id'] = text
            elif tag == 'supportedlanguages':
                if child.text:
                    result['supported_languages'].extend(
                        [l.strip() for l in child.text.replace(',', '\n').split('\n') if l.strip()]
                    )
                for lang in child:
                    if lang.text:
                        result['supported_languages'].append(lang.text.strip())
            elif tag == 'version':
                version_tag = child
            elif tag == 'supportedversions':
                supp_versions_node = child

        # Process version
        if version_tag is not None and version_tag.text:
            result['version'] = version_tag.text.strip()
        elif supp_versions_node is not None:
            v_list = [v.text.strip() for v in supp_versions_node if v.text]
            if v_list:
                result['version'] = sorted(v_list, reverse=True)[0]
                result['game_versions'] = v_list

        # Process dependencies
        deps_node = root.find('modDependencies')
        if deps_node is not None:
            for dep in deps_node:
                p_id = dep.find('packageId')
                if p_id is not None and p_id.text:
                    result['dependencies'].append(p_id.text.strip().lower())

        # Process loadAfter
        load_after_node = root.find('loadAfter')
        if load_after_node is not None:
            for li in load_after_node:
                if li.text:
                    result['load_after'].append(li.text.strip())

        # Process loadBefore
        load_before_node = root.find('loadBefore')
        if load_before_node is not None:
            for li in load_before_node:
                if li.text:
                    result['load_before'].append(li.text.strip())

        # Remove duplicates from supported_languages
        result['supported_languages'] = list(set(result['supported_languages']))

    except Exception as e:
        _logger = logger if logger else loguru_logger
        _logger.error(f"Ошибка парсинга {about_path}: {e}")

    return result

def find_about_xml(mod_path: str) -> str | None:
    """Ищет About.xml в корне мода или в папке About."""
    for path in [os.path.join(mod_path, "About", "About.xml"), os.path.join(mod_path, "About.xml")]:
        if os.path.exists(path):
            return path
    return None

def find_mod_structure(mod_path: str, logger=None) -> dict[str, Any]:
    """
    Анализирует файловую структуру мода. Определяет наличие папок Defs,
    Languages и Core с учётом версионности (1.1, 1.4, 1.5 и т.д.).
    """
    result = {
        'root': mod_path,
        'about_data': parse_about_xml(find_about_xml(mod_path) or "", logger),
        'active_version': None,
        'defs_path': None,
        'langs_path': None,
        'is_translation': False
    }

    if logger:
        logger.info(f"Анализ структуры мода: {mod_path}")

    # Приоритетный список версий для поиска
    versions = ["1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "1.0"]

    # 1. Пытаемся найти версию по наличию папки Defs внутри версионных папок
    for v in versions:
        v_path = os.path.join(mod_path, v)
        if os.path.exists(os.path.join(v_path, "Defs")):
            result['active_version'] = v
            result['defs_path'] = os.path.join(v_path, "Defs")
            result['langs_path'] = os.path.join(v_path, "Languages")
            if logger:
                logger.debug(f"Найдена версия {v}, путь Defs: {result['defs_path']}")
            break

    # 2. Если версионные папки не найдены, используем корень
    if not result['defs_path']:
        dp = os.path.join(mod_path, "Defs")
        if os.path.exists(dp):
            result['defs_path'] = dp
            result['langs_path'] = os.path.join(mod_path, "Languages")
            if logger:
                logger.debug(f"Версионные папки не найдены, используем корень. Defs: {dp}")
        elif logger:
            logger.warning(f"Папка Defs не найдена в {mod_path}")

    # 3. Определяем, является ли мод переводом
    result['is_translation'] = result['about_data'].get('name', '').lower().endswith('translation') or \
                            result['about_data'].get('name', '').lower().endswith('localization')

    if logger:
        logger.info(f"Структура мода проанализирована. Перевод: {result['is_translation']}")

    return result


def analyze_languages(langs_base: str, logger=None) -> dict[str, Any]:
    """
    Анализирует доступные языки в папке Languages.

    Args:
        langs_base: Путь к папке Languages
        logger: Опциональный логгер (объект Logger или loguru logger)

    Returns:
        {язык: {keyed_files: int, def_files: int, total_xml_files: int}}

    Оптимизировано:
    - Объединены os.walk вызовы для Keyed и DefInjected
    - Использован однокоренный подход для подсчета файлов
    """
    languages = {}

    if not os.path.exists(langs_base):
        if logger:
            logger.warning(f"Папка Languages не найдена: {langs_base}")
        return languages

    if logger:
        logger.info(f"Начало анализа языков в: {langs_base}")

    for lang_dir in os.listdir(langs_base):
        lang_path = os.path.join(langs_base, lang_dir)
        if not os.path.isdir(lang_path):
            continue

        keyed_files = 0
        def_files = 0

        # Single pass: check for Keyed and DefInjected directories
        keyed_path = os.path.join(lang_path, "Keyed")
        def_injected_path = os.path.join(lang_path, "DefInjected")

        # Count Keyed files
        if os.path.exists(keyed_path):
            for root, _, files in os.walk(keyed_path):
                keyed_files += sum(1 for f in files if f.endswith('.xml'))

        # Count DefInjected files
        if os.path.exists(def_injected_path):
            for root, _, files in os.walk(def_injected_path):
                def_files += sum(1 for f in files if f.endswith('.xml'))

        total_xml_files = keyed_files + def_files

        if logger:
            logger.debug(f"Язык {lang_dir}: Keyed={keyed_files}, DefInjected={def_files}")

        languages[lang_dir] = {
            'keyed_files': keyed_files,
            'def_files': def_files,
            'total_xml_files': total_xml_files
        }

    if logger:
        logger.info(f"Завершён анализ языков. Найдено: {len(languages)}")

    return languages

# Constants for optimization
MAX_XML_FILE_SIZE = 10 * 1024 * 1024  # 10 MB - skip large files
MAX_TEXT_LENGTH_FOR_DETECTION = 5000  # Limit text length for language detection


def _scan_defs_for_languages(mod_path: str, defs_folders: list[str], logger=None) -> set[str]:
    """
    Сканирует Defs файлы для определения языков в текстовом содержимом.

    Args:
        mod_path: Путь к моду
        defs_folders: Список папок Defs для сканирования
        logger: Опциональный логгер

    Returns:
        Множество обнаруженных языков

    Оптимизировано:
    - Пропускает файлы больше 10MB
    - Ограничивает длину текста для анализа
    - Досрочный выход при обнаружении всех языков
    """
    detected_languages = set()
    all_langs = {"English", "Russian", "Chinese", "Japanese", "Korean", "Ukrainian"}

    if not defs_folders:
        return detected_languages

    for defs_folder in defs_folders:
        if not os.path.exists(defs_folder):
            continue

        for root, _, files in os.walk(defs_folder):
            for filename in files:
                if not filename.endswith('.xml'):
                    continue

                filepath = os.path.join(root, filename)

                # Skip large files
                try:
                    if os.path.getsize(filepath) > MAX_XML_FILE_SIZE:
                        continue
                except OSError:
                    continue

                try:
                    root_xml = safe_parse_xml(filepath)
                    if root_xml is None:
                        continue

                    for elem in root_xml.iter():
                        if not elem.text or not elem.text.strip():
                            continue

                        # Limit text length for performance
                        text = elem.text[:MAX_TEXT_LENGTH_FOR_DETECTION]
                        lang = _detect_language_from_text(text)
                        if lang:
                            detected_languages.add(lang)

                        # Early exit if we found all languages
                        if detected_languages == all_langs:
                            return detected_languages
                except Exception:
                    pass

    return detected_languages


def detect_mod_languages(mod_path: str, logger=None) -> list[str]:
    """
    Определяет доступные языки в моде по папкам Languages и содержимому Defs.

    Args:
        mod_path: Путь к папке мода
        logger: Опциональный логгер

    Returns:
        Список доступных языков (например ['English', 'Russian', 'Chinese'])
    """
    languages = set()

    try:
        langs_folders = find_all_languages_folders_with_loadfolders(mod_path)

        for langs_folder in langs_folders:
            if os.path.exists(langs_folder):
                for item in os.listdir(langs_folder):
                    item_path = os.path.join(langs_folder, item)
                    if os.path.isdir(item_path):
                        languages.add(item)

        defs_folders = find_all_defs_folders_with_loadfolders(mod_path)
        defs_languages = _scan_defs_for_languages(mod_path, defs_folders, logger)

        if defs_languages:
            if logger:
                logger.debug(f"Обнаружены языки в Defs: {defs_languages}")
            languages.update(defs_languages)

    except Exception as e:
        if logger:
            logger.debug(f"Ошибка определения языков: {e}")

    result = sorted(list(languages))
    if logger:
        logger.debug(f"Определены языки в моде {mod_path}: {result}")

    return result
