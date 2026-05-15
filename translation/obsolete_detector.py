# obsolete_detector.py
"""
Модуль для обнаружения и обработки устаревших тегов перевода.

После обновления мода некоторые теги могут быть удалены или переименованы.
Этот модуль находит такие теги в существующих DefInjected файлах и:
1. Закомментирует их (префикс _OBSOLETE_)
2. Добавит XML-комментарий с пояснением
3. Логирует подробную статистику и рекомендации
"""

import os
import lxml.etree as etree

from utils.mod_version import get_mod_name, get_mod_version
from verification.xml_parser import safe_parse_xml, write_tree_pretty


def _extract_def_name_from_index_key(key):
    """
    Извлекает имя Def из ключа индекса.

    Ключ имеет формат "TypeDef_DefName" (например, "AbilityDef_RK_PrayerService").
    Возвращает "DefName" (например, "RK_PrayerService").

    Args:
        key: Ключ из defs_index (формат "TypeDef_DefName")

    Returns:
        str: Имя Def (часть после первого подчёркивания)
    """
    if "_" in key:
        # Разделяем только по первому подчёркиванию
        # "AbilityDef_RK_PrayerService" -> "RK_PrayerService"
        parts = key.split("_", 1)
        return parts[1] if len(parts) > 1 else key
    return key


def _build_current_def_names(defs_index):
    """
    Строит множество актуальных имён Def из индекса.

    Args:
        defs_index: Словарь Defs {def_name: {field: value}}

    Returns:
        set: Множество имён Def
    """
    def_names = set()
    for key in defs_index.keys():
        def_name = _extract_def_name_from_index_key(key)
        def_names.add(def_name)
    return def_names


def find_obsolete_tags(perdef_base, defs_index, logger=None):
    """
    Находит устаревшие теги в DefInjected файлах.

    Сравнивает теги в существующих файлах DefInjected с актуальными Defs
    и возвращает список тегов которые есть в переводе но отсутствуют в Defs.

    Логика:
    1. Строит множество имён Def из defs_index
    2. Для каждого тега в DefInjected извлекает имя Def (до точки)
    3. Если имя Def отсутствует в актуальных - тег устарел

    Args:
        perdef_base: Путь к папке DefInjected
        defs_index: Словарь Defs {def_name: {field: value}}
        logger: Логгер

    Returns:
        dict: {filepath: [(tag_name, tag_value), ...]}
    """
    obsolete = {}

    if not os.path.exists(perdef_base):
        if logger:
            logger.warning(f"DefInjected папка не существует: {perdef_base}")
        return obsolete

    # Шаг 1: Строим множество актуальных Def-ов
    current_def_names = _build_current_def_names(defs_index)

    if logger:
        logger.info("ℹ Проверка устаревших тегов:")
        logger.info(f"   DefInjected папка: {perdef_base}")
        logger.info(f"   Defs в индексе: {len(defs_index)}")
        logger.info(f"   Актуальных Def-ов: {len(current_def_names)}")
        if defs_index:
            logger.info(f"   Примеры ключей defs_index: {list(defs_index.keys())[:5]}")
            logger.info(f"   Примеры имён Def: {list(current_def_names)[:5]}")

    # Шаг 2: Сканируем все DefInjected файлы
    files_checked = 0
    total_tags_in_files = 0

    for root_dir, _, files in os.walk(perdef_base):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root_dir, filename)
            files_checked += 1

            try:
                root = safe_parse_xml(filepath)
                if root is None:
                    continue

                file_obsolete = []
                for child in root:
                    # Пропускаем комментарии и нестандартные теги
                    if not isinstance(child.tag, str):
                        continue

                    # Пропускаем уже закомментированные
                    if child.tag.startswith("_OBSOLETE_"):
                        continue

                    total_tags_in_files += 1

                    # Извлекаем Def имя из тега
                    # Тег имеет формат "DefName.field.path" -> Def имя = "DefName"
                    tag_def_name = child.tag.split(".")[0]

                    # Проверяем наличие Def в актуальных Defs
                    if tag_def_name not in current_def_names:
                        # Дополнительная проверка: тег должен иметь текст
                        if child.text and child.text.strip():
                            file_obsolete.append((child.tag, child.text.strip()))
                            if logger and len(file_obsolete) <= 3:
                                logger.debug(
                                    f"   ▶ OBSOLETE: {child.tag} "
                                    f"(Def '{tag_def_name}' не найден в актуальных Def-ах)"
                                )

                if file_obsolete:
                    rel_path = os.path.relpath(filepath, perdef_base)
                    obsolete[rel_path] = file_obsolete
                    if logger:
                        logger.info(f"   ✜ {rel_path}: {len(file_obsolete)} устаревших тегов")

            except Exception as e:
                if logger:
                    logger.debug(f"Ошибка проверки {filepath}: {e}")

    # ИТОГОВАЯ ОТЧЁТНОСТЬ
    if logger:
        logger.info(f"   ▶ Проверено файлов: {files_checked}")
        logger.info(f"   ▶ Всего тегов в файлах: {total_tags_in_files}")
        logger.info(f"   ▶ Найдено устаревших: {sum(len(v) for v in obsolete.values())}")
        logger.info(f"   ▶ Файлов с устаревшими: {len(obsolete)}")

    return obsolete


