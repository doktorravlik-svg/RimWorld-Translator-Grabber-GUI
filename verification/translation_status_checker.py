# verification/translation_status_checker.py
"""
Модуль проверки статуса переводов модов RimWorld.

Основные функции:
- TranslationStatusChecker: класс проверки актуальности переводов
- Определение устаревших переводов
- Определение соответствия версий перевода и родительского мода
- Анализ дерева зависимостей переводов
"""

import os
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


# ============================================================================
# ТИПЫ ДАННЫХ
# ============================================================================

class TranslationStatus(Enum):
    """Статус перевода"""
    UP_TO_DATE = "up_to_date"          # Актуальный
    OUTDATED = "outdated"              # Устаревший
    VERSION_MISMATCH = "version_mismatch"  # Несовпадение версий
    CUSTOM = "custom"                  # Пользовательский перевод
    UNKNOWN = "unknown"                # Неизвестно
    MISSING_PARENT = "missing_parent" # Родительский мод не найден


class TranslationType(Enum):
    """Тип перевода"""
    STANDALONE = "standalone"          # Отдельный мод-перевод
    EMBEDDED = "embedded"              # Встроенный перевод
    CUSTOM = "custom"                  # Пользовательский перевод


@dataclass
class TranslationDependencyInfo:
    """Информация о зависимости перевода"""
    translation_mod_id: str
    translation_mod_name: str
    parent_mod_id: str
    parent_mod_name: str
    translation_version: str
    parent_version: str
    status: TranslationStatus
    translation_type: TranslationType
    is_compatible: bool
    issues: List[str] = field(default_factory=list)


@dataclass
class TranslationDependencyReport:
    """Отчет о зависимостях переводов"""
    total_translations: int = 0
    up_to_date: int = 0
    outdated: int = 0
    version_mismatch: int = 0
    custom_translations: int = 0
    missing_parent: int = 0
    standalone_translations: int = 0
    embedded_translations: int = 0
    dependencies: List[TranslationDependencyInfo] = field(default_factory=list)
    tree: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# КЛАСС TRANSLATION STATUS CHECKER
# ============================================================================

