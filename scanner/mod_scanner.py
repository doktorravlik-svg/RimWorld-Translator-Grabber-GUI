# mod_scanner.py
import os
import re
from typing import Any

from loguru import logger as loguru_logger
from verification.xml_parser import safe_parse_xml

# Language detection patterns
CYRILLIC_PATTERN = re.compile(r'[\u0400-\u04FF]')
LATIN_PATTERN = re.compile(r'[A-Za-z]')
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]')
JAPANESE_PATTERN = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
KOREAN_PATTERN = re.compile(r'[\uac00-\ud7af]')

def _detect_language_from_text(text: str) -> str | None:
    """
    Определяет язык по тексту.
    Возвращает код языка или None если не определён.
    """
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # Проверяем кириллицу (русский)
    cyrillic_count = len(CYRILLIC_PATTERN.findall(text))
    if cyrillic_count > 10:
        return "Russian"
    
    # Проверяем китайский
    chinese_count = len(CHINESE_PATTERN.findall(text))
    if chinese_count > 5:
        return "Chinese"
    
    # Проверяем японский
    japanese_count = len(JAPANESE_PATTERN.findall(text))
    if japanese_count > 5:
        return "Japanese"
    
    # Проверяем корейский
    korean_count = len(KOREAN_PATTERN.findall(text))
    if korean_count > 5:
        return "Korean"
    
    # Проверяем латинницу (английский)
    latin_count = len(LATIN_PATTERN.findall(text))
    if latin_count > 10:
        return "English"
    
    return None


def parse_about_xml(about_path: str, logger=None) -> dict[str, Any]:
    """
    Выполняет глубокий парсинг About.xml для извлечения метаданных мода.
    Поддерживает стандартные теги и расширения для зависимостей и версий.
    """
    result = {
        'name': 'Unknown Mod',
        'author': 'Unknown',
        'mod_id': None,
        'version': '0.0.0',
        'game_versions': [],  # ✅ НОВОЕ: Версии игры, а не версия мода
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
        # Используем парсер с защитой от пустых файлов
        root = safe_parse_xml(about_path)
        if root is None:
            return result

        # 1. Основные метаданные
        for child in root:
            tag = child.tag.lower()
            text = child.text.strip() if child.text else None

            if tag == 'name': result['name'] = text
            elif tag == 'author': result['author'] = text
            elif tag == 'packageid': result['mod_id'] = text.lower() if text else None
            elif tag == 'description': result['description'] = text
            elif tag == 'targetcontentcreator': result['target_content_creator'] = text
            elif tag == 'targetmodid': result['target_mod_id'] = text

            # Сбор поддерживаемых языков (если указаны)
            elif tag == 'supportedlanguages':
                if child.text:
                    result['supported_languages'].extend([l.strip() for l in child.text.replace(',', '\n').split('\n') if l.strip()])
                for lang in child:
                    if lang.text: result['supported_languages'].append(lang.text.strip())

        # 2. Определение версии мода
        version_tag = root.find('version')
        if version_tag is not None and version_tag.text:
            result['version'] = version_tag.text.strip()
        else:
            # Если тега version нет, берем самую высокую из поддерживаемых версий игры
            supp_versions = root.find('supportedVersions')
            if supp_versions is not None:
                v_list = [v.text.strip() for v in supp_versions if v.text]
                if v_list:
                    result['version'] = sorted(v_list, reverse=True)[0]

        # 2.1. Собираем версии игры (supportedVersions) отдельно от версии мода
        supp_versions = root.find('supportedVersions')
        if supp_versions is not None:
            result['game_versions'] = [v.text.strip() for v in supp_versions if v.text]

        # 3. Сбор зависимостей (packageId других модов)
        deps_node = root.find('modDependencies')
        if deps_node is not None:
            for dep in deps_node:
                p_id = dep.find('packageId')
                if p_id is not None and p_id.text:
                    result['dependencies'].append(p_id.text.strip().lower())

        # 4. Сбор loadAfter (порядок загрузки после)
        load_after_node = root.find('loadAfter')
        if load_after_node is not None:
            for li in load_after_node:
                if li.text:
                    result['load_after'].append(li.text.strip())

        # 5. Сбор loadBefore (порядок загрузки до)
        load_before_node = root.find('loadBefore')
        if load_before_node is not None:
            for li in load_before_node:
                if li.text:
                    result['load_before'].append(li.text.strip())

        # Очистка дубликатов языков
        result['supported_languages'] = list(set(result['supported_languages']))

    except Exception as e:
        # ✅ ИСПРАВЛЕНО: Используем переданный logger или loguru_logger по умолчанию
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
        ✅ ИСПРАВЛЕНО: total_xml_files вместо total_keys (считает файлы, а не ключи)
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

        lang_info = {
            'keyed_files': 0,
            'def_files': 0,
            'total_xml_files': 0
        }

        # Подсчёт Keyed файлов
        keyed_path = os.path.join(lang_path, "Keyed")
        if os.path.exists(keyed_path):
            for root, _, files in os.walk(keyed_path):
                for f in files:
                    if f.endswith('.xml'):
                        lang_info['keyed_files'] += 1

        # Подсчёт DefInjected файлов
        def_injected_path = os.path.join(lang_path, "DefInjected")
        if os.path.exists(def_injected_path):
            for root, _, files in os.walk(def_injected_path):
                for f in files:
                    if f.endswith('.xml'):
                        lang_info['def_files'] += 1

        lang_info['total_xml_files'] = lang_info['keyed_files'] + lang_info['def_files']
        
        if logger:
            logger.debug(f"Язык {lang_dir}: Keyed={lang_info['keyed_files']}, DefInjected={lang_info['def_files']}")
        
        languages[lang_dir] = lang_info

    if logger:
        logger.info(f"Завершён анализ языков. Найдено: {len(languages)}")

    return languages


def _scan_defs_for_languages(mod_path: str, defs_folders: list[str], logger=None) -> set[str]:
    """
    Сканирует Defs файлы для определения языков в текстовом содержимом.
    
    Args:
        mod_path: Путь к моду
        defs_folders: Список папок Defs для сканирования
        logger: Опциональный логгер
    
    Returns:
        Множество обнаруженных языков
    """
    detected_languages = set()
    
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
                try:
                    root_xml = safe_parse_xml(filepath)
                    if root_xml is None:
                        continue
                    
                    for elem in root_xml.iter():
                        if elem.text and elem.text.strip():
                            lang = _detect_language_from_text(elem.text)
                            if lang:
                                detected_languages.add(lang)
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
    from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders, find_all_defs_folders_with_loadfolders
    
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
