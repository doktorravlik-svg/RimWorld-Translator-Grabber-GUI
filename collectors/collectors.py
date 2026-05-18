import json
import os

from lxml import etree
from loguru import logger

from utils.fs_utils import safe_walk
from utils.loguru_setup import get_logger
from utils.rimworld_xml import extract_subfields
from verification.xml_parser import parse_xml_file

# Путь к конфигу фильтров
FILTERS_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "filters_config.json"
)


def _load_filters_config():
    """
    Загружает конфигурацию фильтров из filters_config.json.
    Если файл не существует — fallback на grabber_settings.py.
    Если и его нет — значения по умолчанию.

    ✅ ИСПРАВЛЕНО: whitelist_tags ОБЪЕДИНЯЕТСЯ с TRANSLATABLE_TAGS
    а не заменяет их полностью.
    """
    # Загружаем стандартные теги
    from utils.rimworld_xml import TRANSLATABLE_TAGS

    # Попытка 1: filters_config.json (GUI)
    if os.path.exists(FILTERS_CONFIG_FILE):
        try:
            with open(FILTERS_CONFIG_FILE, encoding="utf-8") as f:
                config = json.load(f)

            # ✅ ОБЪЕДИНЯЕМ whitelist_tags из конфига со стандартными
            config_whitelist = set(config.get("whitelist_tags", []))
            whitelist_tags = TRANSLATABLE_TAGS | config_whitelist  # Объединение

            return {
                "whitelist_tags": whitelist_tags,
                "blacklist_tags": set(config.get("blacklist_tags", [])),
                "blacklist_patterns": config.get("blacklist_patterns", []),
                "min_text_length": config.get("min_text_length", 2),
                "max_text_length": config.get("max_text_length", 200),
                "priority_suffixes": config.get("priority_suffixes", []),
                "partial_tag_matches": config.get("partial_tag_matches", []),
                "aggressive_fallback": config.get("aggressive_fallback", False),
                "enable_elem_tag_check": config.get("enable_elem_tag_check", True),
                "enable_space_fallback": config.get("enable_space_fallback", True),
                "enable_mod_settings_framework": config.get("enable_mod_settings_framework", True),
                "enable_dollar_variable_replace": config.get(
                    "enable_dollar_variable_replace", True
                ),
            }
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Ошибка чтения {FILTERS_CONFIG_FILE}: {e}, fallback на стандартные")

    # Попытка 2: grabber_settings.py
    try:
        from grabber_settings import (
            AGGRESSIVE_FALLBACK,
            BLACKLIST_PATTERNS,
            BLACKLIST_TAGS,
            MIN_TEXT_LENGTH,
            PRIORITY_SUFFIXES,
            WHITELIST_TAGS,
        )

        # ✅ ОБЪЕДИНЯЕМ
        config_whitelist = set(WHITELIST_TAGS) if WHITELIST_TAGS else set()
        whitelist_tags = TRANSLATABLE_TAGS | config_whitelist

        return {
            "whitelist_tags": whitelist_tags,
            "blacklist_tags": set(BLACKLIST_TAGS) if BLACKLIST_TAGS else set(),
            "blacklist_patterns": list(BLACKLIST_PATTERNS) if BLACKLIST_PATTERNS else [],
            "min_text_length": MIN_TEXT_LENGTH if MIN_TEXT_LENGTH else 2,
            "priority_suffixes": list(PRIORITY_SUFFIXES) if PRIORITY_SUFFIXES else [],
            "aggressive_fallback": AGGRESSIVE_FALLBACK if AGGRESSIVE_FALLBACK else False,
        }
    except ImportError:
        pass

    # Попытка 3: значения по умолчанию (TRANSLATABLE_TAGS)
    from utils.rimworld_xml import PARTIAL_TAG_MATCHES

    return {
        "whitelist_tags": TRANSLATABLE_TAGS,
        "blacklist_tags": set(),
        "blacklist_patterns": [],
        "min_text_length": 2,
        "max_text_length": 200,
        "priority_suffixes": [],
        "partial_tag_matches": PARTIAL_TAG_MATCHES,
        "aggressive_fallback": False,
        "enable_elem_tag_check": True,
        "enable_space_fallback": True,
        "enable_mod_settings_framework": True,
        "enable_dollar_variable_replace": True,
    }