class TranslationStatusChecker:
    """
    Класс для проверки статуса переводов и их зависимостей.

    Поддерживает:
    - Определение типа перевода (standalone/embedded/custom)
    - Проверку актуальности перевода относительно версии родительского мода
    - Построение дерева зависимостей переводов
    - Определение устаревших переводов
    """

    def __init__(self, mods_path: str, logger: Any | None = None):
        self.mods_path = mods_path
        self.logger = logger
        self._mods_cache: Dict[str, Dict] = {}
        self._translations: Dict[str, Dict] = {}  # translation_mod_id -> translation_info
        self._parents: Dict[str, Dict] = {}  # parent_mod_id -> parent_info

    # =========================================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # =========================================================================

    def load_mods(self) -> Dict[str, Dict]:
        """
        Загружает информацию обо всех модах и классифицирует их.

        Returns:
            Словарь {packageId: mod_info}
        """
        from scanner.mod_scanner import parse_about_xml, find_about_xml

        if not os.path.exists(self.mods_path):
            if self.logger:
                self.logger.error(f"Путь к модам не существует: {self.mods_path}")
            return {}

        # Очищаем кэш перед загрузкой
        self._mods_cache.clear()
        self._translations.clear()
        self._parents.clear()

        mods_found = 0
        mods_with_about = 0
        mods_with_id = 0

        # Сканируем все папки в Mods
        for item in os.listdir(self.mods_path):
            mod_path = os.path.join(self.mods_path, item)
            if not os.path.isdir(mod_path):
                continue

            mods_found += 1

            # Ищем About.xml
            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            mods_with_about += 1

            # Парсим About.xml
            about_data = parse_about_xml(about_path)
            mod_id = about_data.get('mod_id')

            if not mod_id:
                if self.logger:
                    self.logger.debug(f"Мод без packageId: {mod_path}")
                continue

            mods_with_id += 1

            mod_info = {
                'mod_id': mod_id,
                'mod_name': about_data.get('name', 'Unknown'),
                'mod_path': mod_path,
                'about_path': about_path,
                'version': about_data.get('version'),
                'target_mod_id': about_data.get('target_mod_id'),
                'target_content_creator': about_data.get('target_content_creator'),
                'author': about_data.get('author'),
                'dependencies': about_data.get('dependencies', []),
                'supported_languages': about_data.get('supported_languages', []),
                'load_after': about_data.get('load_after', []),
                'load_before': about_data.get('load_before', []),
                'has_languages': self._has_language_folder(mod_path),
                'has_defs': self._has_defs_folder(mod_path),
            }

            self._mods_cache[mod_id] = mod_info

            # Классифицируем мод
            is_translation, translation_type = self._classify_mod(mod_info)
            mod_info['is_translation'] = is_translation
            mod_info['translation_type'] = translation_type

            if is_translation:
                self._translations[mod_id] = mod_info
            else:
                self._parents[mod_id] = mod_info

        # После загрузки всех модов определяем родительские моды для переводов
        # без target_mod_id через анализ loadAfter
        self._resolve_parent_mods_from_load_after()

        if self.logger:
            self.logger.info(f"Найдено модов: {mods_found}, с About.xml: {mods_with_about}, "
                           f"с packageId: {mods_with_id}")
            self.logger.info(f"Загружено {len(self._mods_cache)} модов, "
                           f"{len(self._translations)} переводов, "
                           f"{len(self._parents)} родительских модов")
        else:
            print(f"[INFO] Найдено модов: {mods_found}, с About.xml: {mods_with_about}, "
                  f"с packageId: {mods_with_id}")
            print(f"[INFO] Загружено {len(self._mods_cache)} модов, "
                  f"{len(self._translations)} переводов, "
                  f"{len(self._parents)} родительских модов")

        return self._mods_cache

    def load_mods_multi(self, mods_path: str) -> Dict[str, Dict]:
        """
        Загружает моды из указанной папки в общий кэш.
        Используется для сканирования нескольких папок с модами.

        Args:
            mods_path: Путь к папке с модами

        Returns:
            Словарь {packageId: mod_info}
        """
        from scanner.mod_scanner import parse_about_xml, find_about_xml

        if not os.path.exists(mods_path):
            return {}

        mods_found = 0
        mods_with_about = 0
        mods_with_id = 0

        # Сканируем все папки
        for item in os.listdir(mods_path):
            mod_path = os.path.join(mods_path, item)
            if not os.path.isdir(mod_path):
                continue

            mods_found += 1

            # Ищем About.xml
            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            mods_with_about += 1

            # Парсим About.xml
            about_data = parse_about_xml(about_path)
            mod_id = about_data.get('mod_id')

            if not mod_id:
                continue

            mods_with_id += 1

            # Проверяем не загружен ли уже мод с таким ID
            if mod_id in self._mods_cache:
                continue

            mod_info = {
                'mod_id': mod_id,
                'mod_name': about_data.get('name', 'Unknown'),
                'mod_path': mod_path,
                'about_path': about_path,
                'version': about_data.get('version'),
                'target_mod_id': about_data.get('target_mod_id'),
                'target_content_creator': about_data.get('target_content_creator'),
                'author': about_data.get('author'),
                'dependencies': about_data.get('dependencies', []),
                'supported_languages': about_data.get('supported_languages', []),
                'load_after': about_data.get('load_after', []),
                'load_before': about_data.get('load_before', []),
                'has_languages': self._has_language_folder(mod_path),
                'has_defs': self._has_defs_folder(mod_path),
            }

            self._mods_cache[mod_id] = mod_info

            # Классифицируем мод
            is_translation, translation_type = self._classify_mod(mod_info)
            mod_info['is_translation'] = is_translation
            mod_info['translation_type'] = translation_type

            if is_translation:
                self._translations[mod_id] = mod_info
            else:
                self._parents[mod_id] = mod_info

        # После загрузки всех модов определяем родительские моды для переводов
        self._resolve_parent_mods_from_load_after()

        return self._mods_cache

    def _resolve_parent_mods_from_load_after(self):
        """
        Определяет родительские моды для всех переводов без target_mod_id.

        Вызывается после загрузки всех модов когда _mods_cache заполнён.
        """
        for mod_id, mod_info in self._translations.items():
            if not mod_info.get('target_mod_id'):
                parent_id = self._guess_parent_from_load_after(mod_info)
                if parent_id:
                    mod_info['target_mod_id'] = parent_id
                    if self.logger:
                        self.logger.debug(f"Определён родитель для {mod_id}: {parent_id}")

    def check_translation_status(self, translation_mod_id: str) -> TranslationDependencyInfo:
        """
        Проверяет статус одного перевода.

        Args:
            translation_mod_id: ID мода перевода

        Returns:
            TranslationDependencyInfo с информацией о статусе перевода
        """
        if translation_mod_id not in self._translations:
            return TranslationDependencyInfo(
                translation_mod_id=translation_mod_id,
                translation_mod_name="Unknown",
                parent_mod_id="",
                parent_mod_name="",
                translation_version="",
                parent_version="",
                status=TranslationStatus.UNKNOWN,
                translation_type=TranslationType.CUSTOM,
                is_compatible=False,
                issues=["Мод перевода не найден"]
            )

        trans_mod = self._translations[translation_mod_id]
        parent_mod_id = trans_mod.get('target_mod_id')
        translation_version = trans_mod.get('version', '0.0.0')

        # Определяем тип перевода
        translation_type = trans_mod.get('translation_type', TranslationType.STANDALONE)

        # Проверяем наличие родительского мода
        if not parent_mod_id:
            # Это может быть пользовательский перевод без ссылки на родителя
            is_custom = self._is_custom_translation(trans_mod)
            return TranslationDependencyInfo(
                translation_mod_id=translation_mod_id,
                translation_mod_name=trans_mod['mod_name'],
                parent_mod_id="",
                parent_mod_name="",
                translation_version=translation_version,
                parent_version="",
                status=TranslationStatus.CUSTOM if is_custom else TranslationStatus.UNKNOWN,
                translation_type=translation_type,
                is_compatible=True,
                issues=["Перевод не имеет ссылки на родительский мод"]
            )

        # Проверяем наличие родительского мода (регистронезависимо)
        parent_mod = None
        found_parent_id = None

        # Сначала проверяем точное совпадение
        if parent_mod_id in self._parents:
            parent_mod = self._parents[parent_mod_id]
            found_parent_id = parent_mod_id
        else:
            # Проверяем в _mods_cache (регистронезависимо)
            found_parent_id = self._find_mod_in_cache(parent_mod_id)
            if found_parent_id:
                if found_parent_id in self._parents:
                    parent_mod = self._parents[found_parent_id]
                else:
                    parent_mod = self._mods_cache[found_parent_id]

        if not parent_mod:
            return TranslationDependencyInfo(
                translation_mod_id=translation_mod_id,
                translation_mod_name=trans_mod['mod_name'],
                parent_mod_id=parent_mod_id,
                parent_mod_name="Unknown",
                translation_version=translation_version,
                parent_version="",
                status=TranslationStatus.MISSING_PARENT,
                translation_type=translation_type,
                is_compatible=False,
                issues=[f"Родительский мод '{parent_mod_id}' не найден"]
            )

        parent_version = parent_mod.get('version', '0.0.0')

        # Проверяем совместимость версий
        is_compatible, status, issues = self._check_version_compatibility(
            translation_version, parent_version
        )

        return TranslationDependencyInfo(
            translation_mod_id=translation_mod_id,
            translation_mod_name=trans_mod['mod_name'],
            parent_mod_id=parent_mod_id,
            parent_mod_name=parent_mod['mod_name'],
            translation_version=translation_version,
            parent_version=parent_version,
            status=status,
            translation_type=translation_type,
            is_compatible=is_compatible,
            issues=issues
        )

    def check_all_translations(self) -> TranslationDependencyReport:
        """
        Проверяет статус всех переводов.

        Returns:
            TranslationDependencyReport с полной информацией
        """
        report = TranslationDependencyReport()

        for trans_mod_id in self._translations:
            info = self.check_translation_status(trans_mod_id)
            report.dependencies.append(info)

            # Подсчитываем статистику
            report.total_translations += 1

            if info.status == TranslationStatus.UP_TO_DATE:
                report.up_to_date += 1
            elif info.status == TranslationStatus.OUTDATED:
                report.outdated += 1
            elif info.status == TranslationStatus.VERSION_MISMATCH:
                report.version_mismatch += 1
            elif info.status == TranslationStatus.CUSTOM:
                report.custom_translations += 1
            elif info.status == TranslationStatus.MISSING_PARENT:
                report.missing_parent += 1

            if info.translation_type == TranslationType.STANDALONE:
                report.standalone_translations += 1
            elif info.translation_type == TranslationType.EMBEDDED:
                report.embedded_translations += 1

        # Строим дерево зависимостей
        report.tree = self._build_dependency_tree()

        return report

    def get_translation_tree(self) -> Dict[str, Any]:
        """
        Возвращает дерево зависимостей переводов.

        Returns:
            Словарь с деревом зависимостей для визуализации
        """
        return self._build_dependency_tree()

    # =========================================================================
    # ЧАСТНЫЕ МЕТОДЫ
    # =========================================================================

    def _has_language_folder(self, mod_path: str) -> bool:
        """Проверяет наличие папки Languages"""
        languages_path = os.path.join(mod_path, 'Languages')
        if not os.path.exists(languages_path):
            # Проверяем версионные папки
            for version in ['1.6', '1.5', '1.4', '1.3', '1.2', '1.1', '1.0']:
                version_langs = os.path.join(mod_path, version, 'Languages')
                if os.path.exists(version_langs):
                    return True
            return False
        return True

    def _has_defs_folder(self, mod_path: str) -> bool:
        """Проверяет наличие папки Defs"""
        defs_path = os.path.join(mod_path, 'Defs')
        if not os.path.exists(defs_path):
            # Проверяем версионные папки
            for version in ['1.6', '1.5', '1.4', '1.3', '1.2', '1.1', '1.0']:
                version_defs = os.path.join(mod_path, version, 'Defs')
                if os.path.exists(version_defs):
                    return True
            return False
        return True

    def _classify_mod(self, mod_info: Dict) -> Tuple[bool, TranslationType]:
        """
        Классифицирует мод как перевод или основной мод.

        Стратегия определения:
        1. Явные признаки: target_mod_id, target_content_creator
        2. Ключевые слова в packageId/name (translation, localization, названия языков)
        3. Структура: есть Languages, нет Defs → перевод
        4. Есть Languages и Defs → встроенный перевод
        5. Есть loadAfter и нет Defs → возможный перевод

        Returns:
            (is_translation, translation_type)
        """
        # 1. Явные признаки перевода
        if mod_info.get('target_mod_id'):
            return True, TranslationType.STANDALONE

        if mod_info.get('target_content_creator'):
            return True, TranslationType.STANDALONE

        # 2. Проверяем признаки в packageId и name
        mod_id = mod_info.get('mod_id', '').lower()
        mod_name = mod_info.get('mod_name', '').lower()

        # Ключевые слова указывающие на перевод
        translation_keywords = [
            # Общие слова перевода
            'translation', 'localization', 'localiser', 'translator', 'translate',

            # Названия языков (полные)
            'russian', 'english', 'german', 'french', 'spanish', 'chinese',
            'japanese', 'korean', 'italian', 'portuguese', 'polish', 'turkish',
            'dutch', 'swedish', 'norwegian', 'danish', 'finnish', 'czech',
            'hungarian', 'romanian', 'bulgarian', 'greek', 'arabic', 'hebrew',
            'thai', 'vietnamese', 'indonesian', 'malay', 'tagalog',

            # Русские названия
            'русификатор', 'перевод', 'локализация', 'язык',

            # Технические маркеры
            'utf', 'utf8', 'utf-8', 'ru-ru', 'en-us', 'en-gb', 'de-de',
            'fr-fr', 'es-es', 'zh-cn', 'ja-jp', 'ko-kr'
        ]

        if any(keyword in mod_id for keyword in translation_keywords):
            return True, TranslationType.STANDALONE

        if any(keyword in mod_name for keyword in translation_keywords):
            return True, TranslationType.STANDALONE

        # 3. Проверяем структуру мода
        has_languages = mod_info.get('has_languages', False)
        has_defs = mod_info.get('has_defs', False)
        load_after = mod_info.get('load_after', [])

        # Если есть Languages но нет Defs - это точно перевод
        if has_languages and not has_defs:
            return True, TranslationType.STANDALONE

        # Встроенные переводы (в моде есть и Languages, и Defs)
        if has_languages and has_defs:
            return True, TranslationType.EMBEDDED

        # 4. Если есть loadAfter и нет Defs - возможный перевод
        #    (многие переводы не имеют ключевых слов в названии)
        if has_languages and load_after and not has_defs:
            return True, TranslationType.STANDALONE

        return False, TranslationType.STANDALONE

    def _is_custom_translation(self, mod_info: Dict) -> bool:
        """
        Определяет, является ли перевод пользовательским (custom).

        Пользовательские переводы обычно:
        - Не имеют ссылки на target_mod_id
        - Имеют специфичные названия (Custom, User, Extra и т.д.)
        - Автор не является официальным разработчиком
        """
        mod_name = mod_info.get('mod_name', '').lower()
        author = mod_info.get('author', '').lower()

        # Признаки пользовательского перевода
        custom_indicators = ['custom', 'user', 'extra', 'private', 'my ', ' personalized']
        if any(indicator in mod_name for indicator in custom_indicators):
            return True

        # Если естьLanguages но нет target_mod_id - вероятно custom
        if mod_info.get('has_languages') and not mod_info.get('target_mod_id'):
            return True

        return False

    def _guess_parent_from_load_after(self, mod_info: Dict) -> Optional[str]:
        """
        Пытается угадать родительский мод перевода из списка loadAfter.

        Для переводов, которые не имеют target_mod_id, анализируется список
        loadAfter для поиска основного мода, который переводится.

        Приоритеты поиска:
        1. Моды из modDependencies (если есть)
        2. Основные моды (не аддоны/расширения) которые существуют в папке
        3. Первый мод из loadAfter который существует в папке

        Args:
            mod_info: Информация о моде перевода

        Returns:
            packageId родительского мода или None
        """
        load_after = mod_info.get('load_after', [])
        dependencies = mod_info.get('dependencies', [])

        if not load_after:
            return None

        # 1. Сначала проверяем modDependencies - это явные зависимости
        for dep_id in dependencies:
            found_id = self._find_mod_in_cache(dep_id)
            if found_id:
                # Проверяем что это не базовые зависимости типа HugsLib
                if not self._is_base_dependency(found_id):
                    return found_id

        # 2. Ищем моды в loadAfter которые существуют в папке
        #    Исключаем известные библиотеки и фреймворки
        exclude_keywords = [
            'hugslib', 'harmony', 'xml', 'extensions', 'unity',
            'vanilla', 'expanded', 'framework', 'lib'
        ]

        matches = []
        for dep_id in load_after:
            # Сравниваем регистронезависимо и получаем правильный packageId
            found_id = self._find_mod_in_cache(dep_id)
            if found_id:
                dep_lower = dep_id.lower()

                # Исключаем библиотеки и фреймворки
                if any(kw in dep_lower for kw in exclude_keywords):
                    continue

                # Исключаем моды с ключевыми словами аддонов
                addon_keywords = ['addon', 'extension', 'patch', 'fix', 'compatibility']
                if any(kw in dep_lower for kw in addon_keywords):
                    continue

                matches.append(found_id)  # Возвращаем правильный packageId из кэша

        # Возвращаем первый найденный мод
        if matches:
            return matches[0]

        # 3. Если ничего не найдено, возвращаем первый из loadAfter
        return load_after[0] if load_after else None

    def _find_mod_in_cache(self, package_id: str) -> Optional[str]:
        """
        Ищет мод в кэше по packageId (регистронезависимо).

        Args:
            package_id: packageId мода для поиска

        Returns:
            packageId из кэша или None
        """
        package_id_lower = package_id.lower()

        for mod_id, mod_info in self._mods_cache.items():
            if mod_id.lower() == package_id_lower:
                return mod_id  # Возвращаем правильный packageId из кэша

        return None

    def _is_base_dependency(self, package_id: str) -> bool:
        """
        Проверяет является ли мод базовой зависимостью (библиотекой).

        Args:
            package_id: packageId мода для проверки

        Returns:
            True если это базовая библиотека, False иначе
        """
        base_libs = [
            'unlimitedhugs.hugslib',
            '0harmony',
            'imranfish.xmlextensions',
            'brrailz.lib',
            'zylle.groupframework'
        ]

        package_id_lower = package_id.lower()
        return any(lib in package_id_lower for lib in base_libs)

    def _mod_exists_in_folder(self, package_id: str) -> bool:
        """
        Проверяет существует ли мод с указанным packageId в папке Mods.

        Args:
            package_id: packageId мода для поиска

        Returns:
            True если мод найден, False иначе
        """
        return self._find_mod_in_cache(package_id) is not None

    def _check_version_compatibility(self, translation_version: str,
                                     parent_version: str) -> Tuple[bool, TranslationStatus, List[str]]:
        """
        Проверяет совместимость версий перевода и родительского мода.

        Returns:
            (is_compatible, status, issues)
        """
        issues = []

        # Если версии не указаны
        if not translation_version or translation_version == '0.0.0':
            return True, TranslationStatus.UNKNOWN, ["Версия перевода не указана"]

        if not parent_version or parent_version == '0.0.0':
            return True, TranslationStatus.UNKNOWN, ["Версия родительского мода не указана"]

        # Сравниваем версии
        try:
            trans_ver = self._parse_version(translation_version)
            parent_ver = self._parse_version(parent_version)

            if trans_ver == parent_ver:
                return True, TranslationStatus.UP_TO_DATE, []

            # Проверяем мажорную версию
            if trans_ver[0] != parent_ver[0]:
                issues.append(f"Несовпадение мажорных версий: перевод {translation_version}, родитель {parent_version}")
                return False, TranslationStatus.VERSION_MISMATCH, issues

            # Проверяем минорную версию
            if trans_ver[1] < parent_ver[1]:
                issues.append(f"Перевод устарел: версия перевода {translation_version} ниже {parent_version}")
                return False, TranslationStatus.OUTDATED, issues

            # trans_ver > parent_ver - перевод новее, но это не проблема
            return True, TranslationStatus.UP_TO_DATE, []

        except Exception as e:
            issues.append(f"Ошибка сравнения версий: {e}")
            return True, TranslationStatus.UNKNOWN, issues

    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """
        Парсит версию в кортеж (major, minor, patch).

        Args:
            version: Строка версии (например "1.6.0")

        Returns:
            Кортеж (major, minor, patch)
        """
        parts = version.replace(',', '.').split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)

    def _build_dependency_tree(self) -> Dict[str, Any]:
        """
        Строит дерево зависимостей переводов.

        Returns:
            Словарь с деревом для визуализации
        """
        tree = {
            'nodes': [],
            'edges': []
        }

        # Отслеживаем добавленные узлы
        added_nodes = set()

        # 1. Сначала добавляем все родительские моды из _parents
        for mod_id, mod_info in self._parents.items():
            tree['nodes'].append({
                'id': mod_id,
                'label': mod_info['mod_name'],
                'type': 'parent',
                'version': mod_info.get('version', 'Unknown'),
                'status': 'ok'
            })
            added_nodes.add(mod_id)

        # 2. Добавляем переводы и их родителей
        for mod_id, mod_info in self._translations.items():
            parent_id = mod_info.get('target_mod_id', '')
            status = self.check_translation_status(mod_id)

            tree['nodes'].append({
                'id': mod_id,
                'label': mod_info['mod_name'],
                'type': 'translation',
                'translation_type': status.translation_type.value,
                'status': status.status.value,
                'version': mod_info.get('version', 'Unknown'),
                'parent_id': parent_id
            })
            added_nodes.add(mod_id)

            # Создаем связь если есть родитель
            if parent_id:
                # Проверяем есть ли родитель в кэше (регистронезависимо)
                found_parent_id = self._find_mod_in_cache(parent_id)

                # Если родитель есть в папке - создаем связь
                if found_parent_id:
                    # Добавляем узел родителя если ещё не добавлен
                    if found_parent_id not in added_nodes:
                        parent_mod = self._mods_cache.get(found_parent_id)
                        if parent_mod:
                            tree['nodes'].append({
                                'id': found_parent_id,
                                'label': parent_mod['mod_name'],
                                'type': 'parent',
                                'version': parent_mod.get('version', 'Unknown'),
                                'status': 'ok'
                            })
                            added_nodes.add(found_parent_id)

                    tree['edges'].append({
                        'from': mod_id,
                        'to': found_parent_id,
                        'label': 'translates'
                    })
                # Если родителя нет в папке - добавляем его как узел-заглушку
                else:
                    tree['nodes'].append({
                        'id': parent_id,
                        'label': f"[Отсутствует] {parent_id}",
                        'type': 'parent',
                        'version': 'Unknown',
                        'status': 'missing'
                    })
                    added_nodes.add(parent_id)

                    tree['edges'].append({
                        'from': mod_id,
                        'to': parent_id,
                        'label': 'translates (missing)'
                    })

        return tree


# ============================================================================
# ФУНКЦИИ ДЛЯ СОВМЕСТИМОСТИ С ДРУГИМИ МОДУЛЯМИ
# ============================================================================

def check_translation_statuses(mods_path: str, logger: Any | None = None) -> TranslationDependencyReport:
    """
    Удобная функция для проверки статуса всех переводов.

    Args:
        mods_path: Путь к папке с модами
        logger: Логгер

    Returns:
        TranslationDependencyReport с результатами
    """
    checker = TranslationStatusChecker(mods_path, logger)
    checker.load_mods()
    return checker.check_all_translations()


def get_translation_tree(mods_path: str, logger: Any | None = None) -> Dict[str, Any]:
    """
    Удобная функция для получения дерева зависимостей переводов.

    Args:
        mods_path: Путь к папке с модами
        logger: Логгер

    Returns:
        Словарь с деревом зависимостей
    """
    checker = TranslationStatusChecker(mods_path, logger)
    checker.load_mods()
    return checker.get_translation_tree()
