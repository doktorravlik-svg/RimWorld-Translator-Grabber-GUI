# integrity_checker.py - Проверка целостности файлов модов
import os
import lxml.etree as etree
from verification.xml_parser import safe_parse_xml


def check_integrity(mods_folder: str, language_filter=None, log_callback=None) -> bool:
    """
    Проверяет целостность XML файлов в папке модов.

    Args:
        mods_folder: Путь к папке с модами
        language_filter: Язык для фильтрации (например, "Russian") или None для всех
        log_callback: Функция для логирования

    Returns:
        True если все файлы прошли проверку
    """
    if not mods_folder or not os.path.exists(mods_folder):
        if log_callback:
            log_callback(f"Папка модов не найдена: {mods_folder}")
        return False

    errors = []
    warnings = []
    files_checked = 0
    files_with_errors = 0
    files_skipped = 0

    # ✅ НОВОЕ: Подготавливаем путь для фильтрации по языку
    lang_path_segment = None
    if language_filter and language_filter != "Все языки":
        # Формируем ожидаемый путь к языковой папке
        lang_path_segment = f"Languages{os.sep}{language_filter}{os.sep}"
        if log_callback:
            log_callback(f"Фильтр языка: {language_filter}")
            log_callback(f"Проверяются только файлы из: Languages/{language_filter}/")

    for root, dirs, files in os.walk(mods_folder):
        for filename in files:
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(root, filename)

            # ✅ НОВОЕ: Фильтрация по языку
            if lang_path_segment:
                # Проверяем только файлы из Languages/{язык}/
                if lang_path_segment.lower() not in filepath.lower():
                    files_skipped += 1
                    continue

            rel_path = os.path.relpath(filepath, mods_folder)
            files_checked += 1

            # ✅ НОВОЕ: Логирование каждого проверенного файла (для worker)
            if log_callback:
                log_callback(f"[FILE] {rel_path}")

            # Проверка 1: Читаемость файла
            if not os.access(filepath, os.R_OK):
                errors.append(f"Нет прав на чтение: {filepath}")
                files_with_errors += 1
                continue

            # Проверка 2: Размер файла
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                warnings.append(f"Пустой файл: {filepath}")
                continue

            # Проверка 3: Валидность XML
            try:
                root_elem = safe_parse_xml(filepath)
                if root_elem is None:
                    errors.append(f"Нет корневого элемента: {filepath}")
                    files_with_errors += 1
                    continue

                # Проверка 5: Проверка на пустые теги
                empty_tags = 0
                for elem in root_elem.iter():
                    if elem.text and not elem.text.strip() and not list(elem):
                        empty_tags += 1

                if empty_tags > 10:
                    warnings.append(f"Много пустых тегов ({empty_tags}): {filepath}")

            except etree.XMLSyntaxError as e:
                errors.append(f"Ошибка XML: {filepath} - {e}")
                files_with_errors += 1
            except Exception as e:
                errors.append(f"Неожиданная ошибка: {filepath} - {e}")
                files_with_errors += 1

    # Вывод результатов
    if log_callback:
        log_callback("Проверка целостности завершена:")
        log_callback(f"  Проверено файлов: {files_checked}")
        if files_skipped > 0:
            log_callback(f"  Пропущено (фильтр): {files_skipped}")
        log_callback(f"  Файлов с ошибками: {files_with_errors}")
        log_callback(f"  Ошибок: {len(errors)}")
        log_callback(f"  Предупреждений: {len(warnings)}")

        if errors:
            log_callback("\nОшибки:")
            for err in errors[:20]:
                log_callback(f"  ❌ {err}")
            if len(errors) > 20:
                log_callback(f"  ... и ещё {len(errors) - 20} ошибок")

        if warnings:
            log_callback("\nПредупреждения:")
            for warn in warnings[:20]:
                log_callback(f"  ⚠️ {warn}")
            if len(warnings) > 20:
                log_callback(f"  ... и ещё {len(warnings) - 20} предупреждений")

    return len(errors) == 0


def check_mod_structure(mod_path: str, log_callback=None) -> dict:
    """
    Проверяет структуру отдельного мода.

    Args:
        mod_path: Путь к папке мода
        log_callback: Функция для логирования

    Returns:
        Словарь с результатами проверки
    """
    result = {
        "valid": True,
        "has_about": False,
        "has_defs": False,
        "has_languages": False,
        "about_valid": False,
        "errors": [],
        "warnings": [],
    }

    if not os.path.exists(mod_path):
        result["errors"].append(f"Папка не существует: {mod_path}")
        result["valid"] = False
        return result

    # Проверка About.xml
    about_path = os.path.join(mod_path, "About", "About.xml")
    if os.path.exists(about_path):
        result["has_about"] = True
        try:
            root = safe_parse_xml(about_path)
            if root is None:
                result["errors"].append("Не удалось распарсить About.xml")
                result["about_valid"] = False
            else:
                # Проверка обязательных полей
                package_id = root.find("packageId")
                if package_id is None or not package_id.text:
                    result["errors"].append("Отсутствует packageId в About.xml")
                    result["about_valid"] = False
                else:
                    result["about_valid"] = True

        except etree.XMLSyntaxError as e:
            result["errors"].append(f"Ошибка парсинга About.xml: {e}")
            result["about_valid"] = False
    else:
        result["warnings"].append("Отсутствует About.xml")

    # Проверка папки Defs
    for version in ["1.6", "1.5", "1.4", "1.3", ""]:
        defs_path = (
            os.path.join(mod_path, version, "Defs") if version else os.path.join(mod_path, "Defs")
        )
        if os.path.exists(defs_path):
            result["has_defs"] = True
            break

    # Проверка папки Languages
    for version in ["1.6", "1.5", "1.4", "1.3", ""]:
        langs_path = (
            os.path.join(mod_path, version, "Languages")
            if version
            else os.path.join(mod_path, "Languages")
        )
        if os.path.exists(langs_path):
            result["has_languages"] = True
            break

    result["valid"] = len(result["errors"]) == 0

    if log_callback:
        mod_name = os.path.basename(mod_path)
        status = "✅ OK" if result["valid"] else "❌ Ошибки"
        log_callback(f"Мод {mod_name}: {status}")
        for err in result["errors"]:
            log_callback(f"  ❌ {err}")
        for warn in result["warnings"]:
            log_callback(f"  ⚠️ {warn}")

    return result
