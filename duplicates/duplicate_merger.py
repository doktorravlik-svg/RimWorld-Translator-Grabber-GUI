# duplicate_merger.py - Утилита для обнаружения и слияния дубликатов переводов
import os
import shutil
import tempfile
import lxml.etree as etree
from verification.xml_parser import safe_parse_xml
from collections import defaultdict


def _collect_languages_folders(mods_folder: str, logger=None) -> list[str]:
    """
    Собирает все папки Languages/Russian (и других языков) из модов.
    """
    languages_folders = []

    if not os.path.exists(mods_folder):
        return languages_folders

    # Проверяем это папка с модами или конкретный мод
    about_path = os.path.join(mods_folder, "About", "About.xml")
    if os.path.exists(about_path):
        # Это конкретный мод
        langs_path = os.path.join(mods_folder, "Languages")
        if os.path.exists(langs_path):
            for lang in os.listdir(langs_path):
                lang_path = os.path.join(langs_path, lang)
                if os.path.isdir(lang_path):
                    languages_folders.append(lang_path)

        for version in ["1.6", "1.5", "1.4", "1.3", "Common"]:
            v_langs = os.path.join(mods_folder, version, "Languages")
            if os.path.exists(v_langs):
                for lang in os.listdir(v_langs):
                    lang_path = os.path.join(v_langs, lang)
                    if os.path.isdir(lang_path):
                        languages_folders.append(lang_path)
    else:
        # Это папка с множеством модов
        for item in os.listdir(mods_folder):
            mod_path = os.path.join(mods_folder, item)
            if not os.path.isdir(mod_path):
                continue

            langs_path = os.path.join(mod_path, "Languages")
            if not os.path.exists(langs_path):
                continue

            for lang in os.listdir(langs_path):
                lang_path = os.path.join(langs_path, lang)
                if os.path.isdir(lang_path):
                    languages_folders.append(lang_path)

            for version in ["1.6", "1.5", "1.4", "1.3", "Common"]:
                v_langs = os.path.join(mod_path, version, "Languages")
                if os.path.exists(v_langs):
                    for lang in os.listdir(v_langs):
                        lang_path = os.path.join(v_langs, lang)
                        if os.path.isdir(lang_path):
                            languages_folders.append(lang_path)

    return languages_folders


def _copy_languages_folders(folders: list[str], target_dir: str, create_backup: bool, logger=None):
    """Копирует только Languages папки во временную директорию."""
    backups_created = 0

    for lang_folder in folders:
        parts = lang_folder.replace("\\", "/").split("/")
        if len(parts) < 3:
            continue

        lang_name = parts[-1]
        mod_name = parts[-3] if len(parts) >= 3 else "Unknown"

        target_lang_folder = os.path.join(target_dir, mod_name, "Languages", lang_name)
        os.makedirs(target_lang_folder, exist_ok=True)

        try:
            for item in os.listdir(lang_folder):
                src = os.path.join(lang_folder, item)
                dst = os.path.join(target_lang_folder, item)

                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
        except Exception as e:
            if logger:
                logger.warning(f"Ошибка копирования {lang_folder}: {e}")

    if logger and backups_created > 0:
        logger.info(f"Создано {backups_created} резервных копий")


