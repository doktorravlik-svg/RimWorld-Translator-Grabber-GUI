# utils/languages_path_resolver.py
"""
Единый модуль для определения путей к папке Languages.

Решает проблему дублирования: ВСЕГДЬ возвращает один и тот же путь
для одного и того же мода, независимо от того, откуда вызывается.

Приоритет определения пути:
1. Корневая Languages/{lang} (если существует)
2. Версионная Languages/{lang} (1.6, 1.5, и т.д.)
3. По умолчанию: корневая Languages/{lang}
"""

import os

from utils.loadfolders_parser import (
    find_all_defs_folders_with_loadfolders,
    find_all_languages_folders_with_loadfolders,
)

# Поддерживаемые версии RimWorld (в порядке приоритета)
SUPPORTED_VERSIONS = ["1.6", "1.5", "1.4", "1.3"]


def find_all_defs_folders(mod_path: str) -> list[str]:
    """
    Находит все папки Defs в моде с учётом LoadFolders.xml.

    Поддерживает:
    - Корневая Defs/
    - Версионная 1.6/Defs, 1.5/Defs и т.д.
    - Common/Defs (через LoadFolders.xml)
    - LoadFolders.xml

    Args:
        mod_path: Путь к моду

    Returns:
        Список путей к папкам Defs
    """
    return find_all_defs_folders_with_loadfolders(mod_path)


def find_all_languages_folders(mod_path: str) -> list[str]:
    """
    Находит все папки Languages в моде с учётом LoadFolders.xml.

    Поддерживает:
    - Корневая Languages/
    - Common/Languages
    - LoadFolders.xml

    Args:
        mod_path: Путь к моду

    Returns:
        Список путей к папкам Languages
    """
    return find_all_languages_folders_with_loadfolders(mod_path)


def has_root_languages_folder(mod_path: str, lang: str = None) -> bool:
    """
    Проверяет наличие корневой папки Languages/{lang} в моде.

    Args:
        mod_path: Путь к папке мода
        lang: Язык для проверки (None = проверить наличие любой Languages)

    Returns:
        True если существует корневая папка Languages
    """
    if lang:
        return os.path.exists(os.path.join(mod_path, "Languages", lang))
    else:
        return os.path.exists(os.path.join(mod_path, "Languages"))


def detect_version_from_path(path: str, mod_path: str = None) -> str | None:
    """
    Определяет версию игры из пути.

    Args:
        path: Полный или относительный путь
        mod_path: Базовый путь мода (для вычисления относительного пути)

    Returns:
        Версия (например "1.6") или None
    """
    check_path = path
    if mod_path:
        try:
            check_path = os.path.relpath(path, mod_path)
        except ValueError:
            # На разных дисках - используем как есть
            check_path = path

    # Нормализуем разделители
    check_path = check_path.replace("\\", "/")
    path_parts = check_path.split("/")

    for version in SUPPORTED_VERSIONS:
        if version in path_parts:
            return version

    return None