def _sort_by_priority(fields: dict, priority_suffixes: list) -> dict:
    """
    Сортирует поля по приоритету на основе суффиксов ключей.
    Поля с приоритетными суффиксами идут первыми.
    """
    if not priority_suffixes:
        return fields

    priority_keys = [s.lower() for s in priority_suffixes]

    def get_priority(key):
        key_lower = key.lower()
        for i, suffix in enumerate(priority_keys):
            if key_lower.endswith(suffix):
                return i  # Чем меньше индекс, тем выше приоритет
        return len(priority_keys)  # Без приоритета — в конец

    sorted_keys = sorted(fields.keys(), key=get_priority)
    return {k: fields[k] for k in sorted_keys}


def collect_defs_with_meta(defs_dir, logger=None, filters_config=None):
    """
    Собирает определения из XML файлов с поддержкой фильтров.

    Args:
        defs_dir: Папка с Defs
        logger: Логгер
        filters_config: Конфигурация фильтров (если None — загружается автоматически)
    """
    # Загружаем фильтры
    if filters_config is None:
        filters_config = _load_filters_config()

    if logger is None:
        logger = get_logger(__name__)
    defs_index, defs_rel, defs_meta = {}, {}, {}

    if not os.path.exists(defs_dir):
        return defs_index, defs_rel, None, None, defs_meta

    for root_dir, _, files in safe_walk(defs_dir, max_depth=10):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue

            path = os.path.join(root_dir, fn)
            tree = parse_xml_file(path, logger)
            if tree is None:
                continue

            try:
                root = tree
                if root is None:
                    continue

                # Рекурсивно ищем ВСЕ элементы с defName (даже вложенные!)
                def find_all_defs_with_defname(element, parent_def_type=""):
                    """Рекурсивно находит все элементы с defName."""
                    found_defs = []

                    for child in element:
                        if not isinstance(child.tag, str):
                            continue

                        # Проверяем есть ли defName
                        dn = child.find("defName")
                        if dn is not None and dn.text and dn.text.strip():
                            dname = dn.text.strip()
                            def_type = child.tag
                            found_defs.append((child, def_type, dname))

                        # Рекурсивно проверяем детей
                        found_defs.extend(find_all_defs_with_defname(child, child.tag))

                    return found_defs

                all_defs = find_all_defs_with_defname(root)

                for def_el, def_type, dname in all_defs:
                    full_key = f"{def_type}_{dname}"

                    # DefInjected структура строится по ТИПУ ДЕФА (стандарт RimWorld)
                    # Например: DefInjected/AbilityDef/file.xml (не DefInjected/Abilities/)
                    defs_rel[full_key] = os.path.join(def_type, fn)
                    defs_meta[full_key] = {
                        "Abstract": def_el.get("Abstract", "false"),
                        "def_type": def_type,
                    }

                    # ✅ Передаём все параметры фильтров в extract_subfields
                    extracted = extract_subfields(
                        def_el,
                        "",
                        logger,
                        whitelist_tags=filters_config["whitelist_tags"],
                        blacklist_tags=filters_config["blacklist_tags"],
                        blacklist_patterns=filters_config["blacklist_patterns"],
                        min_text_length=filters_config["min_text_length"],
                        max_text_length=filters_config.get("max_text_length", 200),
                        partial_tag_matches=filters_config.get("partial_tag_matches", []),
                        enable_space_fallback=filters_config.get("enable_space_fallback", True),
                    )

                    # ✅ Применяем приоритизацию по суффиксам
                    if filters_config.get("priority_suffixes"):
                        extracted = _sort_by_priority(
                            extracted, filters_config["priority_suffixes"]
                        )

                    if extracted:
                        defs_index[full_key] = {k.lstrip("."): v for k, v in extracted.items()}

            except Exception as e:
                logger.error(f"Ошибка при обработке {path}: {e}")

    return defs_index, defs_rel, None, None, defs_meta


def collect_english_source(lang_eng_dir, logger=None):
    """
    Collects English source strings from the language directory.
    
    Handles both formats:
    1. Direct tags: <LanguageData><Key1>Value1</Key1></LanguageData>
    2. Keyed block: <LanguageData><Keyed><li><key>Key1</key><value>Value1</value></li></Keyed></LanguageData>
    
    Args:
        lang_eng_dir: Path to the English language directory
        logger: Logger instance
        
    Returns:
        Dictionary mapping key -> value
    """
    if logger is None:
        logger = get_logger(__name__)
    res = {}
    if not os.path.exists(lang_eng_dir):
        return res

    for root_dir, _, files in safe_walk(lang_eng_dir, max_depth=5):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            tree = parse_xml_file(os.path.join(root_dir, fn), logger)
            if tree is not None:
                root = tree
                
                # First, try to extract from Keyed block (li/key/value structure)
                keyed_block = None
                for el in root.findall(".//Keyed") + root.findall(".//keyed"):
                    if el is not None:
                        keyed_block = el
                        break
                
                if keyed_block is not None:
                    for li in keyed_block.findall(".//li"):
                        ke = li.find("key")
                        ve = li.find("value")
                        if ke is not None and ke.text and ke.text.strip():
                            key = ke.text.strip()
                            value = ve.text.strip() if ve is not None and ve.text else ""
                            if key not in res:  # Don't override Keyed block entries
                                res[key] = value
                
                # Also extract from direct child tags
                for c in root:
                    if c.tag in ("LanguageData", "Keyed", "keyed"):
                        continue
                    if c.text:
                        key = c.tag
                        if key not in res:  # Don't override Keyed block entries
                            res[key] = c.text.strip()
    return res


