"""
Функции merge/проверки переводов по алгоритму RimTrans.

Ключевые правила:
1. Перевод сохраняется ТОЛЬКО если != "TODO" и != оригинала
2. UNUSED поля помечаются комментарием <!-- UNUSED -->
3. Fuzzy поля помечаются комментарием <!-- FUZZY -->
4. Дубликаты пропускаются при записи
"""

import os

import lxml.etree as etree
from verification.xml_parser import safe_parse_xml
from typing import Optional


# Константы (как в RimTrans)
TEXT_UNUSED = "UNUSED"
TEXT_EN = "EN:"
TEXT_TODO = "TODO"
TEXT_FUZZY = "FUZZY"


def is_valid_translation(translation: str, origin: str) -> bool:
    """
    Проверяет что перевод валиден (не TODO и не копия оригинала).

    Алгоритм RimTrans:
    if (translation && translation !== TEXT_TODO && translation !== origin)
        -> VALID

    Args:
        translation: Текст перевода
        origin: Оригинальный текст

    Returns:
        True если перевод валиден
    """
    if not translation or not translation.strip():
        return False
    
    trans = translation.strip()
    
    # Не TODO
    if trans.upper() == "TODO":
        return False
    
    # Не копия оригинала
    if trans == origin.strip():
        return False
    
    return True


def scan_existing_translations_per_file(def_injected_dir: str, logger=None) -> dict[str, dict]:
    """
    Сканирует ВСЕ DefInjected файлы и создаёт карту:
    {tag: {value, origin (из EN: комментария), file}}

    Это улучшенная версия которая также извлекает оригинал из комментариев.

    Args:
        def_injected_dir: Путь к DefInjected
        logger: Логгер

    Returns:
        {tagname: {"value": str, "origin": str, "file": str}}
    """
    result = {}
    
    if not def_injected_dir or not os.path.exists(def_injected_dir):
        return result
    
    for root_dir, _, files in os.walk(def_injected_dir):
        for fn in files:
            if not fn.endswith(".xml"):
                continue
            
            filepath = os.path.join(root_dir, fn)
            try:
                root = safe_parse_xml(filepath)
                if root is None:
                    continue
                
                last_en_comment = None  # Последний EN: комментарий
                
                for child in root:
                    if not isinstance(child.tag, str):
                        continue
                    
                    # Проверяем комментарии перед тегом
                    if child.tag == "LanguageData":
                        continue
                    
                    # Ищем комментарий <!-- EN: ... --> перед этим элементом
                    # В ElementTree комментарии - это отдельные элементы с тегом '!'
                    # Но обычно EN: комментарий находится в tail предыдущего элемента
                    # или как отдельный элемент
                    
                    # Проще: читаем XML как текст и ищем EN: комментарии
                    # Но для скорости используем origin_map из файла
                    
                    if child.text and child.text.strip():
                        value = child.text.strip()
                        tag = child.tag
                        
                        # Пропускаем _OBSOLETE_ теги
                        if tag.startswith("_OBSOLETE_"):
                            tag = tag[len("_OBSOLETE_"):]
                        
                        result[tag] = {
                            "value": value,
                            "origin": last_en_comment or "",
                            "file": filepath,
                        }
                        
                        # Сбрасываем комментарий
                        last_en_comment = None
                    
                    # Проверяем tail на EN: комментарий
                    if child.tail:
                        import re
                        en_match = re.search(r'<!--\s*EN:\s*(.*?)\s*-->', child.tail)
                        if en_match:
                            last_en_comment = en_match.group(1).strip()
                            
            except Exception as e:
                if logger:
                    logger.debug(f"Ошибка чтения {filepath}: {e}")
    
    return result


def merge_translation_fields(
    new_fields: dict[str, str],  # {field_path: english_value} из Defs
    existing_map: dict[str, dict],  # {tagname: {value, origin, file}} из DefInjected
    orig_def_name: str,
    logger=None
) -> list[tuple[str, str, Optional[str]]]:
    """
    Объединяет новые поля из Defs с существующими переводами.

    Алгоритм RimTrans merge():
    1. Для каждого нового поля ищем существующий перевод
    2. Если перевод валиден (не TODO, не копия оригинала) -> используем его
    3. Иначе -> оставляем для обработки (TODO или fuzzy)

    Args:
        new_fields: {field_path: english_value} из Defs
        existing_map: {tagname: {value, origin, file}} из DefInjected
        orig_def_name: Имя Def (например "CleanSelf")
        logger: Логгер

    Returns:
        [(field_path, eng_val, existing_translation_or_None), ...]
    """
    result = []
    
    for field_path, eng_val in new_fields.items():
        tagname = f"{orig_def_name}.{field_path}"
        
        if tagname in existing_map:
            existing = existing_map[tagname]
            translation = existing.get("value", "")
            origin = existing.get("origin", "")
            
            # Проверяем валидность перевода
            if is_valid_translation(translation, origin or eng_val):
                if logger:
                    logger.debug(f"  ✓ Валидный перевод: {tagname} = '{translation[:40]}...'")
                result.append((field_path, eng_val, translation))
            else:
                # Перевод невалиден (TODO или копия оригинала)
                if logger:
                    logger.debug(f"  ⚠ Невалидный перевод: {tagname} ('{translation[:40]}')")
                result.append((field_path, eng_val, None))
        else:
            # Нет существующего перевода
            result.append((field_path, eng_val, None))
    
    return result


def detect_unused_tags(
    new_tags: set[str],
    existing_tags: set[str]
) -> set[str]:
    """
    Находит UNUSED теги (есть в переводе но нет в Defs).

    Args:
        new_tags: Теги из Defs
        existing_tags: Теги из DefInjected

    Returns:
        set unused тегов
    """
    return existing_tags - new_tags


def detect_fuzzy_tags(
    fields: dict[str, str],
    existing_tags: set[str],
    partial_matches: list[str] = None
) -> dict[str, str]:
    """
    Находит FUZZY теги (похожие но не точные совпадения).

    Args:
        fields: {field_path: value} из Defs
        existing_tags: Теги из DefInjected
        partial_matches: Список частичных совпадений для fuzzy

    Returns:
        {field_path: fuzzy_translation}
    """
    result = {}
    
    if not partial_matches:
        return result
    
    for field_path, eng_val in fields.items():
        # Ищем похожий тег
        for existing_tag in existing_tags:
            # Jaccard similarity или простое совпадение частей
            parts_new = set(field_path.replace(".", " ").replace("_", " ").lower().split())
            parts_existing = set(existing_tag.replace(".", " ").replace("_", " ").lower().split())
            
            if parts_new and parts_existing:
                intersection = parts_new & parts_existing
                union = parts_new | parts_existing
                similarity = len(intersection) / len(union)
                
                if similarity > 0.4:  # Порог fuzzy как в RimTrans
                    result[field_path] = existing_tag
    
    return result
