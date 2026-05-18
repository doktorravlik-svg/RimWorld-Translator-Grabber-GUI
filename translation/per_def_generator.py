# per_def_generator.py
"""
Основная логика генерации DefInjected файлов.
Выделено из per_def.py для соблюдения лимита строк.
"""
import os
import re
from dataclasses import dataclass

from lxml import etree

# Регулярное выражение для проверки технических значений (координаты, числа)
VALUE_IS_TECHNICAL = re.compile(r'^[\d\s\(\)., \-]+$')

# Регулярное выражение для RulePackDef имен (Namer*, *Maker, *Def и т.п.)
# Это внутренние ссылки на игровые объекты, а не текст для перевода
# Примеры: NamerPerson_RatkinKingdom, LeaderTitleMaker_RatkinKingdom, NamerIdeo_RatkinKingdom
VALUE_IS_DEFNREF = re.compile(
    r'^(Namer\w*|Leader\w*|Festival\w*|Deity\w*|Ideo\w*|[A-Z][a-z]*Maker)_?\w*$'
)

# Import after regex definitions (E402 workaround - imports in middle of file are intentional)
from translation.matching import find_existing_translation
from translation.obsolete_detector import process_obsolete_tags
from translation.per_def_utils import (
    cleanup_orphan_translations,
    ensure_dir,
    scan_existing_translations,
)
from translation.translator import AutoTranslator
from verification.xml_parser import (
    add_or_update_translation,
    add_rulepack_with_li,
    get_xml_content_hash,
    safe_parse_xml,
    write_tree_pretty,
)