def collect_keyed_entities(lang_eng_dir, logger=None):
    """
    Collects Keyed entities from the Keyed folder.
    
    Handles both formats:
    1. Direct tags: <LanguageData><Key1>Value1</Key1><Key2>Value2</Key2></LanguageData>
    2. Keyed block: <LanguageData><Keyed><li><key>Key1</key><value>Value1</value></li></Keyed></LanguageData>
    
    Args:
        lang_eng_dir: Path to the language directory
        logger: Logger instance
        
    Returns:
        Dictionary mapping relative folder -> filename -> {key: value}
    """
    if logger is None:
        logger = get_logger(__name__)
    res = {}
    kp = os.path.join(lang_eng_dir, "Keyed")
    if not os.path.exists(kp):
        return res

    for root_dir, _, files in safe_walk(kp, max_depth=3):
        rel = os.path.relpath(root_dir, kp)
        fd = {}
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            tree = parse_xml_file(os.path.join(root_dir, fn), logger)
            if tree is not None:
                root = tree
                kv = {}
                
                # First, try to extract from Keyed block (li/key/value structure)
                keyed_block = None
                for el in root.findall(".//Keyed") + root.findall(".//keyed"):
                    if isinstance(el, etree._Element):
                        keyed_block = el
                        break
                
                if keyed_block is not None:
                    # Extract from li/key/value structure
                    for li in keyed_block.findall(".//li"):
                        ke = li.find("key")
                        ve = li.find("value")
                        if ke is not None and ke.text and ke.text.strip():
                            key = ke.text.strip()
                            value = ve.text.strip() if ve is not None and ve.text else ""
                            kv[key] = value
                
                # Also extract from direct child tags (fallback/simple format)
                for c in root:
                    if c.tag not in ("LanguageData", "Keyed", "keyed") and c.text:
                        key = c.tag
                        if key not in kv:  # Don't override Keyed block entries
                            kv[key] = c.text.strip()
                
                if kv:
                    fd[os.path.splitext(fn)[0]] = kv
        if fd:
            res[rel] = fd
    return res


def collect_existing_translations(target_lang_dir, logger=None):
    """
    Collects existing translations from the target language directory.
    
    Handles both formats:
    1. Direct tags: <LanguageData><Key1>Value1</Key1></LanguageData>
    2. Keyed block: <LanguageData><Keyed><li><key>Key1</key><value>Value1</value></li></Keyed></LanguageData>
    
    Args:
        target_lang_dir: Path to the target language directory
        logger: Logger instance
        
    Returns:
        Tuple of (translation_map, index_map)
    """
    if logger is None:
        logger = get_logger(__name__)
    emap, eidx = {}, {}
    if not os.path.exists(target_lang_dir):
        return emap, eidx

    for root_dir, _, files in safe_walk(target_lang_dir, max_depth=5):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue
            path = os.path.join(root_dir, fn)
            tree = parse_xml_file(path, logger)
            if tree is not None:
                root = tree
                
                # First, try to extract from Keyed block
                keyed_block = None
                for el in root.findall(".//Keyed") + root.findall(".//keyed"):
                    if el is not None:
                        keyed_block = el
                        break
                
                if keyed_block is not None:
                    for li in keyed_block.findall(".//li"):
                        ke = li.find("key")
                        ve = li.find("value")
                        if ke is not None and ke.text and ke.text.strip():
                            key = ke.text.strip()
                            if ve is not None and ve.text:
                                emap[key] = ve.text.strip()
                                eidx[key] = path
                
                # Also extract from direct child tags
                for c in root:
                    if c.tag and c.text and c.tag not in ("LanguageData", "Keyed", "keyed"):
                        key = c.tag
                        if key not in emap:  # Don't override Keyed block entries
                            emap[key] = c.text.strip()
                            eidx[key] = path
    return emap, eidx