def comment_obsolete_tags(perdef_base, obsolete_tags_map, logger=None):
    """
    Закомментирует устаревшие теги в DefInjected файлах.
    Создаёт бэкап перед изменением через централизованный менеджер.

    Изменяет XML:
    - Меняет тег <Tag> на <_OBSOLETE_Tag>
    - Добавляет XML-комментарий перед тегом

    Args:
        perdef_base: Путь к папке DefInjected
        obsolete_tags_map: dict {filepath: [(tag_name, tag_value), ...]}
        logger: Логгер

    Returns:
        int: Количество закомментированных тегов
    """
    from utils.backup_manager import get_backup_manager

    if not obsolete_tags_map:
        return 0

    # ИСПРАВЛЕНО: Используем централизованный менеджер бэкапов
    backup_manager = get_backup_manager()
    backup_dir = backup_manager.create_backup(perdef_base, logger=logger)

    if not backup_dir:
        if logger:
            logger.warning("Не удалось создать бэкап, продолжаем без него")

    commented_count = 0

    for rel_path, tags in obsolete_tags_map.items():
        filepath = os.path.join(perdef_base, rel_path)

        if not os.path.exists(filepath):
            continue

        try:
            root = safe_parse_xml(filepath)
            if root is None:
                continue
            modified_file = False

            # Создаём словарь для быстрого поиска
            tags_to_comment = {tag for tag, _ in tags}

            for child in list(root):
                if not isinstance(child.tag, str):
                    continue

                # Пропускаем уже закомментированные
                if child.tag.startswith("_OBSOLETE_"):
                    continue

                # Проверяем нужно ли комментировать
                if child.tag in tags_to_comment:
                    old_tag = child.tag
                    new_tag = f"_OBSOLETE_{old_tag}"

                    # Меняем имя тега
                    child.tag = new_tag

                    # Добавляем комментарий перед тегом
                    comment_text = f" Устаревший тег (удалён в новой версии мода): {old_tag} "
                    comment = etree.Comment(comment_text)

                    # Вставляем комментарий перед тегом
                    children = list(root)
                    index = children.index(child)
                    root.insert(index, comment)

                    commented_count += 1
                    modified_file = True

                    if logger:
                        logger.debug(f"  Закомментирован: {old_tag} → {new_tag}")

            if modified_file:
                if write_tree_pretty(root, filepath, logger):
                    if logger:
                        logger.info(f"  ✔ Закомментированы устаревшие теги: {rel_path}")

        except Exception as e:
            if logger:
                logger.error(f"Ошибка обработки {filepath}: {e}")

    return commented_count


def log_obsolete_report(obsolete_tags_map, commented_count, perdef_base, logger=None):
    """
    Логирует подробный отчёт об устаревших тегах.

    Args:
        obsolete_tags_map: dict {filepath: [(tag_name, tag_value), ...]}
        commented_count: Количество закомментированных тегов
        perdef_base: Путь к папке DefInjected
        logger: Логгер
    """
    if not logger or not obsolete_tags_map:
        return

    # Определяем информацию о моде
    mod_path = os.path.dirname(os.path.dirname(os.path.dirname(perdef_base)))
    mod_version = get_mod_version(mod_path)
    mod_name = get_mod_name(mod_path)

    logger.info(f"\n{'=' * 60}")
    logger.info(f"▶  ОБНАРУЖЕНО УСТАРЕВШИХ ТЕГОВ: {commented_count}")

    if mod_name or mod_version:
        if mod_name:
            logger.info(f"  Мод: {mod_name}")
        if mod_version:
            logger.info(f"  Версия: {mod_version}")

    logger.info(f"{'=' * 60}")
    logger.info("Эти теги есть в переводе, но удалены из новой версии мода:")

    for rel_path, tags in obsolete_tags_map.items():
        logger.info(f"\n  ✜ {rel_path}:")
        for tag, text in tags[:5]:  # Показываем первые 5
            display_text = text[:50] + "..." if len(text) > 50 else text
            logger.info(f"    • <{tag}>: {display_text}")
        if len(tags) > 5:
            logger.info(f"    ... и ещё {len(tags) - 5} тегов")

    logger.info("\nℹ Рекомендация:")
    logger.info("  - Теги закомментированы (префикс _OBSOLETE_)")
    logger.info("  - Вы можете удалить их вручную если уверены что они не нужны")
    logger.info("  - Или оставить на случай если мод снова добавит их обратно")

    if mod_version:
        logger.info("  - Теги были актуальны в предыдущей версии мода")

    logger.info(f"{'=' * 60}")


def process_obsolete_tags(perdef_base, defs_index, logger=None):
    """
    Полный цикл обработки устаревших тегов.

    1. Находит устаревшие теги
    2. Закомментирует их
    3. Логирует отчёт

    Args:
        perdef_base: Путь к папке DefInjected
        defs_index: Словарь Defs {def_name: {field: value}}
        logger: Логгер

    Returns:
        int: Количество закомментированных тегов
    """
    # Шаг 1: Поиск
    obsolete = find_obsolete_tags(perdef_base, defs_index, logger)

    if not obsolete:
        if logger:
            logger.debug("Устаревшие теги не обнаружены")
        return 0

    total_obsolete = sum(len(tags) for tags in obsolete.values())
    if logger:
        logger.info(f"Найдено {total_obsolete} устаревших тегов в {len(obsolete)} файлах")

    # Шаг 2: Комментирование
    commented = comment_obsolete_tags(perdef_base, obsolete, logger)

    # Шаг 3: Отчёт
    log_obsolete_report(obsolete, commented, perdef_base, logger)

    return commented
