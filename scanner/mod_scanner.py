# mod_scanner.py
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any

def parse_about_xml(about_path: str) -> Dict[str, Any]:
    """
    Выполняет глубокий парсинг About.xml для извлечения метаданных мода.
    Поддерживает стандартные теги и расширения для зависимостей и версий.
    """
    result = {
        'name': 'Unknown Mod',
        'author': 'Unknown',
        'mod_id': None,
        'version': '0.0.0',
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
        tree = ET.parse(about_path)
        root = tree.getroot()

        # 1. Основные метаданные
        for child in root:
            tag = child.tag.lower()
            text = child.text.strip() if child.text else None

            if tag == 'name': result['name'] = text
            elif tag == 'author': result['author'] = text
            elif tag == 'packageid': result['mod_id'] = text
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

        # 3. Сбор зависимостей (packageId других модов)
        deps_node = root.find('modDependencies')
        if deps_node is not None:
            for dep in deps_node:
                p_id = dep.find('packageId')
                if p_id is not None and p_id.text:
                    result['dependencies'].append(p_id.text.strip())

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
        print(f"[Error] Ошибка парсинга {about_path}: {e}")

    return result

def find_about_xml(mod_path: str) -> Optional[str]:
    """Ищет About.xml в корне мода или в папке About."""
    for path in [os.path.join(mod_path, "About", "About.xml"), os.path.join(mod_path, "About.xml")]:
        if os.path.exists(path):
            return path
    return None

def find_mod_structure(mod_path: str) -> Dict[str, Any]:
    """
    Анализирует файловую структуру мода. Определяет наличие папок Defs, 
    Languages и Core с учетом версионности (1.1, 1.4, 1.5 и т.д.).
    """
    result = {
        'root': mod_path,
        'about_data': parse_about_xml(find_about_xml(mod_path) or ""),
        'active_version': None,
        'defs_path': None,
        'langs_path': None,
        'is_translation': False
    }

    # Приоритетный список версий для поиска
    versions = ["1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "1.0"]
    
    # 1. Пытаемся найти версию по наличию папки Defs внутри версионных папок
    for v in versions:
        v_path = os.path.join(mod_path, v)
        if os.path.exists(os.path.join(v_path, "Defs")):
            result['active_version'] = v
            result['defs_path'] = os.path.join(v_path, "Defs")
            result['langs_path'] = os.path.join(v_path, "Languages")
            break
            
    # 2. Если версионные папки не найдены, используем корень
    if not result['defs_path']:
        dp = os.path.join(mod_path, "Defs")
        if os.path.exists(dp):
            result['defs_path'] = dp
            result['langs_path'] = os.path.join(mod_path, "Languages")
    
    # 3. Определяем, является ли мод переводом
    result['is_translation'] = result['about_data'].get('name', '').lower().endswith('translation') or \
                                result['about_data'].get('name', '').lower().endswith('localization')
    
    return result


def analyze_languages(langs_base: str, logger=None) -> Dict[str, Any]:
    """
    Анализирует доступные языки в папке Languages.
    
    Returns:
        {язык: {keyed_files: int, def_files: int, total_keys: int}}
    """
    languages = {}
    
    if not os.path.exists(langs_base):
        return languages
    
    for lang_dir in os.listdir(langs_base):
        lang_path = os.path.join(langs_base, lang_dir)
        if not os.path.isdir(lang_path):
            continue
        
        lang_info = {
            'keyed_files': 0,
            'def_files': 0,
            'total_keys': 0
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
        
        lang_info['total_keys'] = lang_info['keyed_files'] + lang_info['def_files']
        languages[lang_dir] = lang_info
    
    return languages