def collect_defs_with_parent_resolution(
    defs_dir: str, logger=None, filters_config=None
) -> tuple[dict, dict, dict]:
    """
    Собирает Defs с разрешением наследования ParentName/Name.

    Это улучшенная версия collect_defs_with_meta которая:
    1. Сначала собирает все именованные элементы (Name="...")
    2. Разрешает цепочки наследования
    3. Извлекает текст из разрешённых элементов

    Args:
        defs_dir: Папка с Defs
        logger: Логгер
        filters_config: Конфигурация фильтров

    Returns:
        (defs_index, defs_rel, defs_meta) - аналогично collect_defs_with_meta
    """
    from utils.parent_resolver import resolve_def_inheritance, resolve_parent_chains

    if logger is None:
        logger = get_logger(__name__)

    if filters_config is None:
        filters_config = _load_filters_config()

    defs_index, defs_rel, defs_meta = {}, {}, {}

    if not os.path.exists(defs_dir):
        return defs_index, defs_rel, defs_meta

    # Шаг 1: Собираем реестр всех именованных элементов
    if logger:
        logger.info("  Сбор именованных элементов для разрешения наследования...")

    name_registry = resolve_parent_chains([defs_dir], logger=logger)

    # Импорт улучшителя Def-ов
    from utils.def_field_enhancer import enhance_def_element

    # Шаг 2: Проходим по всем XML файлам и извлекаем Defs
    if logger:
        logger.info(f"  Начало обработки папки Defs: {defs_dir}")

    processed_count = 0
    skipped_count = 0

    for root_dir, _, files in safe_walk(defs_dir, max_depth=10):
        for fn in files:
            if not fn.lower().endswith(".xml"):
                continue

            path = os.path.join(root_dir, fn)
            tree = parse_xml_file(path, logger)
            if tree is None:
                skipped_count += 1
                if logger:
                    logger.debug(f"  Пропущен файл: {os.path.basename(path)}")
                continue

            processed_count += 1

            try:
                root = tree
                for def_el in root:
                    if not isinstance(def_el.tag, str):
                        continue

                    def_type = def_el.tag
                    dn = def_el.find("defName")
                    if dn is None or not dn.text:
                        continue

                    dname = dn.text.strip()
                    full_key = f"{def_type}_{dname}"

                    # DefInjected структура
                    defs_rel[full_key] = os.path.join(def_type, fn)
                    defs_meta[full_key] = {
                        "Abstract": def_el.get("Abstract", "false"),
                        "def_type": def_type,
                        "HasParent": bool(def_el.get("ParentName")),
                    }

                    # Разрешаем наследование если есть ParentName
                    if def_el.get("ParentName"):
                        resolved_def = resolve_def_inheritance(def_el, name_registry)
                        # ✅ УЛУЧШЕНИЕ: Добавляем недостающие поля
                        if filters_config.get("enable_elem_tag_check", True):
                            enhance_def_element(resolved_def)
                        extracted = extract_subfields(
                            resolved_def,
                            "",
                            logger,
                            whitelist_tags=filters_config["whitelist_tags"],
                            blacklist_tags=filters_config["blacklist_tags"],
                            blacklist_patterns=filters_config["blacklist_patterns"],
                            min_text_length=filters_config["min_text_length"],
                            max_text_length=filters_config.get("max_text_length", 200),
                            partial_tag_matches=filters_config.get("partial_tag_matches", []),
                            enable_space_fallback=filters_config.get("enable_space_fallback", True),
                        )
                    else:
                        # ✅ УЛУЧШЕНИЕ: Добавляем недостающие поля даже без наследования
                        if filters_config.get("enable_elem_tag_check", True):
                            enhance_def_element(def_el)
                        # Нет наследования - извлекаем как есть
                        extracted = extract_subfields(
                            def_el,
                            "",
                            logger,
                            whitelist_tags=filters_config["whitelist_tags"],
                            blacklist_tags=filters_config["blacklist_tags"],
                            blacklist_patterns=filters_config["blacklist_patterns"],
                            min_text_length=filters_config["min_text_length"],
                            max_text_length=filters_config.get("max_text_length", 200),
                            partial_tag_matches=filters_config.get("partial_tag_matches", []),
                            enable_space_fallback=filters_config.get("enable_space_fallback", True),
                        )

                    # Применяем приоритизацию
                    if filters_config.get("priority_suffixes"):
                        extracted = _sort_by_priority(
                            extracted, filters_config["priority_suffixes"]
                        )

                    if extracted:
                        defs_index[full_key] = {k.lstrip("."): v for k, v in extracted.items()}

            except Exception as e:
                logger.error(f"Ошибка при обработке {path}: {e}")

    if logger:
        logger.info(f"  Собрано {len(defs_index)} Defs (с разрешением наследования)")

    return defs_index, defs_rel, defs_meta


