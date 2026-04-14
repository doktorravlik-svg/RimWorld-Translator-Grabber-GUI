# per_def.py
import os
import xml.etree.ElementTree as ET

from translation.matching import find_existing_translation
from translation.obsolete_detector import process_obsolete_tags
from translation.translator import AutoTranslator
from verification.xml_parser import (
    add_or_preserve,
    get_xml_content_hash,
    safe_parse_xml,
    write_tree_pretty,
)


def _ensure_dir(path):
    if not os.path.exists(path):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        os.makedirs(path, exist_ok=True)


def _find_matching_translation_file(target_dir, def_name, tagname, logger=None):
    """
    Ищет существующий файл перевода с отличающимся именем, который содержит нужный тег.

    Returns:
        path к найденному файлу или None
    """
    if not os.path.exists(target_dir):
        return None

    # Сканируем все XML файлы в папке
    for filename in os.listdir(target_dir):
        if not filename.endswith(".xml"):
            continue

        filepath = os.path.join(target_dir, filename)
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Проверяем, есть ли искомый тег
            for child in root:
                # Проверяем точный тег или префикс (например, CleanSelf.reportString)
                if child.tag == tagname or child.tag.startswith(tagname.split(".")[0] + "."):
                    if logger:
                        logger.debug(f"Found matching tag {tagname} in {filename}")
                    return filepath
        except Exception as e:
            if logger:
                logger.debug(f"Error reading {filepath}: {e}")

    return None


def _scan_existing_translations(target_dir, logger=None):
    """
    Сканирует папку и создаёт карту: тег -> файл

    Returns:
        dict: {tagname: filepath}
    """
    tag_to_file = {}

    if not os.path.exists(target_dir):
        return tag_to_file

    for root_dir, dirs, files in os.walk(target_dir):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root_dir, filename)
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()

                for child in root:
                    if child.tag and child.tag not in ("LanguageData", "Keyed"):
                        tag_to_file[child.tag] = filepath
            except Exception as e:
                if logger:
                    logger.debug(f"Error scanning {filepath}: {e}")

    return tag_to_file


def _cleanup_orphan_translations(target_dir, created_files, logger=None):
    """
    Удаляет осиротевшие файлы переводов, которые не соответствуют оригинальным Def файлам.

    Args:
        target_dir: папка DefInjected
        created_files: список файлов, которые были созданы/обновлены
    """
    if not os.path.exists(target_dir):
        return []

    created_paths = set(os.path.abspath(f) for f in created_files)
    orphans = []

    # Собираем все ожидаемые имена файлов из созданных
    expected_files = set()
    for f in created_files:
        expected_files.add(os.path.basename(f))

    # Сканируем все XML файлы
    for root_dir, dirs, files in os.walk(target_dir):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root_dir, filename)
            if os.path.abspath(filepath) in created_paths:
                continue

            # Проверяем, есть ли этот файл в списке созданных
            if filename not in expected_files:
                # Это потенциальный осиротевший файл
                # Но не удаляем сразу - помечаем
                orphans.append(filepath)
                if logger:
                    logger.info(f"Found orphan translation file: {filepath}")

    return orphans


