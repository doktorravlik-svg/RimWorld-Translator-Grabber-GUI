# main.py
import os
import shutil
import sys
import time

from collectors.collectors import (
    collect_defs_with_meta,
    collect_english_source,
    collect_existing_translations,
    collect_keyed_entities,
)
from core.logger import Logger
from duplicates.duplicate_merger import find_duplicates

# Инициализация loguru
from utils.loguru_setup import setup_logging

setup_logging(debug_mode=False)

# Импорты из новых разбитых файлов
from scanner.mod_scanner import analyze_languages
from translation.keyed_merge import write_keyed_files_mirror_with_merge
from translation.per_def import generate_or_update_per_def_files_v2
from translation.translation_utils import (
    compare_translations,
    import_translations_from_csv,
    import_translations_from_json,
    resolve_conflicts,
)
from utils.cli_helpers import create_backup, display_language_table, prompt_yes_no
from utils.languages_path_resolver import (
    create_source_language_structure as ensure_languages_folder,
    find_all_language_folders,
    prioritize_language_folders,
)
from utils.path_utils import ensure_project_root_in_path

# Обеспечиваем корректный путь к корню проекта
ensure_project_root_in_path()


def safe_copy(src, dst, max_retries=15):
    """Безопасное копирование файла с повторными попытками."""
    for attempt in range(max_retries):
        try:
            with open(src, 'rb') as f:
                content = f.read()
            with open(dst, 'wb') as f:
                f.write(content)
            return
        except OSError as e:
            if getattr(e, 'winerror', None) == 32 and attempt < max_retries - 1:
                delay = 0.5 * (2 ** attempt)
                time.sleep(min(delay, 10))
            else:
                raise


def main_process(mod_path, logger, interactive=True, backup=True):
    """
    Основной процесс анализа и перевода мода RimWorld.
    
    Выполняет полный цикл перевода:
    1. Анализ структуры мода и доступных языков
    2. Сравнение существующих переводов с оригиналом
    3. Импорт переводов из CSV/JSON файлов (опционально)
    4. Создание резервной копии
    """
    mod_name = os.path.basename(mod_path)
    logger.info(f"Анализ мода: {mod_name}")

    # === Анализ языков ===
    logger.info("[1/5] Анализ структуры и языков...")
    langs_base = os.path.join(mod_path, "Languages")
    languages = analyze_languages(mod_path, logger=logger)
    
    if not languages:
        logger.error("Не найдено папок с языками")
        return
    
    display_language_table(languages)
    
    source_lang = "English"
    target_lang = "Russian"
    
    if interactive:
        print(f"\nИсходный язык: {source_lang}")
        display_language_table(languages)
        if len(languages) > 1:
            print("\nВыбери язык-источник:")
            for i, lang in enumerate(sorted(languages.keys())):
                print(f"  {i + 1}. {lang}")
            try:
                choice = int(input("Номер: ").strip()) - 1
                source_lang = sorted(languages.keys())[choice]
            except (ValueError, IndexError):
                pass
        
        target_lang = (
            input("\nЯзык перевода (по умолчанию Russian): ").strip() if interactive else "Russian"
        )
        if not target_lang:
            target_lang = "Russian"
    
    # === Сравнение переводов ===
    logger.info(f"[3/5] Сравнение переводов ({source_lang} -> {target_lang})...")
    source_lang_dir = os.path.join(langs_base, source_lang)
    target_lang_dir = os.path.join(langs_base, target_lang)
    
    # Копируем Strings (если есть) из исходного языка в целевой
    source_strings = os.path.join(source_lang_dir, "Strings")
    if os.path.isdir(source_strings):
        target_strings = os.path.join(target_lang_dir, "Strings")
        if not os.path.exists(target_strings):
            os.makedirs(target_strings, exist_ok=True)
        for fname in os.listdir(source_strings):
            s = os.path.join(source_strings, fname)
            t = os.path.join(target_strings, fname)
            if os.path.isfile(s) and not os.path.exists(t):
                try:
                    safe_copy(s, t)
                except Exception as e:
                    print(f"Не удалось скопировать Strings/{fname}: {e}")
    
    source_map = collect_english_source(source_lang_dir, logger=logger) or {}
    existing_map, existing_index = (
        collect_existing_translations(target_lang_dir, logger=logger)
        if os.path.exists(target_lang_dir)
        else ({}, {})
    )
    
    stats = compare_translations(source_map, existing_map, logger)
    logger.info(
        f"Статистика перевода:\n"
        f"  Всего ключей в исходном: {stats['total_source']}\n"
        f"  Уже переведено: {stats['translated']}\n"
        f"  Отсутствует: {stats['missing']}\n"
        f"  Готовность: {stats['percent']:.1f}%"
    )
    
    duplicates = find_duplicates(existing_map, logger)
    if duplicates:
        logger.warning(f"Найдено {len(duplicates)} конфликтов дубликатов!")
        if prompt_yes_no("Разрешить конфликты?", default="y", interactive=interactive):
            existing_map, resolved = resolve_conflicts(
                duplicates, existing_map, logger, interactive=interactive
            )
            if resolved:
                logger.info(f"Разрешено {len(resolved)} конфликтов")
    
    # === Импорт переводов из файлов ===
    if interactive:
        csv_path = input("\nПуть к CSV файлу переводов (пусто для пропуска): ").strip()
        if csv_path and os.path.exists(csv_path):
            count = import_translations_from_csv(csv_path, existing_map, logger)
            logger.info(f"Импортировано {count} переводов из CSV")
        
        json_path = input("Путь к JSON файлу переводов (пусто для пропуска): ").strip()
        if json_path and os.path.exists(json_path):
            count = import_translations_from_json(json_path, existing_map, logger)
            logger.info(f"Импортировано {count} переводов из JSON")
    
    # === Создание резервной копии ===
    if backup and prompt_yes_no("\nСоздать резервную копию?", default="y", interactive=interactive):
        backup_path = create_backup(mod_path, logger=logger)
        if backup_path:
            logger.info(f"Резервная копия создана: {backup_path}")
    
    # === Генерация DefInjected файлов ===
    logger.info("[5/5] Генерация DefInjected файлов...")
    defs_folders = []  # TODO: собрать папки Defs
    if defs_folders:
        generate_or_update_per_def_files_v2(
            defs_folders=defs_folders,
            output_folder=mod_path,
            target_lang=target_lang,
            logger=logger,
        )
    
    logger.info("=== Процесс завершен ===")


if __name__ == "__main__":
    mods_folder = sys.argv[1] if len(sys.argv) > 1 else "."
    logger = Logger("main")
    main_process(mods_folder, logger, interactive=True)