def collect_defs_with_patches(
    defs_dir: str, patches_dir: str = None, logger=None, filters_config=None
) -> tuple[dict, dict, dict]:
    """
    Собирает Defs с обработкой патчей.

    Args:
        defs_dir: Папка с Defs
        patches_dir: Папка с патчами (если None - ищем Patches/ рядом с defs_dir)
        logger: Логгер
        filters_config: Конфигурация фильтров

    Returns:
        (defs_index, defs_rel, defs_meta) с применёнными патчами
    """
    from utils.patch_processor import process_patches

    if logger is None:
        logger = get_logger(__name__)

    # Сначала собираем обычные Defs
    defs_index, defs_rel, _, _, defs_meta = collect_defs_with_meta(
        defs_dir, logger=logger, filters_config=filters_config
    )

    # Определяем папку с патчами
    if patches_dir is None:
        patches_dir = os.path.join(os.path.dirname(defs_dir), "Patches")

    if not os.path.exists(patches_dir):
        if logger:
            logger.debug(f"  Папка патчей не найдена: {patches_dir}")
        return defs_index, defs_rel, None, None, defs_meta

    # Обрабатываем патчи
    if logger:
        logger.info(f"  Обработка патчей из: {patches_dir}")

    defs_index = process_patches(
        patches_dir, defs_index, logger=logger, filters_config=filters_config
    )

    if logger:
        logger.info(f"  После патчей: {len(defs_index)} Defs")

    return defs_index, defs_rel, None, None, defs_meta


def collect_translatable_strings(file_path: str, logger=None) -> dict:
    """
    Извлекает переводимые строки из XML файла мода.

    Args:
        file_path: Путь к XML файлу
        logger: Логгер

    Returns:
        Словарь {ключ: значение} с переводимыми строками
    """
    if logger is None:
        logger = get_logger(__name__)

    result = {}
    root = parse_xml_file(file_path, logger)
    if root is None:
        return result

    from utils.rimworld_xml import extract_subfields, TRANSLATABLE_TAGS

    filters_config = _load_filters_config()

    fields = extract_subfields(
        root,
        "",
        logger,
        whitelist_tags=filters_config.get("whitelist_tags", TRANSLATABLE_TAGS),
        blacklist_tags=filters_config.get("blacklist_tags", set()),
        blacklist_patterns=filters_config.get("blacklist_patterns", []),
        min_text_length=filters_config.get("min_text_length", 2),
        max_text_length=filters_config.get("max_text_length", 200),
        partial_tag_matches=filters_config.get("partial_tag_matches", []),
        enable_space_fallback=filters_config.get("enable_space_fallback", True),
    )

    for key, value in fields.items():
        if value and len(str(value).strip()) > 1:
            result[key] = value.strip()

    return result


def collect_defs_full(
    defs_dir: str,
    patches_dir: str = None,
    resolve_parents: bool = True,
    process_patches_flag: bool = True,
    logger=None,
    filters_config=None,
) -> tuple[dict, dict, dict]:
    """
    Полная функция сбора Defs со всеми улучшениями:
    - Разрешение наследования ParentName/Name
    - Обработка патчей
    - Извлечение переводимых строк

    Args:
        defs_dir: Папка с Defs
        patches_dir: Папка с патчами (опционально)
        resolve_parents: Разрешать наследование
        process_patches_flag: Обрабатывать патчи
        logger: Логгер
        filters_config: Конфигурация фильтров

    Returns:
        (defs_index, defs_rel, defs_meta)
    """
    if logger is None:
        logger = get_logger(__name__)

    if resolve_parents:
        # Используем версию с разрешением наследования
        defs_index, defs_rel, defs_meta = collect_defs_with_parent_resolution(
            defs_dir, logger=logger, filters_config=filters_config
        )
    else:
        # Обычная версия
        defs_index, defs_rel, _, _, defs_meta = collect_defs_with_meta(
            defs_dir, logger=logger, filters_config=filters_config
        )

    # Обработка патчей
    if process_patches_flag:
        if patches_dir is None:
            patches_dir = os.path.join(os.path.dirname(defs_dir), "Patches")

        if os.path.exists(patches_dir):
            from utils.patch_processor import process_patches

            if logger:
                logger.info(f"  Обработка патчей: {patches_dir}")

            defs_index = process_patches(
                patches_dir, defs_index, logger=logger, filters_config=filters_config
            )

    return defs_index, defs_rel, defs_meta
