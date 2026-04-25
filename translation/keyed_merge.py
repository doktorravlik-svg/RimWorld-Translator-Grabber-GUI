# keyed_merge.py
"""
Модуль для записи Keyed XML файлов с объединением переводов.

Создаёт и обновляет Keyed XML файлы, объединяя существующие переводы
с новыми, обеспечивая безопасную обработку XML тегов.
"""

import os
from typing import Any

from lxml import etree
from verification.xml_parser import get_xml_content_hash, safe_parse_xml, write_tree_pretty


def _safe_rel_folder(rel: str) -> str:
    """Нормализует rel_folder: '.' или '' -> '' ; заменяет обратные слеши на прямые.

    Args:
        rel: Относительный путь к папке

    Returns:
        Нормализованный относительный путь
    """
    if not rel or rel in (".", ""):
        return ""
    return rel.replace("\\", "/").strip("/")


def _ensure_dir(path: str, logger: Any | None = None) -> bool:
    """Создаёт директорию если она не существует.

    Args:
        path: Путь к директории
        logger: Логгер для записи ошибок

    Returns:
        True если директория создана/существует, False при ошибке
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        if logger:
            logger.error(f"Failed to create directory {path}: {e}")
        return False


def _is_valid_xml_tag(tag: str) -> bool:
    """Простая проверка валидности имени XML-тега.

    Args:
        tag: Имя тега для проверки

    Returns:
        True если тег валидный, False иначе
    """
    if not tag or not isinstance(tag, str):
        return False
    if any(ch.isspace() for ch in tag):
        return False
    for bad in (
        "<",
        ">",
        "/",
        "\\",
        "?",
        "!",
        "@",
        "#",
        "$",
        "%",
        "^",
        "&",
        "*",
        "(",
        ")",
        "+",
        "=",
        "{",
        "}",
        "[",
        "]",
        ";",
        ":",
        '"',
        "'",
    ):
        if bad in tag:
            return False
    if tag[0].isdigit():
        return False
    return True


def write_keyed_files_mirror_with_merge(
    keyed_files: dict[str, dict[str, dict[str, str | None]]],
    target_dir: str,
    existing_map: dict[str, str],
    existing_index: dict[str, str],
    source_map: dict[str, str],
    logger: Any | None = None,
    aggressive: bool = False,
) -> list[str]:
    """
    Записывает Keyed XML файлы с объединением переводов.

    Создаёт структуру файлов Keyed/<rel>/<fname>.xml, объединяя
    существующие переводы с новыми из source_map.

    Args:
        keyed_files: Словарь {rel_folder: {filename: {key: value}}}
        target_dir: Целевая директория для записи
        existing_map: Карта существующих переводов {key: value}
        existing_index: Индекс существующих файлов {key: filepath}
        source_map: Карта исходных переводов для объединения
        logger: Логгер для записи сообщений
        aggressive: Агрессивный режим (не используется)

    Returns:
        Список созданных/обновлённых файлов
    """
    created = []
    keyed_base_dir = os.path.join(target_dir, "Keyed")
    try:
        os.makedirs(keyed_base_dir, exist_ok=True)
    except Exception as e:
        if logger:
            logger.error(f"Cannot create base Keyed dir {keyed_base_dir}: {e}")
        return created

    # === Поиск дубликатов по содержимому ===
    existing_duplicate_map = {}  # хеш -> список файлов
    if os.path.exists(keyed_base_dir):
        for root_dir, _, files in os.walk(keyed_base_dir):
            for fname in files:
                if fname.endswith(".xml"):
                    fpath = os.path.join(root_dir, fname)
                    try:
                        root = safe_parse_xml(fpath)
                        if root is not None:
                            content_hash = get_xml_content_hash(root)
                            if content_hash not in existing_duplicate_map:
                                existing_duplicate_map[content_hash] = []
                            existing_duplicate_map[content_hash].append(fpath)
                    except Exception:
                        pass

    # Храним все хеши содержимого для проверки
    existing_content_hashes = existing_duplicate_map  # хеш -> список файлов
    if existing_content_hashes and logger:
        duplicate_count = sum(1 for v in existing_content_hashes.values() if len(v) > 1)
        logger.info(
            f"Проверено {len(existing_content_hashes)} уникальных содержимого в Keyed файлах, найдено {duplicate_count} групп дубликатов"
        )

    for rel_folder, files_map in (keyed_files or {}).items():
        rel_norm = (
            ""
            if not rel_folder or rel_folder in (".", "")
            else rel_folder.replace("\\", "/").strip("/")
        )
        out_folder = os.path.normpath(os.path.join(keyed_base_dir, rel_norm))
        try:
            os.makedirs(out_folder, exist_ok=True)
        except Exception as e:
            if logger:
                logger.error(f"Cannot create out_folder {out_folder}: {e}")
            continue

        for fname, kv in (files_map or {}).items():
            chosen_path = os.path.join(out_folder, f"{fname}.xml")
            if logger:
                logger.debug(f"Keyed: preparing file {chosen_path}")
                logger.debug(
                    f"Keyed: kv keys count = {len(kv or {})}; sample keys = {list((kv or {}).keys())[:20]}"
                )

            if not kv:
                if logger:
                    logger.debug(f"Keyed: skip empty kv for {fname} (rel={rel_norm})")
                continue

            # Load existing tree if present
            if os.path.exists(chosen_path):
                try:
                    root = safe_parse_xml(chosen_path)
                    if root is None:
                        root = etree.Element("LanguageData")
                except Exception as e:
                    if logger:
                        logger.warn(
                            f"Keyed: failed to parse existing {chosen_path}: {e}; creating new root"
                        )
                    root = etree.Element("LanguageData")
            else:
                root = etree.Element("LanguageData")

            # find existing keyed block and direct tags
            keyed_block = None
            # safe search for Keyed element(s)
            for el in root.findall(".//Keyed") + root.findall(".//keyed"):
                if isinstance(el, etree._Element):
                    keyed_block = el
                    break

            # collect existing direct tag names (safe)
            existing_direct_tags = set()
            for ch in list(root):
                try:
                    tag = getattr(ch, "tag", None)
                    if isinstance(tag, str):
                        tag_name = tag
                        # skip the container tag 'Keyed' itself
                        if tag_name.lower() != "keyed" and tag_name != "LanguageData":
                            existing_direct_tags.add(tag_name)
                except Exception:
                    continue

            added_any = False

            # Process each key in kv
            for key, english_val in kv.items():
                try:
                    if key is None:
                        continue
                    key = str(key).strip()
                    eng_val = english_val if english_val is not None else ""
                    # choose final value: prefer existing_map (translated), then source_map (english), else english_val
                    final_val = None
                    src_label = "none"
                    if (
                        existing_map
                        and key in existing_map
                        and existing_map[key]
                        and str(existing_map[key]).strip()
                    ):
                        final_val = existing_map[key]
                        src_label = "existing_map"
                    elif (
                        source_map
                        and key in source_map
                        and source_map[key]
                        and str(source_map[key]).strip()
                    ):
                        final_val = source_map[key]
                        src_label = "source_map"
                    else:
                        final_val = eng_val
                        src_label = "english"

                    if final_val is None:
                        final_val = ""

                    if logger:
                        logger.debug(
                            f"Keyed: key='{key}' chosen_src={src_label} final_len={len(str(final_val))}"
                        )

                    # decide whether key is valid XML tag name
                    if _is_valid_xml_tag(key):
                        # write as direct tag on root
                        if key in existing_direct_tags:
                            existing_el = None
                            for ch in list(root):
                                try:
                                        tag = getattr(ch, "tag", None)
                                        if isinstance(tag, str) and tag == key:
                                            existing_el = ch
                                            break
                                except Exception:
                                    continue
                            if existing_el is not None:
                                if not (existing_el.text and existing_el.text.strip()):
                                    existing_el.text = str(final_val)
                                    added_any = True
                                    if logger:
                                        logger.debug(f"Keyed: filled existing direct tag <{key}>")
                            elif logger:
                                    logger.debug(
                                        f"Keyed: direct tag <{key}> already has value; skipped"
                                    )
                            else:
                                el = etree.SubElement(root, key)
                                el.text = str(final_val)
                                added_any = True
                                if logger:
                                    logger.debug(f"Keyed: added direct tag <{key}> (fallback)")
                        else:
                            try:
                                el = etree.SubElement(root, key)
                                el.text = str(final_val)
                                added_any = True
                                if logger:
                                    logger.debug(f"Keyed: added direct tag <{key}>")
                            except Exception as e:
                                if logger:
                                    logger.debug(
                                        f"Keyed: failed to create direct tag <{key}>: {e}; using Keyed list"
                                    )
                        if keyed_block is None:
                            keyed_block = etree.SubElement(root, "Keyed")
                        exists_in_keyed = False
                        for li in keyed_block.findall(".//li"):
                            ke = li.find("key")
                            if ke is not None and ke.text and ke.text.strip() == key:
                                exists_in_keyed = True
                                ve = li.find("value")
                                if ve is not None and not (ve.text and ve.text.strip()):
                                    ve.text = str(final_val)
                                    added_any = True
                                    if logger:
                                        logger.debug(
                                            f"Keyed: filled existing keyed li for key='{key}'"
                                        )
                                break
                        if not exists_in_keyed:
                            li = etree.SubElement(keyed_block, "li")
                            key_el = etree.SubElement(li, "key")
                            key_el.text = key
                            val_el = etree.SubElement(li, "value")
                            val_el.text = str(final_val)
                            added_any = True
                            if logger:
                                logger.debug(f"Keyed: added new keyed li for key='{key}'")
                    else:
                        # write into Keyed list; avoid duplicates
                        if keyed_block is None:
                            keyed_block = etree.SubElement(root, "Keyed")
                        exists_in_keyed = False
                        for li in keyed_block.findall(".//li"):
                            ke = li.find("key")
                            if ke is not None and ke.text and ke.text.strip() == key:
                                exists_in_keyed = True
                                ve = li.find("value")
                                if ve is not None and not (ve.text and ve.text.strip()):
                                    ve.text = str(final_val)
                                    added_any = True
                                    if logger:
                                        logger.debug(
                                            f"Keyed: filled existing keyed li for key='{key}'"
                                        )
                                break
                        if not exists_in_keyed:
                            li = etree.SubElement(keyed_block, "li")
                            key_el = etree.SubElement(li, "key")
                            key_el.text = key
                            val_el = etree.SubElement(li, "value")
                            val_el.text = str(final_val)
                            added_any = True
                            if logger:
                                logger.debug(f"Keyed: added new keyed li for key='{key}'")
                        else:
                            # fill existing keyed li
                            for li in keyed_block.findall(".//li"):
                                ke = li.find("key")
                                if ke is not None and ke.text and ke.text.strip() == key:
                                    exists_in_keyed = True
                                    ve = li.find("value")
                                    if ve is not None and not (ve.text and ve.text.strip()):
                                        ve.text = str(final_val)
                                        added_any = True
                                        if logger:
                                            logger.debug(
                                                f"Keyed: filled existing keyed li for key='{key}'"
                                            )
                                    break
                        if not exists_in_keyed:
                            li = etree.SubElement(keyed_block, "li")
                            key_el = etree.SubElement(li, "key")
                            key_el.text = key
                            val_el = etree.SubElement(li, "value")
                            val_el.text = str(final_val)
                            added_any = True
                            if logger:
                                logger.debug(f"Keyed: added new keyed li for key='{key}'")
                except Exception as e:
                    if logger:
                        logger.error(f"Keyed: exception processing key '{key}' in {fname}: {e}")
                    continue

            if not added_any:
                if logger:
                    logger.debug(f"Keyed: nothing to write for {chosen_path}")
                continue

            # Safety: ensure chosen_path is inside keyed_base_dir
            keyed_base_dir_norm = os.path.normpath(keyed_base_dir)
            chosen_path_norm = os.path.normpath(chosen_path)
            if not chosen_path_norm.startswith(keyed_base_dir_norm):
                if logger:
                    logger.warn(
                        f"Chosen path {chosen_path} is outside Keyed base; switching to safe path"
                    )
                chosen_path = os.path.join(keyed_base_dir, rel_norm, f"{fname}.xml")
                os.makedirs(os.path.dirname(chosen_path), exist_ok=True)

            # === Проверка на дубликаты по содержимому ===
            new_content_hash = get_xml_content_hash(root)

            # Проверяем, есть ли уже файл с таким же содержимым
            is_duplicate = False
            if new_content_hash in existing_content_hashes:
                # Файл с таким содержимым уже существует
                existing_files = existing_content_hashes[new_content_hash]
                # Проверяем, отличается ли имя файла
                if chosen_path not in existing_files:
                    is_duplicate = True
                    if logger:
                        logger.warn(
                            f"Дубликат: файл {os.path.basename(chosen_path)} пропущен, т.к. содержимое идентично файлам: {[os.path.basename(f) for f in existing_files]}"
                        )
                else:
                    # Файл уже существует с таким же именем - это обновление, а не дубликат
                    pass
            elif os.path.exists(chosen_path):
                # Проверяем, изменилось ли содержимое
                try:
                    existing_root = safe_parse_xml(chosen_path)
                    if existing_root is not None:
                        existing_hash = get_xml_content_hash(existing_root)
                        if existing_hash == new_content_hash:
                            # Содержимое не изменилось - пропускаем
                            if logger:
                                logger.debug(f"Пропущен файл без изменений: {chosen_path}")
                            continue
                except Exception:
                    pass

            if is_duplicate:
                continue

            try:
                ok = write_tree_pretty(root, chosen_path, logger)
                if ok:
                    created.append(chosen_path)
                    if logger:
                        logger.info(f"Created/updated keyed file: {chosen_path}")
                elif logger:
                    logger.warn(f"Failed to write keyed file: {chosen_path}")
            except Exception as e:
                if logger:
                    logger.error(f"Exception while writing keyed file {chosen_path}: {e}")

    return created