def _copy_merged_back(
    temp_dir: str,
    mods_folder: str,
    output_folder: str = None,
    create_backup: bool = True,
    logger=None,
):
    """Копирует результаты слияния из временной папки обратно в оригинальные моды."""
    if not os.path.exists(temp_dir):
        return

    target_base = output_folder if output_folder else mods_folder

    for mod_name in os.listdir(temp_dir):
        mod_temp_path = os.path.join(temp_dir, mod_name)
        if not os.path.isdir(mod_temp_path):
            continue

        about_path = os.path.join(mods_folder, "About", "About.xml")
        if os.path.exists(about_path):
            mod_original_path = mods_folder
        else:
            mod_original_path = os.path.join(mods_folder, mod_name)
            if not os.path.exists(mod_original_path):
                if logger:
                    logger.warning(f"Оригинальный мод не найден: {mod_original_path}")
                continue

        temp_langs = os.path.join(mod_temp_path, "Languages")
        if not os.path.exists(temp_langs):
            continue

        original_langs = os.path.join(mod_original_path, "Languages")

        if create_backup and os.path.exists(original_langs):
            try:
                from utils.backup_manager import get_backup_manager

                backup_manager = get_backup_manager()
                backup_manager.create_backup(original_langs, logger=logger)
            except Exception as e:
                if logger:
                    logger.warning(f"Не удалось создать бекап: {e}")

        for lang in os.listdir(temp_langs):
            temp_lang_path = os.path.join(temp_langs, lang)
            if not os.path.isdir(temp_lang_path):
                continue

            original_lang_path = os.path.join(original_langs, lang)

            try:
                os.makedirs(original_lang_path, exist_ok=True)

                for item in os.listdir(temp_lang_path):
                    src = os.path.join(temp_lang_path, item)
                    dst = os.path.join(original_lang_path, item)

                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)

                if logger:
                    logger.info(f"✅ Скопировано: {mod_name}/{lang}")
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка копирования {mod_name}/{lang}: {e}")


def scan_translations(directory: str, logger=None, mod_path=None) -> dict[str, list[dict]]:
    """Сканирует директорию и собирает информацию о всех переводах."""
    translations = defaultdict(list)

    if not os.path.exists(directory):
        if logger:
            logger.warn(f"Директория не существует: {directory}")
        return translations

    lang_name = os.path.basename(os.path.normpath(directory))

    for root, dirs, files in os.walk(directory):
        # Исключаем бекап папки
        dirs[:] = [d for d in dirs if "_backup_" not in d and "obsolete" not in d.lower()]

        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root, filename)
            try:
                xml_root = safe_parse_xml(filepath)
                if xml_root is None:
                    continue

                for child in xml_root:
                    tag = child.tag
                    text = child.text or ""

                    translations[tag].append(
                        {
                            "file": filepath,
                            "filename": filename,
                            "value": text.strip() if text else "",
                            "rel_path": os.path.relpath(filepath, directory),
                            "mod_path": mod_path or directory,
                            "lang": lang_name,
                        }
                    )
            except Exception as e:
                if logger:
                    logger.error(f"Ошибка чтения {filepath}: {e}")

    return translations


def find_duplicates(
    translations: dict[str, list[dict]], case_sensitive: bool = True
) -> dict[str, list[dict]]:
    """Находит дубликаты - одинаковые теги в разных файлах с одинаковым значением."""
    duplicates = {}

    for tag, entries in translations.items():
        if len(entries) <= 1:
            continue

        files_with_tag = set(e["filename"] for e in entries)
        if len(files_with_tag) <= 1:
            continue

        value_groups = defaultdict(list)
        for entry in entries:
            value = entry["value"] if case_sensitive else entry["value"].lower()
            value_groups[value].append(entry)

        for value, group in value_groups.items():
            group_files = set(e["filename"] for e in group)
            if len(group_files) > 1 and len(group) > 1:
                if tag not in duplicates:
                    duplicates[tag] = []
                duplicates[tag].extend(group)

    return duplicates