def resolve_target_languages_path(
    mod_path: str,
    target_lang: str,
    mod_output: str = None,
    mode: str = "separate",
    defs_folders_list: list[str] = None,
    create_if_missing: bool = True,
) -> tuple[str, bool]:
    """
    Определяет ЕДИНСТВЕННЫЙ путь к папке Languages/{target_lang}.

    ✅ ИСПРАВЛЕНО:
    1. Проверяет Common/Languages и LoadFolders.xml
    2. Если target_lang не найден, ищет похожие (Russian2, Russian — копия)
    3. Не создаёт пустую папку если есть существующий перевод

    Returns:
        Кортеж (путь_к_Languages/lang, был_создан)
    """
    from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders

    # Шаг 1: Проверяем ВСЕ существующие Languages папки (включая Common/)
    all_langs_folders = find_all_languages_folders_with_loadfolders(mod_path)

    # Ищем папку с целевым языком
    existing_target_folder = None
    common_target = None
    similar_folders = []  # Похожие папки (Russian2, Russian — копия)

    for lang_folder in all_langs_folders:
        # Точное совпадение
        target_sub = os.path.join(lang_folder, target_lang)
        if os.path.exists(target_sub):
            if "Common" in lang_folder:
                common_target = target_sub
            elif existing_target_folder is None:
                existing_target_folder = target_sub
            continue

        # Ищем похожие (Russian2, Russian3, Russian — копия)
        if os.path.exists(lang_folder):
            for existing in os.listdir(lang_folder):
                existing_full = os.path.join(lang_folder, existing)
                if os.path.isdir(existing_full) and existing.lower().startswith(
                    target_lang[:4].lower()
                ):
                    similar_folders.append(existing_full)

    # Сортируем похожие: Russian2, Russian3... перед "Russian — копия"
    similar_folders.sort(
        key=lambda x: (
            0 if any(c.isdigit() for c in os.path.basename(x)) else 1,
            os.path.basename(x),
        )
    )

    # Приоритет 1: Точное совпадение в Common/Languages
    if common_target:
        # Проверяем пуста ли папка
        is_empty = True
        for root_d, dirs_d, files_d in os.walk(common_target):
            if files_d:
                is_empty = False
                break

        if is_empty and similar_folders and create_if_missing:
            # Пустая! Пробуем заполнить из похожего перевода
            source_folder = similar_folders[0]
            source_lang_name = os.path.basename(source_folder)

            # Проверяем что источник не пустой
            src_has_content = False
            for item in os.listdir(source_folder):
                item_path = os.path.join(source_folder, item)
                if os.path.isdir(item_path):
                    for r2, d2, f2 in os.walk(item_path):
                        if f2:
                            src_has_content = True
                            break
                if src_has_content:
                    break

            if src_has_content:
                import shutil

                try:
                    shutil.rmtree(common_target)
                    shutil.copytree(source_folder, common_target)
                    import sys

                    print(
                        f"[ПРЕДУПРЕЖДЕНИЕ] Папка '{target_lang}' была пустой, "
                        f"заполнена из '{source_lang_name}'.",
                        file=sys.stderr,
                    )
                except Exception as e:
                    print(
                        f"[ОШИБКА] Заполнение {target_lang} из {source_lang_name}: {e}",
                        file=sys.stderr,
                    )

                return common_target, True

        return common_target, False

    # Приоритет 2: Точное совпадение в другом месте
    if existing_target_folder:
        return existing_target_folder, False

    # Приоритет 3: Похожий перевод (Russian2 → создаём Russian с копированием)
    if similar_folders and create_if_missing:
        # Берём первый похожий как источник
        source_folder = similar_folders[0]
        source_lang_name = os.path.basename(source_folder)

        # Проверяем что источник НЕ пустой (имеет файлы перевода)
        has_content = False
        if os.path.exists(source_folder):
            for item in os.listdir(source_folder):
                item_path = os.path.join(source_folder, item)
                if os.path.isdir(item_path):
                    # Проверяем есть ли файлы внутри
                    for root_d, dirs_d, files_d in os.walk(item_path):
                        if files_d:
                            has_content = True
                            break
                if has_content:
                    break

        if has_content:
            # Определяем базовую папку Languages
            langs_base = None
            for lang_folder in all_langs_folders:
                if source_folder.startswith(lang_folder):
                    langs_base = lang_folder
                    break

            if langs_base:
                target_base = os.path.join(langs_base, target_lang)

                if not os.path.exists(target_base):
                    # Целевая папка не существует - копируем
                    import shutil

                    try:
                        shutil.copytree(source_folder, target_base)
                        # ✅ Лог предупреждения
                        import sys

                        print(
                            f"[ПРЕДУПРЕЖДЕНИЕ] Папка '{target_lang}' не найдена, "
                            f"но найден похожий перевод '{source_lang_name}'. "
                            f"Создана '{target_lang}' с копированием из '{source_lang_name}'.",
                            file=sys.stderr,
                        )
                    except Exception as e:
                        print(
                            f"[ОШИБКА] Копирование {source_lang_name} → {target_lang}: {e}",
                            file=sys.stderr,
                        )
                        os.makedirs(target_base, exist_ok=True)

                    return target_base, True
                else:
                    # Целевая папка уже существует - проверяем пуста ли она
                    is_empty = True
                    for root_d, dirs_d, files_d in os.walk(target_base):
                        if files_d:
                            is_empty = False
                            break

                    if is_empty:
                        # Пустая - удаляем и копируем
                        import shutil

                        try:
                            shutil.rmtree(target_base)
                            shutil.copytree(source_folder, target_base)
                            import sys

                            print(
                                f"[ПРЕДУПРЕЖДЕНИЕ] Папка '{target_lang}' была пустой, "
                                f"заполнена из '{source_lang_name}'.",
                                file=sys.stderr,
                            )
                        except Exception as e:
                            print(
                                f"[ОШИБКА] Заполнение {target_lang} из {source_lang_name}: {e}",
                                file=sys.stderr,
                            )

                        return target_base, True

                    return target_base, False

    # Шаг 2: Определяем версию из Defs
    version = None
    if defs_folders_list:
        for defs_folder in defs_folders_list:
            ver = detect_version_from_path(defs_folder, mod_path)
            if ver:
                version = ver
                break

    # Шаг 3: Определяем базовый путь
    # Если есть Common/Languages - используем его
    common_langs = os.path.join(mod_path, "Common", "Languages")
    has_common_langs = os.path.exists(common_langs)

    if mode in ("inplace", "merge"):
        if has_common_langs:
            # Приоритет Common/Languages
            target_base = os.path.join(common_langs, target_lang)
        elif has_root_languages_folder(mod_path):
            # Корневая Languages
            target_base = os.path.join(mod_path, "Languages", target_lang)
        elif version:
            # Версионная папка
            target_base = os.path.join(mod_path, version, "Languages", target_lang)
        else:
            # Фоллбэк на корень
            target_base = os.path.join(mod_path, "Languages", target_lang)
    else:
        # Separate mode
        output_base = mod_output or os.path.join(mod_path, "Translated")

        if has_common_langs:
            target_base = os.path.join(common_langs, target_lang)
        elif has_root_languages_folder(mod_path):
            target_base = os.path.join(output_base, "Languages", target_lang)
        elif version:
            target_base = os.path.join(output_base, version, "Languages", target_lang)
        else:
            target_base = os.path.join(output_base, "Languages", target_lang)

    # Шаг 4: Создаём если нужно
    created = False
    if create_if_missing and not os.path.exists(target_base):
        os.makedirs(target_base, exist_ok=True)
        created = True

    return target_base, created


