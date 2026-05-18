# utils/mod_translation_status.py
"""
Модуль проверки статуса переводов модов для GUI.

Объединяет логику:
- Проверки встроенных переводов (в самом моде)
- Проверки отдельных модов-переводов
- Проверки зависимостей
- Определения полноты перевода
"""

import os
import threading
from dataclasses import dataclass
from enum import Enum


class ModTranslationStatus(Enum):
    """Статус перевода мода"""

    EMBEDDED_FULL = "embedded_full"  # Встроенный полный перевод
    EMBEDDED_PARTIAL = "embedded_partial"  # Встроенный частичный перевод
    SEPARATE_MOD = "separate_mod"  # Отдельный мод-перевод
    NOT_TRANSLATED = "not_translated"  # Нет перевода
    OUTDATED = "outdated"  # Устаревший перевод
    UNKNOWN = "unknown"  # Неизвестно


@dataclass
class ModTranslationInfo:
    """Информация о переводе мода"""

    status: ModTranslationStatus
    status_text: str  # Текст для отображения (✅ Переведён, ⚠️ Частично и т.д.)
    status_icon: str  # Иконка для отображения
    translation_path: str | None = None  # Путь к переводу
    is_separate_mod: bool = False  # Это отдельный мод-перевод?
    parent_mod_id: str | None = None  # ID родительского мода (для отдельных переводов)
    parent_mod_path: str | None = None  # Путь к родительскому моду
    completeness: float = 0.0  # Полнота перевода (0.0 - 1.0)
    dependencies_status: str = ""  # Статус зависимостей
    missing_deps: list[str] = None  # Недостающие зависимости

    def __post_init__(self):
        if self.missing_deps is None:
            self.missing_deps = []