def find_conflicts(translations: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Находит конфликты - одинаковые ключи с РАЗНЫМИ значениями."""
    conflicts = {}

    for tag, entries in translations.items():
        if len(entries) <= 1:
            continue

        files_with_tag = set(e["filename"] for e in entries)
        if len(files_with_tag) <= 1:
            continue

        values = set(e["value"].lower() for e in entries)
        if len(values) > 1:
            conflicts[tag] = entries

    return conflicts


def merge_duplicates(
    duplicates: dict, directory: str, keep: str = "first", logger=None
) -> tuple[int, int]:
    """Сливает дубликаты, удаляя лишние файлы."""
    files_deleted = 0
    keys_merged = 0

    for tag, entries in duplicates.items():
        if keep == "first":
            keep_entry = entries[0]
        elif keep == "last":
            keep_entry = entries[-1]
        elif keep == "longest":
            keep_entry = max(entries, key=lambda e: len(e["value"]))
        else:
            keep_entry = entries[0]

        for entry in entries:
            if entry["file"] == keep_entry["file"]:
                continue

            try:
                root = safe_parse_xml(entry["file"])
                if root is None:
                    continue

                found = False
                for child in root:
                    if child.tag == tag:
                        root.remove(child)
                        found = True
                        keys_merged += 1
                        if logger:
                            logger.debug(f"Удалён дубликат {tag} из {entry['filename']}")
                        break

                if len(root) == 0 or all(c.text is None or not c.text.strip() for c in root):
                    os.remove(entry["file"])
                    files_deleted += 1
                    if logger:
                        logger.info(f"Удалён пустой файл: {entry['file']}")
                else:
                    tree = etree.Element("root")
                    tree.write(entry["file"], encoding="utf-8", xml_declaration=True)

            except Exception as e:
                if logger:
                    logger.error(f"Ошибка обработки {entry['file']}: {e}")

    return files_deleted, keys_merged


def run_duplicate_merger(
    directory: str = None,
    keep: str = "first",
    case_sensitive: bool = True,
    logger=None,
    mods_folder: str = None,
    output_folder: str = None,
    auto_merge: bool = True,
    create_backup: bool = True,
    log_callback=None,
) -> dict:
    """Основная функция - запускает анализ и слияние дубликатов."""
    if log_callback and not logger:

        class CallbackLogger:
            def __init__(self, cb):
                self.cb = cb

            def info(self, msg):
                self.cb(msg)

            def debug(self, msg):
                self.cb(f"DEBUG: {msg}")

            def warn(self, msg):
                self.cb(f"WARNING: {msg}")

            def warning(self, msg):
                self.cb(f"WARNING: {msg}")

            def error(self, msg):
                self.cb(f"ERROR: {msg}")

        logger = CallbackLogger(log_callback)

    temp_dir = None

    if directory is None and mods_folder:
        if logger:
            logger.info(f"Сканирование папки модов: {mods_folder}")

        languages_folders = _collect_languages_folders(mods_folder, logger)

        if not languages_folders:
            if logger:
                logger.warning("Папки Languages не найдены в модах")
            return {
                "files_processed": 0,
                "duplicates_found": 0,
                "duplicates_merged": 0,
                "backups_created": 0,
                "errors": ["Папки Languages не найдены"],
                "warnings": [],
            }

        if logger:
            logger.info(f"Найдено {len(languages_folders)} папок Languages")

        temp_dir = tempfile.mkdtemp(prefix="rimworld_dup_merge_")
        _copy_languages_folders(languages_folders, temp_dir, create_backup, logger)
        directory = temp_dir

    if output_folder and directory and output_folder != directory:
        if logger:
            logger.info(f"Результаты будут скопированы в: {output_folder}")

    if directory is None:
        if logger:
            logger.error("Не указана папка для анализа")
        return None

    results = {
        "total_tags": 0,
        "duplicate_keys": 0,
        "conflict_keys": 0,
        "files_deleted": 0,
        "keys_merged": 0,
        "duplicates_detail": {},
        "conflicts_detail": {},
    }

    if logger:
        logger.info(f"Сканирование директории: {directory}")

    translations = scan_translations(directory, logger)
    results["total_tags"] = len(translations)

    if logger:
        logger.info(f"Найдено {results['total_tags']} уникальных тегов")

    duplicates = find_duplicates(translations, case_sensitive)
    results["duplicate_keys"] = len(duplicates)
    results["duplicates_detail"] = duplicates

    if logger:
        logger.info(f"Найдено {results['duplicate_keys']} ключей с дубликатами")

    conflicts = find_conflicts(translations)
    results["conflict_keys"] = len(conflicts)
    results["conflicts_detail"] = conflicts

    if logger:
        logger.info(f"Найдено {results['conflict_keys']} конфликтных ключей")

    files_deleted, keys_merged = merge_duplicates(duplicates, directory, keep, logger)
    results["files_deleted"] = files_deleted
    results["keys_merged"] = keys_merged

    if logger:
        logger.info(f"Удалено файлов: {files_deleted}, обработано ключей: {keys_merged}")

    # Копируем результаты обратно в оригинальные папки модов
    if mods_folder and os.path.exists(mods_folder) and temp_dir:
        if logger:
            logger.info("Копирование результатов обратно в моды...")
        _copy_merged_back(temp_dir, mods_folder, output_folder, create_backup, logger)

    return results