def resolve_def_injected_path(
    mod_path: str,
    target_lang: str,
    mod_output: str = None,
    mode: str = "separate",
    defs_folder: str = None,
    create_if_missing: bool = True,
) -> tuple[str, str, bool]:
    """
    Определяет путь к папке DefInjected внутри Languages/{target_lang}.

    Args:
        mod_path: Путь к папке исходного мода
        target_lang: Целевой язык
        mod_output: Путь к папке вывода (для separate mode)
        mode: Режим перевода
        defs_folder: Путь к исходной папке Defs (для определения версии)
        create_if_missing: Создать папку если не существует

    Returns:
        Кортеж (путь_к_DefInjected, путь_к_Languages_base, был_создан)
    """
    # Используем единую функцию для определения базового пути
    defs_list = [defs_folder] if defs_folder else []
    target_lang_path, created = resolve_target_languages_path(
        mod_path=mod_path,
        target_lang=target_lang,
        mod_output=mod_output,
        mode=mode,
        defs_folders_list=defs_list,
        create_if_missing=create_if_missing,
    )

    # DefInjected находится внутри Languages/{lang}/DefInjected
    def_injected_path = os.path.join(target_lang_path, "DefInjected")

    if create_if_missing and not os.path.exists(def_injected_path):
        os.makedirs(def_injected_path, exist_ok=True)

    return def_injected_path, target_lang_path, created


