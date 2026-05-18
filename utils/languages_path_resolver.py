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
import shutil
import sys

from utils.loadfolders_parser import (
    find_all_defs_folders_with_loadfolders,
    find_all_languages_folders_with_loadfolders,
)
from utils.mod_version import get_mod_name

# Поддерживаемые версии RimWorld (в порядке приоритета)
SUPPORTED_VERSIONS = ["1.6", "1.5", "1.4", "1.3"]


def _is_folder_empty(path: str) -> bool:
    """Вспомогательная функция для проверки наличия файлов в директории."""
    if not os.path.exists(path):
        return True
    for _, _, files in os.walk(path):
        if files:
            return False
    return True


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


def prioritize_language_folders(folders: list[str], mod_path: str) -> list[str]:
    """
    Приоритизирует папки Languages: корневая/свободные (Contents, Common) > версионные.

    Args:
        folders: Список путей к папкам Languages (например Contents/Languages, 1.6/Languages)
        mod_path: Путь к папке мода

    Returns:
        Отсортированный список (приоритет: не-версионные первыми)
    """
    if not folders:
        return []

    root_langs = []      # Non-versioned: Languages, Common/Languages, Contents/Languages
    versioned_langs = [] # 1.6/Languages, 1.5/Languages

    for folder in folders:
        rel_path = os.path.relpath(folder, mod_path)
        # Проверяем, является ли путь версионным (содержит /1.6/, /1.5/ и т.д.)
        path_parts = rel_path.replace("\\", "/").split("/")
        is_versioned = any(part in SUPPORTED_VERSIONS for part in path_parts)

        if is_versioned:
            versioned_langs.append(folder)
        else:
            root_langs.append(folder)

    # Приоритет: корневые и Common/Contents > версионные
    return root_langs + versioned_langs


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

    Returns:
        Кортеж (путь_к_Languages/lang, был_создан)
    """
    # ✅ ИСПРАВЛЕНО: Для separate mode ВСЕГДА используем mod_output
    if mode == "separate" and mod_output:
        target_base = mod_output
        created = False
        if create_if_missing and not os.path.exists(target_base):
            os.makedirs(target_base, exist_ok=True)
            created = True
        return target_base, created

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
        is_empty = _is_folder_empty(common_target)

        if is_empty and similar_folders and create_if_missing:
            # Пустая! Пробуем заполнить из похожего перевода
            source_folder = similar_folders[0]
            source_lang_name = os.path.basename(source_folder)

            # Проверяем что источник не пустой
            src_has_content = not _is_folder_empty(source_folder)

            if src_has_content:
                try:
                    shutil.rmtree(common_target)
                    shutil.copytree(source_folder, common_target)
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
        has_content = not _is_folder_empty(source_folder)

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
                    try:
                        shutil.copytree(source_folder, target_base)
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
                    is_empty = _is_folder_empty(target_base)

                    if is_empty:
                        # Пустая - удаляем и копируем
                        try:
                            shutil.rmtree(target_base)
                            shutil.copytree(source_folder, target_base)
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

    # Шаг 3: Определяем базовый путь для Languages (inplace/merge)
    if mode in ("inplace", "merge"):
        # Ищем базовый Languages, соответствующий папке Defs
        if defs_folders_list:
            # Берём первую папку Defs и ищем Languages на том же уровне
            first_defs = defs_folders_list[0]
            parent_dir = os.path.dirname(first_defs)
            # Проверяем, есть ли Languages на том же уровне что и Defs
            candidate = os.path.join(parent_dir, "Languages")
            if os.path.exists(candidate):
                target_base = os.path.join(candidate, target_lang)
            else:
                # Если нет, используем fallback
                common_langs = os.path.join(mod_path, "Common", "Languages")
                if os.path.exists(common_langs):
                    target_base = os.path.join(common_langs, target_lang)
                elif has_root_languages_folder(mod_path):
                    target_base = os.path.join(mod_path, "Languages", target_lang)
                elif version:
                    target_base = os.path.join(mod_path, version, "Languages", target_lang)
                else:
                    target_base = os.path.join(mod_path, "Languages", target_lang)
        else:
            # Нет Defs папок — fallback
            common_langs = os.path.join(mod_path, "Common", "Languages")
            if os.path.exists(common_langs):
                target_base = os.path.join(common_langs, target_lang)
            elif has_root_languages_folder(mod_path):
                target_base = os.path.join(mod_path, "Languages", target_lang)
            elif version:
                target_base = os.path.join(mod_path, version, "Languages", target_lang)
            else:
                target_base = os.path.join(mod_path, "Languages", target_lang)
    else:
        # Separate mode: используем mod_output если передан, иначе fallback
        if mod_output:
            target_base = mod_output
        else:
            output_base = os.path.join(mod_path, "Translated")
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


def create_source_language_structure(mod_path: str, source_lang: str = "English") -> str | None:
    """
    Создает структуру папок для исходного языка (English).
    Приоритет:
      0. Существующая Languages (LoadFolders/scan) → используем, создаём папку языка внутри
      1. Корневая Defs → создать Languages/
      2. Common/Defs → создать Common/Languages/
      3. Версия/V/Defs → создать V/Languages/
      4. Fallback: Languages рядом с любыми Defs (через LoadFolders)
    Возвращает путь к папке Languages или None.
    """
    print(f"[DEBUG] create_source_language_structure: mod_path={mod_path}, source_lang={source_lang}", file=sys.stderr)

    # Приоритет 0: Есть ли уже Languages где-либо?
    all_langs_folders = find_all_languages_folders_with_loadfolders(mod_path)
    print(f"[DEBUG]   Найдены Languages папки: {all_langs_folders}", file=sys.stderr)
    if all_langs_folders:
        chosen_langs = all_langs_folders[0]
        print(f"[DEBUG]   => Выбрана папка Languages: {chosen_langs}", file=sys.stderr)
        source_lang_path = os.path.join(chosen_langs, source_lang)
        os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "Strings"), exist_ok=True)
        print(f"[DEBUG]   => Создана структура для {source_lang} в {chosen_langs}", file=sys.stderr)
        return chosen_langs

    # Приоритет 1: Корневая Defs/
    root_defs = os.path.join(mod_path, "Defs")
    if os.path.exists(root_defs):
        root_langs = os.path.join(mod_path, "Languages")
        os.makedirs(root_langs, exist_ok=True)
        print(f"[DEBUG]   => Создана корневая Languages (из Defs): {root_langs}", file=sys.stderr)
        source_lang_path = os.path.join(root_langs, source_lang)
        os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "Strings"), exist_ok=True)
        return root_langs

    # Приоритет 2: Common/Defs
    common_defs = os.path.join(mod_path, "Common", "Defs")
    if os.path.exists(common_defs):
        common_langs = os.path.join(mod_path, "Common", "Languages")
        os.makedirs(common_langs, exist_ok=True)
        print(f"[DEBUG]   => Создана Common/Languages (из Common/Defs): {common_langs}", file=sys.stderr)
        source_lang_path = os.path.join(common_langs, source_lang)
        os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "Strings"), exist_ok=True)
        return common_langs

    # Приоритет 3: Версионные папки (1.6, 1.5, ...)
    for version in SUPPORTED_VERSIONS:
        v_defs = os.path.join(mod_path, version, "Defs")
        if os.path.exists(v_defs):
            v_langs = os.path.join(mod_path, version, "Languages")
            os.makedirs(v_langs, exist_ok=True)
            print(f"[DEBUG]   => Создана {version}/Languages (из {version}/Defs): {v_langs}", file=sys.stderr)
            source_lang_path = os.path.join(v_langs, source_lang)
            os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
            os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
            os.makedirs(os.path.join(source_lang_path, "Strings"), exist_ok=True)
            return v_langs

    # Приоритет 4: Fallback — ищем любые Defs через LoadFolders
    all_defs = find_all_defs_folders_with_loadfolders(mod_path)
    if all_defs:
        first_def = all_defs[0]
        parent_dir = os.path.dirname(first_def)
        candidate_langs = os.path.join(parent_dir, "Languages")
        os.makedirs(candidate_langs, exist_ok=True)
        print(f"[DEBUG]   => Создана Languages рядом с Defs (fallback): {candidate_langs}", file=sys.stderr)
        source_lang_path = os.path.join(candidate_langs, source_lang)
        os.makedirs(os.path.join(source_lang_path, "Keyed"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "DefInjected"), exist_ok=True)
        os.makedirs(os.path.join(source_lang_path, "Strings"), exist_ok=True)
        return candidate_langs

    print(f"[DEBUG]   => Не найдено папок Defs, Languages не создана", file=sys.stderr)
    return None


def find_all_language_folders(mod_path: str, lang: str) -> list[str]:
    """
    Находит ВСЕ папки Languages/{lang} в моде (через LoadFolders/универсальный поиск).

    Args:
        mod_path: Путь к папке мода
        lang: Язык для поиска (English, Russian, и т.д.)

    Returns:
        Список путей к найденным папкам Languages/{lang}
    """
    # Получаем все Languages папки
    all_langs_folders = find_all_languages_folders_with_loadfolders(mod_path)
    # Фильтруем те, где есть нужный язык
    result = []
    for langs_folder in all_langs_folders:
        lang_path = os.path.join(langs_folder, lang)
        if os.path.exists(lang_path):
            result.append(lang_path)  # Возвращаем путь к языку (например .../Languages/English)
    return result


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
    mod_name = get_mod_name(mod_path)
    res = os.path.join(output_folder, mod_name, "Languages", target_lang)
    os.makedirs(res, exist_ok=True)
    return res