class ModTranslationChecker:
    """
    Проверка статуса переводов модов.

    Используется во вкладке "Перевод" для отображения точного статуса.
    """

    def __init__(self, mods_folder: str, target_language: str = "Russian"):
        self.mods_folder = mods_folder
        self.target_language = target_language
        self._mods_cache: dict[str, dict] = {}  # mod_id -> mod_info
        self._translations_cache: dict[str, dict] = {}  # mod_id -> translation_info
        self._cache_lock = threading.Lock()  # Защита от race condition
        self._scanning = False  # Флаг для предотвращения параллельного сканирования

    def set_target_language(self, target_language: str):
        """
        Обновляет целевой язык перевода.

        После вызова метода следует вызвать scan_mods() для обновления статусов.

        Args:
            target_language: Новый целевой язык (например, "Russian", "English" и т.д.)
        """
        with self._cache_lock:
            self.target_language = target_language

    def scan_mods(self) -> dict[str, dict]:
        """
        Сканирует папку модов и кеширует информацию.

        Returns:
            Словарь {mod_id: mod_info}
        """
        from scanner.mod_scanner import find_about_xml, parse_about_xml

        with self._cache_lock:
            if self._scanning:
                return self._mods_cache.copy()  # Уже сканируется, возвращаем текущий кэш
            self._scanning = True
            self._mods_cache.clear()
            self._translations_cache.clear()

        try:
            if not os.path.exists(self.mods_folder):
                return {}

            temp_cache = {}
            temp_translations = {}

            for item in os.listdir(self.mods_folder):
                mod_path = os.path.join(self.mods_folder, item)
                if not os.path.isdir(mod_path):
                    continue

                about_path = find_about_xml(mod_path)
                if not about_path:
                    continue

                about_data = parse_about_xml(about_path)
                mod_id = about_data.get("mod_id")

                if not mod_id:
                    continue

                mod_info = {
                    "mod_id": mod_id,
                    "mod_name": about_data.get("name", "Unknown"),
                    "mod_path": mod_path,
                    "version": about_data.get("version"),
                    "target_mod_id": about_data.get("target_mod_id"),
                    "dependencies": about_data.get("dependencies", []),
                    "load_after": about_data.get("load_after", []),
                    "author": about_data.get("author"),
                }

                temp_cache[mod_id] = mod_info

                # Классифицируем: это перевод?
                if self._is_translation(mod_info):
                    temp_translations[mod_id] = mod_info

            # Атомарно обновляем кэш
            with self._cache_lock:
                self._mods_cache.update(temp_cache)
                self._translations_cache.update(temp_translations)
        finally:
            with self._cache_lock:
                self._scanning = False

        return self._mods_cache.copy()

    def get_mod_translation_status(self, mod_path: str) -> ModTranslationInfo:
        """
        Определяет статус перевода для мода.

        Args:
            mod_path: Путь к моду

        Returns:
            ModTranslationInfo с полной информацией
        """
        # 1. Получаем информацию о моде (с защитой от race condition)
        mod_info = self._get_mod_info_by_path(mod_path)
        if not mod_info:
            return ModTranslationInfo(
                status=ModTranslationStatus.UNKNOWN, status_text="❓ Неизвестно", status_icon="❓"
            )

        mod_id = mod_info.get("mod_id", "")

        # 2. Проверяем есть ли отдельный мод-перевод
        separate_translation = self._find_separate_translation(mod_id, mod_info)
        if separate_translation:
            return separate_translation

        # 3. Проверяем встроенный перевод
        embedded_status = self._check_embedded_translation(mod_path)
        if embedded_status.status != ModTranslationStatus.NOT_TRANSLATED:
            return embedded_status

        # 4. Нет перевода
        return ModTranslationInfo(
            status=ModTranslationStatus.NOT_TRANSLATED,
            status_text="⬜ Не переведён",
            status_icon="⬜",
        )

    def check_dependencies_status(self, mod_id: str) -> tuple[str, list[str]]:
        """
        Проверяет статус зависимостей мода.

        Args:
            mod_id: ID мода

        Returns:
            (status_text, missing_deps)
        """
        if mod_id not in self._mods_cache:
            return ("", [])

        mod_info = self._mods_cache[mod_id]
        dependencies = mod_info.get("dependencies", [])
        load_after = mod_info.get("load_after", [])

        # Объединяем все зависимости
        all_deps = list(set(dependencies + load_after))

        # Исключаем базовые библиотеки
        exclude_keywords = ["hugslib", "harmony", "xmlextensions", "unity", "brrailz"]
        all_deps = [
            dep for dep in all_deps if not any(kw in dep.lower() for kw in exclude_keywords)
        ]

        if not all_deps:
            return ("✅ Нет зависимостей", [])

        missing_deps = []
        satisfied_deps = []

        for dep_id in all_deps:
            # Ищем зависимость (регистронезависимо)
            found = self._find_mod_by_id(dep_id)
            if found:
                # Проверяем есть ли у зависимости перевод
                dep_status = self.get_mod_translation_status(found["mod_path"])
                if dep_status.status in [
                    ModTranslationStatus.EMBEDDED_FULL,
                    ModTranslationStatus.EMBEDDED_PARTIAL,
                    ModTranslationStatus.SEPARATE_MOD,
                ]:
                    satisfied_deps.append(f"{dep_id} ✅")
                else:
                    satisfied_deps.append(f"{dep_id} ⬜")
            else:
                missing_deps.append(dep_id)

        if missing_deps:
            status_text = f"⚠️ Отсутствуют: {', '.join(missing_deps)}"
        elif satisfied_deps:
            status_text = "✅ Все зависимости найдены"
        else:
            status_text = "✅ Нет зависимостей"

        return (status_text, missing_deps)

    def get_translation_summary(self) -> dict:
        """
        Возвращает сводку по всем переводам.

        Returns:
            Словарь с общей статистикой
        """
        summary = {
            "total_mods": len(self._mods_cache),
            "translated_mods": 0,
            "partial_mods": 0,
            "untranslated_mods": 0,
            "separate_translation_mods": len(self._translations_cache),
        }

        for mod_id, mod_info in self._mods_cache.items():
            if mod_info.get("is_translation"):
                continue  # Пропускаем моды-переводы

            status = self.get_mod_translation_status(mod_info["mod_path"])

            if status.status in [
                ModTranslationStatus.EMBEDDED_FULL,
                ModTranslationStatus.SEPARATE_MOD,
            ]:
                summary["translated_mods"] += 1
            elif status.status == ModTranslationStatus.EMBEDDED_PARTIAL:
                summary["partial_mods"] += 1
            else:
                summary["untranslated_mods"] += 1

        return summary

    # =========================================================================
    # ЧАСТНЫЕ МЕТОДЫ
    # =========================================================================

    def _is_translation(self, mod_info: dict) -> bool:
        """Определяет является ли мод переводом (использует единый модуль классификации)"""
        from utils.mod_classifier import is_translation_mod

        return is_translation_mod(mod_info)

    def _has_language_folder(self, mod_path: str) -> bool:
        """
        Проверяет наличие папки Languages.
        Поддерживает Common/Languages и LoadFolders.xml.
        """
        from utils.loadfolders_parser import find_all_languages_folders_with_loadfolders

        langs = find_all_languages_folders_with_loadfolders(mod_path)
        if langs:
            # Проверяем что внутри есть хотя бы один язык
            for lang_folder in langs:
                if os.listdir(lang_folder):
                    return True

        return False

    def _has_defs_folder(self, mod_path: str) -> bool:
        """
        Проверяет наличие папки Defs.
        Поддерживает Common/Defs и LoadFolders.xml.
        """
        from utils.loadfolders_parser import find_all_defs_folders_with_loadfolders

        defs = find_all_defs_folders_with_loadfolders(mod_path)
        return len(defs) > 0

    def _get_mod_info_by_path(self, mod_path: str) -> dict | None:
        """Получает информацию о моде по пути (с защитой от race condition)"""
        # Сначала ищем в кеше (с блокировкой)
        with self._cache_lock:
            for mod_id, mod_info in self._mods_cache.items():
                if mod_info.get("mod_path") == mod_path:
                    return mod_info.copy() if mod_info else None

        # Если не нашли - сканируем About.xml
        from scanner.mod_scanner import find_about_xml, parse_about_xml

        about_path = find_about_xml(mod_path)
        if not about_path:
            return None

        about_data = parse_about_xml(about_path)
        mod_id = about_data.get("mod_id", "")

        return {
            "mod_id": mod_id,
            "mod_name": about_data.get("name", "Unknown"),
            "mod_path": mod_path,
            "version": about_data.get("version"),
            "target_mod_id": about_data.get("target_mod_id"),
            "dependencies": about_data.get("dependencies", []),
            "load_after": about_data.get("load_after", []),
        }

    def _find_mod_by_id(self, mod_id: str) -> dict | None:
        """Ищет мод по ID (регистронезависимо)"""
        mod_id_lower = mod_id.lower()

        for cached_id, mod_info in self._mods_cache.items():
            if cached_id.lower() == mod_id_lower:
                return mod_info

        return None

    def _find_separate_translation(self, mod_id: str, mod_info: dict) -> ModTranslationInfo | None:
        """
        Ищет отдельный мод-перевод для мода.

        Проверяет:
        - Моды с target_mod_id = mod_id
        - Моды в loadAfter которых есть mod_id
        - Моды-переводы с ключевыми словами в ID указывающие на mod_id
        """
        mod_id_lower = mod_id.lower()

        for trans_id, trans_info in self._translations_cache.items():
            target_id = (trans_info.get("target_mod_id") or "").lower()

            # Прямая ссылка на родительский мод
            if target_id == mod_id_lower:
                return ModTranslationInfo(
                    status=ModTranslationStatus.SEPARATE_MOD,
                    status_text=f"🔵 Отдельный мод ({trans_info.get('mod_name', 'Unknown')})",
                    status_icon="🔵",
                    translation_path=trans_info.get("mod_path"),
                    is_separate_mod=True,
                    parent_mod_id=mod_id,
                    parent_mod_path=mod_info.get("mod_path"),
                )

            # Проверяем loadAfter
            load_after = trans_info.get("load_after", [])
            for dep_id in load_after:
                if dep_id.lower() == mod_id_lower:
                    # Исключаем базовые библиотеки
                    if self._is_base_dependency(dep_id):
                        continue

                    return ModTranslationInfo(
                        status=ModTranslationStatus.SEPARATE_MOD,
                        status_text=f"🔵 Отдельный мод ({trans_info.get('mod_name', 'Unknown')})",
                        status_icon="🔵",
                        translation_path=trans_info.get("mod_path"),
                        is_separate_mod=True,
                        parent_mod_id=mod_id,
                        parent_mod_path=mod_info.get("mod_path"),
                    )

            # ✅ УЛУЧШЕНИЕ: Проверяем содержит ли ID перевода имя родительского мода
            # Например: "kamikadza13.RimHUD" для мода "Jaxe.RimHUD"
            trans_id_lower = trans_id.lower()
            trans_name_lower = (trans_info.get("mod_name") or "").lower()

            # Извлекаем "чистое" имя мода (без префиксов автора)
            mod_name_clean = mod_info.get("mod_name", "").lower()
            trans_name_clean = trans_info.get("mod_name", "").lower()

            # Удаляем префиксы типа "Rus", "Русский", "Translation"
            for prefix in ["rus ", "рус ", "russian ", "translation ", "перевод ", "локализация "]:
                mod_name_clean = mod_name_clean.replace(prefix, "").strip()
                trans_name_clean = trans_name_clean.replace(prefix, "").strip()

            # Если "чистые" имена совпадают - это перевод
            if mod_name_clean and trans_name_clean == mod_name_clean:
                return ModTranslationInfo(
                    status=ModTranslationStatus.SEPARATE_MOD,
                    status_text=f"🔵 Отдельный мод ({trans_info.get('mod_name', 'Unknown')})",
                    status_icon="🔵",
                    translation_path=trans_info.get("mod_path"),
                    is_separate_mod=True,
                    parent_mod_id=mod_id,
                    parent_mod_path=mod_info.get("mod_path"),
                )

        return None

    def _is_base_dependency(self, package_id: str) -> bool:
        """Проверяет является ли мод базовой зависимостью"""
        base_libs = ["unlimitedhugs.hugslib", "0harmony", "imranfish.xmlextensions", "brrailz.lib"]

        package_id_lower = package_id.lower()
        return any(lib in package_id_lower for lib in base_libs)

    def _check_embedded_translation(self, mod_path: str) -> ModTranslationInfo:
        """
        Проверяет встроенный перевод в моде.

        Возвращает статус полноты перевода.
        """
        lang_path = None
        target_lang = self.target_language

        # Ищем Languages/{target_language}
        langs_path = os.path.join(mod_path, "Languages")
        if os.path.exists(langs_path):
            target_lang_path = os.path.join(langs_path, target_lang)
            if os.path.exists(target_lang_path):
                lang_path = target_lang_path

        # Проверяем версионные папки
        if not lang_path:
            for version in ["1.6", "1.5", "1.4", "1.3"]:
                version_langs = os.path.join(mod_path, version, "Languages", target_lang)
                if os.path.exists(version_langs):
                    lang_path = version_langs
                    break

        # Fallback: проверяем Russian если целевой язык не найден
        if not lang_path and target_lang != "Russian":
            russian_path = os.path.join(langs_path, "Russian") if os.path.exists(langs_path) else None
            if os.path.exists(russian_path):
                lang_path = russian_path
            else:
                for version in ["1.6", "1.5", "1.4", "1.3"]:
                    version_langs = os.path.join(mod_path, version, "Languages", "Russian")
                    if os.path.exists(version_langs):
                        lang_path = version_langs
                        break

        if not lang_path:
            return ModTranslationInfo(
                status=ModTranslationStatus.NOT_TRANSLATED,
                status_text="⬜ Не переведён",
                status_icon="⬜",
            )

        # Проверяем полноту перевода
        has_keyed = os.path.exists(os.path.join(lang_path, "Keyed"))
        has_def_injected = os.path.exists(os.path.join(lang_path, "DefInjected"))

        # Если есть DefInjected или Keyed - считаем что есть перевод
        if has_def_injected or has_keyed:
            # Считаем XML файлы для определения полноты
            translation_files = 0

            if has_def_injected:
                for root, dirs, files in os.walk(os.path.join(lang_path, "DefInjected")):
                    translation_files += len([f for f in files if f.endswith(".xml")])

            if has_keyed:
                for root, dirs, files in os.walk(os.path.join(lang_path, "Keyed")):
                    translation_files += len([f for f in files if f.endswith(".xml")])

            # Если есть файлы - полный перевод
            if translation_files > 0:
                return ModTranslationInfo(
                    status=ModTranslationStatus.EMBEDDED_FULL,
                    status_text="✅ Переведён",
                    status_icon="✅",
                    translation_path=lang_path,
                )
            else:
                # Папки есть но файлов нет - частичный
                return ModTranslationInfo(
                    status=ModTranslationStatus.EMBEDDED_PARTIAL,
                    status_text="⚠️ Частично",
                    status_icon="⚠️",
                    translation_path=lang_path,
                )

        # Нет ни DefInjected ни Keyed
        return ModTranslationInfo(
            status=ModTranslationStatus.NOT_TRANSLATED,
            status_text="⬜ Не переведён",
            status_icon="⬜",
        )