def resolve_keyed_path(
    mod_path: str,
    target_lang: str,
    mod_output: str = None,
    mode: str = "separate",
    create_if_missing: bool = True,
) -> tuple[str, str, bool]:
    """
    Определяет путь к папке Keyed внутри Languages/{target_lang}.

    Args:
        mod_path: Путь к папке исходного мода
        target_lang: Целевой язык
        mod_output: Путь к папке вывода (для separate mode)
        mode: Режим перевода
        create_if_missing: Создать папку если не существует

    Returns:
        Кортеж (путь_к_Keyed, путь_к_Languages_base, был_создан)
    """
    # Используем единую функцию для определения базового пути
    target_lang_path, created = resolve_target_languages_path(
        mod_path=mod_path,
        target_lang=target_lang,
        mod_output=mod_output,
        mode=mode,
        defs_folders_list=[],  # Keyed не зависит от Defs
        create_if_missing=create_if_missing,
    )

    # Keyed находится внутри Languages/{lang}/Keyed
    keyed_path = os.path.join(target_lang_path, "Keyed")

    if create_if_missing and not os.path.exists(keyed_path):
        os.makedirs(keyed_path, exist_ok=True)

    return keyed_path, target_lang_path, created


def create_source_language_structure(
    mod_path: str,
    source_lang: str = "English",
) -> str | None:
    """
    Проверяет и создаёт папку Languages для source языка, если она не существует.

    ✅ ИСПРАВЛЕНО: Сначала проверяем корневую Languages, только потом версионные.
    Это предотвращает создание дублирующей папки 1.6/Languages.

    Args:
        mod_path: Путь к папке мода
        source_lang: Исходный язык (по умолчанию English)

    Returns:
        Путь к папке Languages или None при ошибке
    """
    import sys

    # ✅ ОТЛАДКА
    print(f"[SOURCE LANG DEBUG] mod_path={mod_path}, source_lang={source_lang}", file=sys.stderr)

    # ✅ ПРИОРИТЕТ 1: Проверяем корневую Languages
    root_langs = os.path.join(mod_path, "Languages")
    root_defs = os.path.join(mod_path, "Defs")

    root_defs_exists = os.path.exists(root_defs)
    root_langs_exists = os.path.exists(root_langs)

    print(
        f"[SOURCE LANG DEBUG]   root_defs_exists={root_defs_exists}, root_langs_exists={root_langs_exists}",
        file=sys.stderr,
    )

    # ✅ ПРИОРИТЕТ 1: Если корневая Languages уже существует — используем её!
    if root_langs_exists:
        source_lang_path = os.path.join(root_langs, source_lang)
        if not os.path.exists(source_lang_path):
            os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
            os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        print("[SOURCE LANG DEBUG]   => ROOT Languages already exists, using it", file=sys.stderr)
        return root_langs

    # ✅ ПРИОРИТЕТ 2: Есть корневая Defs — создаём корневую Languages
    if root_defs_exists:
        os.makedirs(root_langs, exist_ok=True)
        source_lang_path = os.path.join(root_langs, source_lang)
        os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        print("[SOURCE LANG DEBUG]   => Created ROOT Languages (has root Defs)", file=sys.stderr)
        return root_langs

    # ✅ ПРИОРИТЕТ 2.5: Универсальный поиск Defs во ВСЕХ папках (как Text-grabber)
    print("[SOURCE LANG DEBUG]   Универсальный поиск Defs...", file=sys.stderr)
    from utils.loadfolders_parser import find_all_defs_folders_with_loadfolders

    all_defs = find_all_defs_folders_with_loadfolders(mod_path)

    if all_defs:
        # Берём первую найденную папку Defs и создаём Languages рядом
        first_def = all_defs[0]
        # Languages находится на уровень выше Defs
        parent_dir = os.path.dirname(first_def)
        langs_dir = os.path.join(mod_path, parent_dir if parent_dir else "", "Languages")

        # Или проще: Languages в той же папке где и Defs
        langs_base = os.path.dirname(first_def)
        # Если Defs в Common/Defs, то Languages в Common/Languages
        langs_dir = os.path.join(os.path.dirname(first_def).replace("Defs", "Languages"))

        if not os.path.exists(langs_dir):
            # Пробуем найти базу мода и создать Languages там
            # Ищем папку содержащую Defs
            for defs_path in all_defs:
                parent = os.path.dirname(defs_path)
                langs_dir = os.path.join(parent, "Languages")
                if not os.path.exists(langs_dir):
                    os.makedirs(langs_dir, exist_ok=True)

                source_lang_path = os.path.join(langs_dir, source_lang)
                os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
                os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
                print(
                    f"[SOURCE LANG DEBUG]   => Создана Languages в: {os.path.relpath(langs_dir, mod_path)}",
                    file=sys.stderr,
                )
                return langs_dir
        else:
            source_lang_path = os.path.join(langs_dir, source_lang)
            os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
            os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
            print(
                f"[SOURCE LANG DEBUG]   => Languages уже существует: {os.path.relpath(langs_dir, mod_path)}",
                file=sys.stderr,
            )
            return langs_dir

    # ✅ ПРИОРИТЕТ 3: Проверяем версионные папки
    print(
        "[SOURCE LANG DEBUG]   No root/Common Languages/Defs, checking versioned...",
        file=sys.stderr,
    )
    for v in SUPPORTED_VERSIONS:
        v_defs = os.path.join(mod_path, v, "Defs")
        if os.path.exists(v_defs):
            v_langs = os.path.join(mod_path, v, "Languages")
            if not os.path.exists(v_langs):
                os.makedirs(v_langs, exist_ok=True)
                source_lang_path = os.path.join(v_langs, source_lang)
                os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
                os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
                print(f"[SOURCE LANG DEBUG]   => Created versioned Languages: {v}", file=sys.stderr)
            else:
                print(
                    f"[SOURCE LANG DEBUG]   => Versioned Languages already exists: {v}",
                    file=sys.stderr,
                )
            return v_langs

    print("[SOURCE LANG DEBUG]   => No Languages created (no Defs found)", file=sys.stderr)
    return None


