# main.py
import os
import sys

from collectors.collectors import (
    collect_defs_with_meta,
    collect_english_source,
    collect_existing_translations,
    collect_keyed_entities,
)
from core.logger import Logger
from duplicates.duplicate_merger import find_duplicates

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
)
from utils.path_utils import ensure_project_root_in_path

# Обеспечиваем корректный путь к корню проекта
ensure_project_root_in_path()


def main_process(mod_path, logger, interactive=True, backup=True):
    """
    Основной процесс анализа и перевода мода RimWorld.

    Выполняет полный цикл перевода:
    1. Анализ структуры мода и доступных языков
    2. Сравнение существующих переводов с оригиналом
    3. Импорт переводов из CSV/JSON файлов (опционально)
    4. Создание резервной копии
    5. Генерация обновленных файлов переводов

    Args:
        mod_path: Путь к папке мода RimWorld
        logger: Экземпляр логгера для записи событий
        interactive: Режим интерактивности (запрос параметров у пользователя)
        backup: Создавать ли резервную копию существующих переводов

    Returns:
        None
    """
    if not os.path.exists(mod_path):
        print(f"Ошибка: Путь {mod_path} не существует.")
        return

    defs_dir = os.path.join(mod_path, "Defs")
    langs_base = os.path.join(mod_path, "Languages")

    if not os.path.exists(defs_dir):
        for v in ["1.6", "1.5", "1.4", "1.3"]:
            defs_dir = os.path.join(mod_path, v, "Defs")
            langs_base = os.path.join(mod_path, v, "Languages")
            if os.path.exists(defs_dir):
                print(f"Определена версия: {v}")
                break

    if not os.path.exists(defs_dir):
        print("Ошибка: Папка Defs не найдена")
        return

    # Проверяем и создаём папку Languages, если она не существует
    created_langs = ensure_languages_folder(mod_path, create_source_lang="English")
    if created_langs:
        # Обновляем langs_base на актуальный путь
        langs_base = created_langs
        print(f"✓ Папка Languages: {langs_base}")

    # === Анализ языков ===
    print("\n[2/5] Анализ языков...")
    languages = analyze_languages(langs_base, logger)
    source_lang = (
        "English"
        if "English" in languages
        else (list(languages.keys())[0] if languages else "English")
    )

    print(f"\nИсходный язык: {source_lang}")
    display_language_table(languages)

    if len(languages) > 1 and interactive:
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
    print(f"\n[3/5] Сравнение переводов ({source_lang} -> {target_lang})...")
    source_lang_dir = os.path.join(langs_base, source_lang)
    target_lang_dir = os.path.join(langs_base, target_lang)

    source_map = collect_english_source(source_lang_dir, logger=logger) or {}
    existing_map, existing_index = (
        collect_existing_translations(target_lang_dir, logger=logger)
        if os.path.exists(target_lang_dir)
        else ({}, {})
    )

    stats = compare_translations(source_map, existing_map, logger)
    print(
        f"\nСтатистика перевода:\n  Всего ключей в исходном: {stats['total_source']}\n  Уже переведено: {stats['translated']}\n  Отсутствует: {stats['missing']}\n  Готовность: {stats['percent']:.1f}%"
    )

    duplicates = find_duplicates(existing_map, logger)
    if duplicates:
        print(f"\nВНИМАНИЕ: Найдено {len(duplicates)} конфликтов дубликатов!")
        if prompt_yes_no("Разрешить конфликты?", default="y", interactive=interactive):
            existing_map, resolved = resolve_conflicts(
                duplicates, existing_map, logger, interactive=interactive
            )
            print(f"Разрешено конфликтов: {resolved}")

    # === Импорт из файла ===
    import_path = (
        input("Путь к файлу: ").strip()
        if interactive
        and prompt_yes_no("\nИмпортировать переводы из файла (CSV/JSON)?", default="n")
        else None
    )
    if import_path and os.path.exists(import_path):
        imported = (
            import_translations_from_csv(import_path, logger)
            if import_path.lower().endswith(".csv")
            else (
                import_translations_from_json(import_path, logger)
                if import_path.lower().endswith(".json")
                else {}
            )
        )
        existing_map.update({k: v for k, v in imported.items() if k not in existing_map})
        print(f"Импортировано новых ключей: {len(imported)}")

    # === Настройки и Выполнение ===
    use_api = prompt_yes_no(
        "Использовать API для автоперевода?", default="n", interactive=interactive
    )
    aggressive = prompt_yes_no(
        "Агрессивный поиск (все подряд)?", default="n", interactive=interactive
    )

    # Собираем данные для проверки изменений
    print("\n[4/5] Проверка необходимости перевода...")
    keyed_entities = collect_keyed_entities(source_lang_dir, logger=logger)
    defs_index, defs_rel, _, _, defs_meta = collect_defs_with_meta(defs_dir, logger=logger)

    # Подсчитываем сколько ключей нуждается в обработке
    existing_keys = set(existing_map.keys())
    source_keys = set(source_map.keys())
    defs_keys = set()

    for def_name, fields in defs_index.items():
        if "_" in def_name:
            orig_def_name = def_name.split("_", 1)[1]
        else:
            orig_def_name = def_name

        for field_path in fields.keys():
            tagname = f"{orig_def_name}.{field_path}"
            defs_keys.add(tagname)

    # Собираем все Keyed ключи
    keyed_keys = set()
    for files in (keyed_entities or {}).values():
        for kv in files.values():
            keyed_keys.update(kv.keys())

    # Проверяем сколько ключей уже переведено
    defs_missing = defs_keys - existing_keys
    keyed_missing = keyed_keys - existing_keys
    total_missing = len(defs_missing) + len(keyed_missing)

    print(f"  Ключей в Defs: {len(defs_keys)}")
    print(f"  Ключей в Keyed: {len(keyed_entities or {})}")
    print(f"  Нуждаются в переводе: {total_missing}")

    # Создаём бекап ТОЛЬКО если есть изменения
    if backup and os.path.exists(langs_base) and total_missing > 0:
        print("\n  Создание бэкапа...")
        create_backup(langs_base, logger)
    elif total_missing == 0:
        print("\n  ✓ Все переводы уже существуют - бэкап не нужен")

    print("\n[5/5] Обработка переводов...")

    keyed_map = {
        k: v
        for files in (keyed_entities or {}).values()
        for kv in files.values()
        for k, v in kv.items()
    }

    print("  Обработка Keyed...")
    created_keyed = write_keyed_files_mirror_with_merge(
        keyed_entities,
        target_lang_dir,
        existing_map,
        existing_index,
        source_map,
        logger=logger,
        aggressive=aggressive,
    )
    print("  Обработка DefInjected...")
    created_per_def = generate_or_update_per_def_files_v2(
        defs_index,
        defs_rel,
        {},
        {},
        defs_meta,
        keyed_map,
        source_map,
        existing_map,
        existing_index,
        target_lang_dir,
        logger=logger,
        aggressive=aggressive,
        use_api=use_api,
        lang_to=target_lang,
    )

    print(
        "\n"
        + "=" * 60
        + f"\n  Готово!\n  Обновлено Keyed: {len(created_keyed)}\n  Обновлено DefInjected: {len(created_per_def)}\n"
        + "=" * 60
    )


if __name__ == "__main__":
    try:
        main_process(sys.argv[1] if len(sys.argv) > 1 else ".", Logger())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback

        traceback.print_exc()
    input("\nНажмите Enter, чтобы выйти...")