def generate_or_update_per_def_files_v2(
    defs_index,
    defs_rel,
    defs_source_abs,
    defs_file_map,
    defs_meta,
    keyed_map,
    source_map,
    existing_map,
    existing_index,
    target_lang_dir,
    logger=None,
    aggressive=False,
    use_api=False,
    lang_to="Russian",
    cleanup_orphans=False,
    fuzzy=False,
    existing_origin=None,
    check_obsolete=True,
):
    """
    Основная функция создания DefInjected файлов.

    Алгоритм RimTrans merge():
    1. Перевод сохраняется ТОЛЬКО если != "TODO" и != оригинала
    2. UNUSED поля помечаются комментарием <!-- UNUSED -->
    3. Дубликаты пропускаются при записи

    Добавлены параметры:
        cleanup_orphans: если True - помечает осиротевшие файлы переводов
        fuzzy: если True - включает нечёткий поиск переводов (как RimTrans)
        existing_origin: {tagname: original_text} из EN: комментариев
        check_obsolete: если True - проверяет устаревшие теги
    """
    created_files = []
    # Путь к Languages/Russian/DefInjected
    perdef_base = os.path.join(target_lang_dir, "DefInjected")
    _ensure_dir(perdef_base)

    # === Поиск дубликатов по содержимому ===
    existing_duplicate_map = {}
    if os.path.exists(perdef_base):
        for root_dir, _, files in os.walk(perdef_base):
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
    existing_content_hashes = existing_duplicate_map
    if existing_content_hashes and logger:
        duplicate_count = sum(1 for v in existing_content_hashes.values() if len(v) > 1)
        logger.info(
            f"Проверено {len(existing_content_hashes)} уникальных содержимого в DefInjected файлах, найдено {duplicate_count} групп дубликатов"
        )

    # Инициализация переводчика
    translator = AutoTranslator(enabled=use_api, logger=logger, target_lang=lang_to)

    if not defs_index:
        if logger:
            logger.warn("Словарь Defs пуст. Нечего обрабатывать.")
        return created_files

    # Предварительное сканирование существующих переводов для быстрого поиска
    existing_tags_map = _scan_existing_translations(perdef_base, logger)
    if logger and existing_tags_map:
        logger.info(f"Найдено {len(existing_tags_map)} существующих тегов перевода")

    # Счётчики для статистики
    skipped_already_translated = 0
    defs_processed = 0
    defs_with_changes = 0

    # Общий счётчик для прогресса
    total_defs = len(defs_index)
    defs_processed_count = 0

    for def_name, fields in defs_index.items():
        defs_processed_count += 1
        defs_processed += 1

        # fields содержит {'reportString': 'cleaning self', 'label': '...'}
        # def_name теперь в формате "Тип_Имя" (например, "JobDef_CleanSelf")

        # Извлекаем оригинальное имя Def'а из составного ключа
        if "_" in def_name:
            # Разделяем "Тип_Имя" - находим первое подчёркивание
            parts = def_name.split("_", 1)
            def_type = parts[0]
            orig_def_name = parts[1] if len(parts) > 1 else def_name
        else:
            def_type = defs_meta.get(def_name, {}).get("def_type", "")
            orig_def_name = def_name

        relpath = defs_rel.get(def_name, "")

        if logger:
            logger.debug(
                f"Processing def: {def_name} (type: {def_type}, orig: {orig_def_name}), relpath: {relpath}, fields: {list(fields.keys())}"
            )

        # Определяем имя файла СРАЗУ (нужно для проверки папок)
        orig_filename = os.path.basename(relpath)
        if not orig_filename:
            orig_filename = f"Generated_{orig_def_name}.xml"

        # Определяем папку (например, DefInjected/Ability)
        sub_dir = os.path.dirname(relpath)
        out_dir = os.path.join(perdef_base, sub_dir)

        # ПРОВЕРКА: Ищем существующую папку с похожим именем
        # Универсальная проверка для ЛЮБЫХ расхождений
        if not os.path.exists(out_dir) and os.path.exists(perdef_base):
            for existing_dir in os.listdir(perdef_base):
                existing_path = os.path.join(perdef_base, existing_dir)
                if not os.path.isdir(existing_path):
                    continue

                # Варианты совпадения:
                match_found = False

                # 1. Точное совпадение (case-insensitive)
                if existing_dir.lower() == sub_dir.lower():
                    match_found = True

                # 2. С суффиксом Def (Ability → AbilityDef, AbilityDef → Ability)
                elif existing_dir == sub_dir + "Def" or sub_dir == existing_dir + "Def":
                    match_found = True

                # 3. Множественное число (RecipeDefs → RecipeDef, ThingDefs → ThingDef)
                elif existing_dir.rstrip("s") == sub_dir.rstrip("s"):
                    match_found = True

                # 4. Частичное совпадение (TentacleMonster → SoundDef по содержимому файла)
                elif orig_filename and os.path.exists(os.path.join(existing_path, orig_filename)):
                    # Файл с таким же именем существует в другой папке
                    match_found = True
                    if logger:
                        logger.debug(f"  🔍 Найдено по имени файла: {existing_dir}/{orig_filename}")

                if match_found:
                    if logger:
                        logger.info(
                            f"  🔄 Использую существующую папку: {existing_dir} (вместо {sub_dir})"
                        )
                    out_dir = existing_path
                    break

        # Ищем существующий файл с таким же именем
        per_path = os.path.join(out_dir, orig_filename)

        # ПРОВЕРКА: Если файл не существует в текущей out_dir, ищем в АЛЬТЕРНАТИВНЫХ папках
        # Это ключевая проверка из Text-grabber - file_exists(np)
        # УНИВЕРСАЛЬНАЯ - ищет во ВСЕХ папках DefInjected
        if not os.path.exists(per_path) and os.path.exists(perdef_base):
            for existing_dir in os.listdir(perdef_base):
                existing_path = os.path.join(perdef_base, existing_dir, orig_filename)
                if os.path.exists(existing_path):
                    # Проверяем что это не та же папка (чтобы не дублировать)
                    if os.path.normpath(os.path.dirname(existing_path)) != os.path.normpath(
                        out_dir
                    ):
                        if logger:
                            logger.info(
                                f"  🔄 Найден существующий файл: {os.path.relpath(existing_path, perdef_base)}"
                            )
                        out_dir = os.path.dirname(existing_path)
                        per_path = existing_path
                        break

        # === КРИТИЧЕСКАЯ ПРОВЕРКА: Читаем КОНКРЕТНЫЙ файл и проверяем КАКИЕ теги в нём есть ===
        # Это решает проблему "перевод есть в БД/другом файле но нет в нашем файле"
        file_existing_tags = {}  # tagname -> value
        if os.path.exists(per_path):
            try:
                tree_check = ET.parse(per_path)
                root_check = tree_check.getroot()
                for child in root_check:
                    if isinstance(child.tag, str) and child.text and child.text.strip():
                        tag = child.tag
                        # Пропускаем _OBSOLETE_ теги
                        if tag.startswith("_OBSOLETE_"):
                            tag = tag[len("_OBSOLETE_") :]
                        file_existing_tags[tag] = child.text.strip()
                if logger:
                    logger.debug(
                        f"  📄 В файле {os.path.basename(per_path)} найдено {len(file_existing_tags)} тегов"
                    )
            except Exception as e:
                if logger:
                    logger.debug(f"  ⚠️ Ошибка чтения {per_path}: {e}")

        # === ПРОВЕРКА: Все ли поля уже переведены В КОНКРЕТНОМ ФАЙЛЕ? ===
        # Алгоритм RimTrans merge(): перевод валиден только если != TODO и != оригинала
        all_fields_translated = True
        fields_to_process = []

        for field_path, eng_val in fields.items():
            tagname = f"{orig_def_name}.{field_path}"

            # 1. Проверяем ТОЧНО в КОНКРЕТНОМ файле (НЕ в БД или других файлах!)
            if tagname in file_existing_tags:
                existing_val = file_existing_tags[tagname]
                # ✅ ПРОВЕРКА RIMTRANS: перевод != оригинала?
                origin_for_tag = (existing_origin or {}).get(tagname, eng_val)
                if existing_val.upper() == "TODO" or existing_val == origin_for_tag:
                    # Невалидный перевод - нужно обработать
                    if logger:
                        logger.debug(f"  ⚠ Невалидный перевод: {tagname} ('{existing_val[:40]}')")
                    all_fields_translated = False
                    fields_to_process.append((field_path, eng_val, None))
                else:
                    # Валидный перевод - пропускаем
                    if logger:
                        logger.debug(f"  ✓ Уже есть в файле: {tagname}")
                    continue

            # 2. Проверяем ТОЧНОЕ совпадение в existing_map (только если это тот же файл!)
            if tagname in existing_map and existing_map[tagname].strip():
                existing_val = existing_map[tagname]
                origin_for_tag = (existing_origin or {}).get(tagname, eng_val)

                # ✅ ПРОВЕРКА RIMTRANS: перевод валиден?
                if existing_val.upper() == "TODO" or existing_val == origin_for_tag:
                    # Невалидный - нужно обработать
                    all_fields_translated = False
                    fields_to_process.append((field_path, eng_val, None))
                else:
                    # Проверяем что перевод именно из нашего файла
                    tag_file = existing_index.get(tagname, "")
                    if os.path.normpath(tag_file) == os.path.normpath(per_path):
                        if logger:
                            logger.debug(f"  ✓ Найден точный перевод в этом файле: {tagname}")
                        continue

            # 3. Fuzzy поиск (если включён) - для переименованных тегов
            if fuzzy:
                fuzzy_val, fuzzy_path = find_existing_translation(
                    tagname, existing_map, existing_index, logger, fuzzy=True
                )
                if fuzzy_val:
                    if logger:
                        logger.info(f"  🔍 Fuzzy: {tagname} → найден перевод ({fuzzy_path})")
                    all_fields_translated = False
                    fields_to_process.append((field_path, eng_val, fuzzy_val))
                    continue

            # 4. Если дошли сюда - поле нуждается в обработке
            all_fields_translated = False
            fields_to_process.append((field_path, eng_val, None))

        # Если все поля уже есть в файле - пропускаем
        if all_fields_translated and fields:
            skipped_already_translated += 1
            if logger:
                # Показываем подробный лог только для первых 5 и каждого 10-го
                if skipped_already_translated <= 5 or skipped_already_translated % 10 == 0:
                    logger.debug(
                        f"  ⏭ [{defs_processed_count}/{total_defs}] Пропущен (все {len(fields)} полей уже в файле): {def_name}"
                    )
            continue

        # КРИТИЧЕСКАЯ ПРОВЕРКА: Если нечего обрабатывать И файл не существует - не создаём его
        if not fields_to_process and not os.path.exists(per_path):
            if logger:
                logger.debug(f"  ⏭ Файл не существует и нечего добавлять - пропускаем: {per_path}")
            continue

        # Создаём папку только если нужно (файл будет создан)
        _ensure_dir(out_dir)

        # Загружаем существующий XML или создаем новый
        if os.path.exists(per_path):
            try:
                tree_exist = ET.parse(per_path)
                root = tree_exist.getroot()
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка чтения {per_path}: {e}")
                root = ET.Element("LanguageData")
        else:
            root = ET.Element("LanguageData")

        modified = False

        # === ПЕРЕПРОВЕРКА: Проверяем КАЖДЫЙ тег в КОНКРЕТНОМ файле ===
        # Это решает проблему "перевод есть в БД но нет в файле"
        fields_final = []
        for item in fields_to_process:
            if len(item) == 3:
                field_path, eng_val, fuzzy_translation = item
            else:
                field_path, eng_val = item
                fuzzy_translation = None

            tagname = f"{orig_def_name}.{field_path}"

            # Проверяем есть ли тег в КОНКРЕТНОМ файле
            tag_in_file = False
            for child in root:
                if child.tag == tagname and child.text and child.text.strip():
                    tag_in_file = True
                    if logger:
                        logger.debug(f"  ✓ Тег уже в файле: {tagname}")
                    break

            if not tag_in_file:
                # Тега нет в файле - нужно добавить
                fields_final.append((field_path, eng_val, fuzzy_translation))
            # Тег уже есть в файле - пропускаем
            elif logger:
                logger.debug(f"  ⏭ Пропуск (уже в файле): {tagname}")

        # Если после перепроверки нечего добавляем - пропускаем
        if not fields_final and os.path.exists(per_path):
            if logger:
                logger.debug(f"  ⏭ Все теги уже в файле - пропускаем: {os.path.basename(per_path)}")
            continue

        # Обрабатываем только поля, нуждающиеся в переводе
        for item in fields_final:
            if len(item) == 3:
                field_path, eng_val, fuzzy_translation = item
            else:
                field_path, eng_val = item
                fuzzy_translation = None

            # Для JobDef.reportString tagname будет "CleanSelf.reportString"
            # Используем orig_def_name чтобы не было префикса типа
            tagname = f"{orig_def_name}.{field_path}"

            # 1. Проверяем, есть ли уже перевод в этом файле
            found = False
            for child in root:
                if child.tag == tagname and child.text and child.text.strip():
                    found = True
                    if logger:
                        logger.debug(f"Found existing translation in file for {tagname}")
                    break

            if found:
                continue

            # 2. Пытаемся найти ТОЧНЫЙ перевод в existing_map (НЕ ищем похожие!)
            final_val = existing_map.get(tagname)

            # 2.5. Если есть fuzzy перевод - используем его
            if not final_val and fuzzy_translation:
                final_val = fuzzy_translation
                if logger:
                    logger.info(f"  🔍 Использован fuzzy перевод для {tagname}")

            # 3. Если нет, ищем в Keyed/Source (ТОЧНОЕ совпадение)
            if not final_val:
                final_val = keyed_map.get(tagname) or source_map.get(tagname)

            # 4. Если включен API и перевода всё еще нет — переводим
            if not final_val and use_api:
                final_val = translator.translate(eng_val)
                if final_val and logger:
                    logger.info(f"Автоперевод [{tagname}]: {eng_val} -> {final_val}")

            # 5. Если совсем ничего не нашли, берем оригинал
            if not final_val:
                final_val = eng_val

            # Записываем в дерево и отмечаем модификацию
            # Проверяем, существует ли уже тег с переводом
            tag_exists_with_value = False
            for child in root:
                if child.tag == tagname:
                    if child.text and child.text.strip():
                        # Тег уже существует и не пустой - не модифицируем
                        tag_exists_with_value = True
                        if logger:
                            logger.debug(f"Тег уже существует с значением: {tagname}")
                    break

            if not tag_exists_with_value:
                add_or_preserve(root, tagname, final_val, logger)
                modified = True

        if modified:
            # === Проверка на дубликаты по содержимому ===
            new_content_hash = get_xml_content_hash(root)

            is_duplicate = False
            if new_content_hash in existing_content_hashes:
                existing_files = existing_content_hashes[new_content_hash]
                if per_path not in existing_files:
                    is_duplicate = True
                    if logger:
                        logger.warn(
                            f"Дубликат: файл {os.path.basename(per_path)} пропущен, т.к. содержимое идентично файлам: {[os.path.basename(f) for f in existing_files]}"
                        )

            if is_duplicate:
                continue

            tree = ET.ElementTree(root)
            if write_tree_pretty(tree, per_path, logger):
                created_files.append(per_path)
                if logger:
                    logger.info(f"Файл обновлен: {per_path}")
            elif logger:
                logger.error(f"Не удалось записать файл: {per_path}")
        elif logger:
            logger.debug(f"No modifications for {per_path}")

    # === Проверка устаревших тегов (после обновления мода) ===
    if check_obsolete:
        # Определяем путь к моду (поднимаемся на 3 уровня от DefInjected)
        # perdef_base = Languages/Russian/DefInjected
        # mod_path = Languages/../.. = корень мода
        mod_path = os.path.dirname(os.path.dirname(os.path.dirname(perdef_base)))
        process_obsolete_tags(perdef_base, defs_index, logger, mod_path)

    # Опциональная очистка осиротевших файлов
    if cleanup_orphans:
        orphans = _cleanup_orphan_translations(perdef_base, created_files, logger)
        if orphans:
            if logger:
                logger.info(
                    f"Найдено {len(orphans)} осиротевших файлов (не будут удалены автоматически):"
                )
                for o in orphans[:10]:
                    logger.info(f"  - {o}")

    # === ИТОГОВАЯ СВОДКА ===
    if logger:
        separator = "=" * 60
        logger.info(f"\n{separator}")
        logger.info("📊 СВОДКА ОБРАБОТКИ DEF INJECTED")
        logger.info(separator)
        logger.info(f"   Всего Defs: {len(defs_index)}")
        logger.info(f"   Обработано: {defs_processed}")
        logger.info(f"   Пропущено (уже есть перевод): {skipped_already_translated}")
        logger.info(f"   Файлов создано/обновлено: {len(created_files)}")

        if len(created_files) > 0:
            logger.info("\n   📄 Созданные/обновлённые файлы:")
            for f in created_files[:10]:  # Показываем первые 10
                rel = os.path.relpath(f, perdef_base)
                logger.info(f"      • {rel}")
            if len(created_files) > 10:
                logger.info(f"      ... и ещё {len(created_files) - 10} файлов")

        logger.info(separator)

    return created_files