def find_all_language_folders(mod_path: str, lang: str) -> list[str]:
    """
    Находит ВСЕ папки с указанным языком в моде (корневые, Common и версионные).

    Args:
        mod_path: Путь к папке мода
        lang: Язык для поиска (English, Russian, и т.д.)

    Returns:
        Список путей к найденным папкам Languages/{lang}
    """
    folders = []

    # Проверяем Common/Languages (Приоритет 1 - LoadFolders.xml)
    common_lang = os.path.join(mod_path, "Common", "Languages", lang)
    if os.path.exists(common_lang):
        folders.append(common_lang)

    # Проверяем корневую Languages
    root_lang = os.path.join(mod_path, "Languages", lang)
    if os.path.exists(root_lang):
        folders.append(root_lang)

    # Проверяем версионные папки
    for version in SUPPORTED_VERSIONS:
        version_lang = os.path.join(mod_path, version, "Languages", lang)
        if os.path.exists(version_lang):
            folders.append(version_lang)

    return folders


def prioritize_language_folders(folders: list[str], mod_path: str) -> list[str]:
    """
    Приоритизирует папки Languages: корневая > версионные.

    Логика:
    1. Сначала возвращаем корневую Languages (если есть)
    2. Затем версионные (1.6, 1.5, ...)
    3. Исключаем дубликаты

    Args:
        folders: Список найденных папок с языком
        mod_path: Путь к папке мода

    Returns:
        Отсортированный список папок (корневая первая)
    """
    if not folders:
        return []

    root_langs = []
    versioned_langs = []

    for folder in folders:
        rel_path = os.path.relpath(folder, mod_path)
        # Проверяем, является ли путь версионным
        is_versioned = detect_version_from_path(rel_path) is not None

        if is_versioned:
            versioned_langs.append(folder)
        else:
            # Корневая Languages или другие варианты
            root_langs.append(folder)

    # Приоритет: корневая папка Languages
    return root_langs + versioned_langs


def get_mod_output_path(mod_path: str, target_lang: str, output_folder: str) -> str:
    """
    Определяет путь вывода для мода в separate mode.

    Args:
        mod_path: Путь к исходному моду
        target_lang: Целевой язык
        output_folder: Базовая папка вывода

    Returns:
        Путь к папке вывода для мода
    """
    mod_name = os.path.basename(mod_path)
    return os.path.join(output_folder, f"{mod_name}-{target_lang}")