@dataclass
class GeneratorConfig:
    """Конфигурация генератора DefInjected файлов"""
    aggressive: bool = False
    use_api: bool = False
    lang_to: str = "Russian"
    cleanup_orphans: bool = False
    fuzzy: bool = False
    check_obsolete: bool = True
    existing_origin: dict | None = None
    engine_names: list[str] | None = None  # ✅ НОВОЕ: список движков перевода
    glossary_manager: "GlossaryManager | None" = None  # ✅ НОВОЕ: кэшированный glossary_manager


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
    config: GeneratorConfig | None = None,
    # Обратная совместимость - старые параметры
    aggressive=False,
    use_api=False,
    lang_to="Russian",
    cleanup_orphans=False,
    fuzzy=False,
    existing_origin=None,
    check_obsolete=True,
    engine_names=None,  # ✅ НОВОЕ: список движков перевода
    glossary_manager=None,  # ✅ НОВОЕ: кэшированный glossary_manager
):
    """
    Основная функция создания DefInjected файлов.

    ✅ Новый формат вызова:
    generate_or_update_per_def_files_v2(..., config=GeneratorConfig(fuzzy=True, use_api=True))

    ✅ Старый формат вызова тоже остаётся работать для обратной совместимости
    """
    # ✅ Если передан конфиг - используем его
    if config is None:
        config = GeneratorConfig(
            aggressive=aggressive,
            use_api=use_api,
            lang_to=lang_to,
            cleanup_orphans=cleanup_orphans,
            fuzzy=fuzzy,
            check_obsolete=check_obsolete,
            existing_origin=existing_origin,
            engine_names=engine_names,  # ✅ НОВОЕ: передаём список движков
            glossary_manager=glossary_manager,  # ✅ НОВОЕ: передаём кэшированный glossary_manager
        )

    # ✅ Теперь ВЕЗДЕ в коде используем только config.*
    aggressive = config.aggressive
    use_api = config.use_api
    lang_to = config.lang_to
    cleanup_orphans = config.cleanup_orphans
    fuzzy = config.fuzzy
    check_obsolete = config.check_obsolete
    existing_origin = config.existing_origin
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
    ensure_dir(perdef_base)

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
    translator = AutoTranslator(
        enabled=use_api,
        logger=logger,
        target_lang=lang_to,
        engine_names=config.engine_names,  # ✅ НОВОЕ: передаём список движков
        glossary_manager=config.glossary_manager,  # ✅ НОВОЕ: используем кэшированный glossary_manager
    )

    if not defs_index:
        if logger:
            logger.warn("Словарь Defs пуст. Нечего обрабатывать.")
        return created_files

    # Предварительное сканирование существующих переводов для быстрого поиска
    existing_tags_map = scan_existing_translations(perdef_base, logger)
    if logger and existing_tags_map:
        logger.info(f"Найдено {len(existing_tags_map)} существующих тегов перевода")

    # Счётчики для статистики
    skipped_already_translated = 0
    defs_processed = 0
    defs_with_changes = 0

    # Общий счётчик для прогресса
    total_defs = len(defs_index)
    defs_processed_count = 0

    # ✅ НОВОЕ: Группируем defs по выходному файлу
    # Это решает проблему тройной перезаписи - каждый файл записывается ОДИН раз
    file_to_defs = {}  # per_path -> [(def_name, fields, def_type, orig_def_name, relpath), ...]

    for def_name, fields in defs_index.items():
        defs_processed_count += 1
        defs_processed += 1

        # fields содержит {'reportString': 'cleaning self', 'label': '...'}
        # def_name теперь в формате "Тип_Имя" (например, "JobDef_CleanSelf")

        # Извлекаем оригинальное имя Def'а из составного ключа
        if "_" in def_name:
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

        # Определяем имя файла СРАЗУ
        orig_filename = os.path.basename(relpath)
        if not orig_filename:
            orig_filename = f"Generated_{orig_def_name}.xml"

        # Определяем папку (например, DefInjected/Ability)
        sub_dir = os.path.dirname(relpath)
        out_dir = os.path.join(perdef_base, sub_dir)

        # ПРОВЕРКА: Ищем существующую папку с похожим именем
        # Универсальная проверка для ЛЮБЫХ расхождений в названии папки (Def/Defs, plural, etc.)
        if not os.path.exists(out_dir) and os.path.exists(perdef_base):
            for existing_dir in os.listdir(perdef_base):
                existing_path = os.path.join(perdef_base, existing_dir)
                if not os.path.isdir(existing_path):
                    continue

                match_found = False

                if existing_dir.lower() == sub_dir.lower():
                    match_found = True
                elif existing_dir == sub_dir + "Def" or sub_dir == existing_dir + "Def":
                    match_found = True
                elif existing_dir.rstrip("s") == sub_dir.rstrip("s"):
                    match_found = True
                elif orig_filename and os.path.exists(os.path.join(existing_path, orig_filename)):
                    match_found = True
                    if logger:
                        logger.debug(f"  🔍 Найдено по имени файла: {existing_dir}/{orig_filename}")

                if match_found:
                    if logger:
                        logger.info(f"  Используем существующую папку: {existing_dir} (вместо {sub_dir})")
                    out_dir = existing_path
                    break

        per_path = os.path.join(out_dir, orig_filename)

        # ПРОВЕРКА: Если файл не существует, ищем в АЛЬТЕРНАТИВНЫХ папках
        if not os.path.exists(per_path) and os.path.exists(perdef_base):
            for existing_dir in os.listdir(perdef_base):
                existing_path_full = os.path.join(perdef_base, existing_dir, orig_filename)
                if os.path.exists(existing_path_full):
                    if os.path.normpath(os.path.dirname(existing_path_full)) != os.path.normpath(out_dir):
                        if logger:
                            logger.info(f"  Найден существующий файл: {os.path.relpath(existing_path_full, perdef_base)}")
                        out_dir = os.path.dirname(existing_path_full)
                        per_path = existing_path_full
                        break

        # ✅ Группируем по per_path
        if per_path not in file_to_defs:
            file_to_defs[per_path] = []
        file_to_defs[per_path].append((def_name, fields, def_type, orig_def_name, relpath))

    # === ВТОРОЙ ПРОХОД: обрабатываем файлы группами ===
    # Каждый файл записывается ТОЛЬКО ОДИН РАЗ
    for per_path, defs_list in file_to_defs.items():
        if logger:
            logger.debug(f"Processing file: {os.path.basename(per_path)} ({len(defs_list)} defs)")

        # Загружаем или создаём XML один раз
        if os.path.exists(per_path):
            try:
                root = safe_parse_xml(per_path)
                if root is None:
                    root = etree.Element("LanguageData")
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка чтения {per_path}: {e}")
                root = etree.Element("LanguageData")
        else:
            root = etree.Element("LanguageData")

        modified = False
        file_existing_tags = {}  # tagname -> value (from this file)

        # Сканируем существующие теги в файле
        for child in root:
            if isinstance(child.tag, str) and child.text and child.text.strip():
                tag = child.tag
                if tag.startswith("_OBSOLETE_"):
                    tag = tag[len("_OBSOLETE_"):]
                file_existing_tags[tag] = child.text.strip()

        # Обрабатываем ВСЕ defs для этого файла
        for def_name, fields, def_type, orig_def_name, relpath in defs_list:
            # === ПРОВЕРКА: Все ли поля уже переведены В КОНКРЕТНОМ ФАЙЛЕ? ===
            all_fields_translated = True
            fields_to_process = []

            for field_path, eng_val in fields.items():
                tagname = f"{orig_def_name}.{field_path}"

                # Пропускаем ссылки на Def/RulePack (Namer*, *Maker и т.п.)
                # Это внутренние ссылки на игровые объекты, а не текст для перевода
                # eng_val может быть списком для RulePackDef (field_path.endswith("._list"))
                if eng_val and isinstance(eng_val, str) and VALUE_IS_DEFNREF.match(eng_val):
                    if logger:
                        logger.debug(f"  Пропущена ссылка на Def {tagname}: '{eng_val}'")
                    continue

                # 1. Проверяем ТОЧНО в КОНКРЕТНОМ файле
                if tagname in file_existing_tags:
                    existing_val = file_existing_tags[tagname]
                    origin_for_tag = (existing_origin or {}).get(tagname, eng_val)
                    if existing_val.upper() == "TODO" or existing_val == origin_for_tag:
                        if logger:
                            logger.debug(f"  Невалидный перевод: {tagname} ('{existing_val[:40]}')")
                        all_fields_translated = False
                        fields_to_process.append((field_path, eng_val, None))
                    else:
                        if logger:
                            logger.debug(f"  Уже есть в файле: {tagname}")
                else:
                    # 2. Проверяем в existing_map (БД переводов)
                    if tagname in existing_map and existing_map[tagname].strip():
                        existing_val = existing_map.get(tagname)
                        origin_for_tag = (existing_origin or {}).get(tagname, eng_val)
                        if existing_val.upper() == "TODO" or existing_val == origin_for_tag:
                            all_fields_translated = False
                            fields_to_process.append((field_path, eng_val, None))
                        else:
                            # Проверяем что перевод именно из нашего файла
                            tag_file = existing_index.get(tagname, "")
                            if os.path.normpath(tag_file) == os.path.normpath(per_path):
                                if logger:
                                    logger.debug(f"  Найден точный перевод в этом файле: {tagname}")
                            else:
                                all_fields_translated = False
                                fields_to_process.append((field_path, eng_val, None))
                    # 3. Fuzzy поиск (только для не-_list полей)
                    elif fuzzy and not field_path.endswith("._list"):
                        fuzzy_val, fuzzy_path = find_existing_translation(
                            tagname, existing_map, existing_index, logger, fuzzy=True, original_text=eng_val,
                            target_language=lang_to
                        )
                        if fuzzy_val:
                            if logger:
                                logger.info(f"  Fuzzy: {tagname} → найден перевод ({fuzzy_path})")
                            all_fields_translated = False
                            fields_to_process.append((field_path, eng_val, fuzzy_val))
                        else:
                            all_fields_translated = False
                            fields_to_process.append((field_path, eng_val, None))
                    else:
                        all_fields_translated = False
                        fields_to_process.append((field_path, eng_val, None))

            # Если все поля уже есть в файле - пропускаем
            if all_fields_translated and fields:
                skipped_already_translated += 1
                if logger:
                    if skipped_already_translated <= 5 or skipped_already_translated % 10 == 0:
                        logger.debug(f"  Пропущен (все {len(fields)} полей уже в файле): {def_name}")
                continue

            # Обрабатываем поля
            for item in fields_to_process:
                if len(item) == 3:
                    field_path, eng_val, fuzzy_translation = item
                else:
                    field_path, eng_val = item
                    fuzzy_translation = None

                # Проверяем, это RulePackDef с списком <li>?
                if field_path.endswith("._list"):
                    # RulePackDef: field_path = "rulePack.rulesStrings._list"
                    tagname = f"{orig_def_name}.rulePack.rulesStrings"

                    # eng_val содержит список текстов
                    if isinstance(eng_val, list):
                        eng_list = eng_val
                    else:
                        eng_list = [eng_val]

                    # Переводим каждый текст в списке
                    translated_list = []
                    for text in eng_list:
                        if not text or not text.strip():
                            translated_list.append(text)
                            continue

                        # ✅ RulePackDef: переводим только часть ПОСЛЕ "->"
                        # Формат: "pattern->output" где pattern нельзя переводить
                        if "->" in text:
                            parts = text.split("->", 1)
                            pattern_part = parts[0]  # не переводим - это PATTERN!
                            output_part = parts[1] if len(parts) > 1 else ""

                            # Переводим только output_part
                            if output_part and output_part.strip():
                                if use_api:
                                    # ✅ НОВОЕ: Защищаем [variable] переменные в output_part
                                    # Сохраняем [syllable], [end] и т.д.
                                    import re
                                    rVariables = re.findall(r'\[[^\]]+\]', output_part)
                                    var_placeholder_map = {}
                                    temp_output = output_part
                                    for i, var in enumerate(rVariables):
                                        placeholder = f"__VAR_{i}__"
                                        var_placeholder_map[placeholder] = var
                                        temp_output = temp_output.replace(var, placeholder)

                                    # ✅ ВАЖНО: Передаём pattern_part как original_text
                                    # Это предотвращает применение глоссария к output_part
                                    # Глоссарий применяется к text, но мы хотим его применить к pattern_part
                                    # Поэтому передаём pattern_part, чтобы глоссарий обработал его
                                    # А output_part будет переведён "с нуля" API
                                    translated_output = translator.translate(temp_output, pattern_part)

                                    if translated_output:
                                        # ✅ Восстанавливаем переменные обратно (регистронезависимый поиск)
                                        for placeholder, var in var_placeholder_map.items():
                                            # Используем регулярное выражение для case-insensitive замены
                                            translated_output = re.sub(
                                                re.escape(placeholder), var, translated_output, flags=re.IGNORECASE
                                            )
                                        # ✅ pattern_part НИКОГДА не переводится!
                                        translated_list.append(f"{pattern_part}->{translated_output}")
                                    else:
                                        translated_list.append(text)
                                else:
                                    translated_list.append(text)
                            else:
                                translated_list.append(text)
                        else:
                            # Обычный текст без паттерна
                            if VALUE_IS_TECHNICAL.match(text):
                                translated_list.append(text)
                            else:
                                if use_api:
                                    translated = translator.translate(text, text)
                                    if translated:
                                        translated_list.append(translated)
                                    else:
                                        translated_list.append(text)
                                else:
                                    translated_list.append(text)

                    # Записываем как один тег с <li> детьми
                    add_rulepack_with_li(root, tagname, translated_list, logger)
                    modified = True
                    continue

                    # Проверяем, существует ли уже тег в root
                    tag_exists_in_root = False
                    for child in root:
                        if child.tag == tagname:
                            tag_exists_in_root = True
                            break

                    # Записываем как один тег с <li> детьми
                    add_rulepack_with_li(root, tagname, translated_list, logger)
                    modified = True
                    continue

                tagname = f"{orig_def_name}.{field_path}"

                # Определяем финальное значение
                final_val = None
                source_name = None

                if fuzzy_translation:
                    final_val = fuzzy_translation
                    source_name = "fuzzy поиск"
                elif existing_map.get(tagname):
                    final_val = existing_map.get(tagname)
                    source_name = "existing_map (БД переводов)"
                elif keyed_map.get(tagname):
                    final_val = keyed_map.get(tagname)
                    source_name = "Keyed файлы"
                elif source_map.get(tagname):
                    final_val = source_map.get(tagname)
                    source_name = "Source файлы мода"
                elif use_api:
                    # ✅ RulePackDef: обрабатываем формат "pattern->output"
                    # Для rulesStrings полей тоже нужно сохранять pattern_part
                    if isinstance(eng_val, str) and "->" in eng_val:
                        import re
                        parts = eng_val.split("->", 1)
                        pattern_part = parts[0]
                        output_part = parts[1] if len(parts) > 1 else ""

                        if output_part and output_part.strip():
                            # Защищаем [variable] переменные в output_part
                            rVariables = re.findall(r'\[[^\]]+\]', output_part)
                            var_placeholder_map = {}
                            temp_output = output_part
                            for i, var in enumerate(rVariables):
                                placeholder = f"__VAR_{i}__"
                                var_placeholder_map[placeholder] = var
                                temp_output = temp_output.replace(var, placeholder)

                            # Передаем pattern_part как original_text для глоссария
                            translated_output = translator.translate(temp_output, pattern_part)

                            if translated_output:
                                # Восстанавливаем переменные (регистронезависимый поиск)
                                for placeholder, var in var_placeholder_map.items():
                                    # Используем регулярное выражение для case-insensitive замены
                                    translated_output = re.sub(
                                        re.escape(placeholder), var, translated_output, flags=re.IGNORECASE
                                    )
                                # pattern_part НИКОГДА не переводится!
                                final_val = f"{pattern_part}->{translated_output}"
                            else:
                                final_val = eng_val
                        else:
                            final_val = eng_val
                    else:
                        final_val = translator.translate(eng_val, eng_val)

                    source_name = "Автоперевод API"
                    if final_val and logger:
                        logger.info(f"  🤖 Автоперевод: [{tagname}] '{eng_val}' -> '{final_val}'")
                else:
                    final_val = eng_val
                    source_name = "оригинал (перевод не найден)"

                # Пропускаем технические значения
                if eng_val and isinstance(eng_val, str) and VALUE_IS_TECHNICAL.match(eng_val):
                    if logger:
                        logger.debug(f"  Пропущен технический тег {tagname}: '{eng_val}'")
                    continue

                # Пропускаем ссылки на Def/RulePack (Namer*, *Maker и т.п.)
                # Это внутренние ссылки на игровые объекты, а не текст для перевода
                if eng_val and isinstance(eng_val, str) and VALUE_IS_DEFNREF.match(eng_val):
                    if logger:
                        logger.debug(f"  Пропущена ссылка на Def/RulePack {tagname}: '{eng_val}'")
                    continue

                # Проверяем, существует ли уже тег с переводом
                tag_exists_with_value = False
                for child in root:
                    if child.tag == tagname:
                        if child.text and child.text.strip():
                            tag_exists_with_value = True
                            if logger:
                                logger.debug(f"Тег уже существует с значением: {tagname}")
                        break

                if not tag_exists_with_value:
                    add_or_update_translation(root, tagname, eng_val, final_val, logger)
                    modified = True

        # Записываем файл ОДИН РАЗ после обработки всех defs
        if modified:
            # Проверка на дубликаты по содержимому
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

            if not is_duplicate:
                if write_tree_pretty(root, per_path, logger):
                    created_files.append(per_path)
                    if logger:
                        logger.info(f"Файл обновлён: {per_path}")
            else:
                if logger:
                    logger.debug(f"No modifications for {per_path}")
        else:
            if logger:
                logger.debug(f"No modifications for {per_path}")

    # === Проверка устаревших тегов (после обновления мода) ===
    if check_obsolete:
        process_obsolete_tags(perdef_base, defs_index, logger)

    # Опциональная очистка осиротевших файлов
    if cleanup_orphans:
        orphans = cleanup_orphan_translations(perdef_base, created_files, logger)
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
        logger.info("СВОДКА ОБРАБОТКИ DEF INJECTED")
        logger.info(separator)
        logger.info(f"   Всего Defs: {len(defs_index)}")
        logger.info(f"   Обработано: {defs_processed}")
        logger.info(f"   Пропущено (уже есть перевод): {skipped_already_translated}")
        logger.info(f"   Файлов создано/обновлён: {len(created_files)}")

        if len(created_files) > 0:
            logger.info("\n   Созданные/обновлённые файлы:")
            for f in created_files[:10]:  # Показываем первые 10
                rel = os.path.relpath(f, perdef_base)
                logger.info(f"      • {rel}")
            if len(created_files) > 10:
                logger.info(f"      ... и ещё {len(created_files) - 10} файлов")

    return created_files
