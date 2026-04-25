# verification/dependency_checker.py
"""
Модуль проверки зависимостей между модами RimWorld.

✅ ОБНОВЛЕНО: Поддержка официальных DLC — не помечаются как missing

Основные функции:
- DependencyChecker: класс проверки зависимостей
- check_mod_dependencies: проверка зависимостей одного мода
- verify_version_compatibility: проверка совместимости версий
- find_missing_dependencies: поиск отсутствующих зависимостей
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ✅ НОВОЕ: Импорт официальных DLC из центрального источника
try:
    from integrity.game_data_processor import DLC_PACKAGE_IDS, OFFICIAL_DLC
except ImportError:
    # Fallback если модуль недоступен
    OFFICIAL_DLC = ["Core", "Royalty", "Ideology", "Biotech", "Anomaly", "Odyssey"]
    DLC_PACKAGE_IDS = {
        "ludeon.rimworld": "Core",
        "ludeon.rimworld.royalty": "Royalty",
        "ludeon.rimworld.ideology": "Ideology",
        "ludeon.rimworld.biotech": "Biotech",
        "ludeon.rimworld.anomaly": "Anomaly",
        "ludeon.rimworld.odyssey": "Odyssey",
    }


def _is_official_dlc(package_id: str) -> bool:
    """Проверяет, является ли packageId официальным DLC"""
    dep_id_lower = package_id.lower()
    return any(dep_id_lower == pid.lower() for pid in DLC_PACKAGE_IDS) or any(
        dep_id_lower == f"ludeon.rimworld.{dlc.lower()}" for dlc in OFFICIAL_DLC
    )


# ============================================================================
# ТИПЫ ДАННЫХ
# ============================================================================


class DependencySeverity(Enum):
    """Серьёзность проблемы с зависимостью"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DependencyType(Enum):
    """Тип зависимости"""

    REQUIRED = "required"
    OPTIONAL = "optional"
    SOFT = "soft"
    INCOMPATIBLE = "incompatible"


@dataclass
class DependencyInfo:
    """Информация о зависимости мода"""

    package_id: str
    display_name: str
    dependency_type: DependencyType
    required_version: str | None = None
    installed_version: str | None = None
    is_installed: bool = False
    is_compatible: bool = True


@dataclass
class DependencyCheckResult:
    """Результат проверки одной зависимости"""

    package_id: str
    severity: DependencySeverity
    dependency_type: DependencyType
    message: str
    is_resolved: bool = True
    installed_version: str | None = None
    required_version: str | None = None


@dataclass
class ModDependencyReport:
    """Отчет о зависимостях одного мода"""

    mod_id: str
    mod_name: str
    mod_path: str
    dependencies: list[DependencyCheckResult] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)
    incompatible_versions: list[str] = field(default_factory=list)
    is_valid: bool = True
    error_count: int = 0
    warning_count: int = 0


# ============================================================================
# КЛАСС DEPENDENCY CHECKER
# ============================================================================


class DependencyChecker:
    """
    Класс для проверки зависимостей между модами RimWorld.

    Поддерживает:
    - Поиск отсутствующих зависимостей
    - Проверку совместимости версий
    - Определение типа зависимости (обязательная/опциональная)
    - Генерацию отчетов
    """

    def __init__(self, mods_path: str, logger: logging.Logger | None = None):
        self.mods_path = mods_path
        self.logger = logger
        self._mods_cache: dict[str, dict] = {}

        # Приоритетный список версий для поиска
        self.version_priority = ["1.6", "1.5", "1.4", "1.3", "1.2", "1.1", "1.0"]

    # =========================================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # =========================================================================

    def load_mods(self) -> dict[str, dict]:
        """
        Загружает информацию обо всех модах в директории.

        Returns:
            Словарь {packageId: mod_info}
        """
        from scanner.mod_scanner import find_about_xml, parse_about_xml

        if not os.path.exists(self.mods_path):
            if self.logger:
                self.logger.error(f"Путь к модам не существует: {self.mods_path}")
            return {}

        for item in os.listdir(self.mods_path):
            mod_path = os.path.join(self.mods_path, item)
            if not os.path.isdir(mod_path):
                continue

            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            about_data = parse_about_xml(about_path)
            mod_id = about_data.get("mod_id")

            if not mod_id:
                continue

            self._mods_cache[mod_id] = {
                "mod_id": mod_id,
                "mod_name": about_data.get("name", "Unknown"),
                "mod_path": mod_path,
                "about_path": about_path,
                "about_data": about_data,
                "version": about_data.get("version"),
                "dependencies": about_data.get("dependencies", []),
                "supported_languages": about_data.get("supported_languages", []),
                "target_mod_id": about_data.get("target_mod_id"),
                "target_content_creator": about_data.get("target_content_creator"),
                "author": about_data.get("author"),
            }

        if self.logger:
            self.logger.info(f"Загружено {len(self._mods_cache)} модов")

        return self._mods_cache

    def check_mod_dependencies(self, mod_id: str) -> ModDependencyReport:
        """
        Проверяет зависимости одного мода.

        Args:
            mod_id: ID мода (packageId)

        Returns:
            ModDependencyReport с результатами проверки
        """
        if mod_id not in self._mods_cache:
            return ModDependencyReport(
                mod_id=mod_id, mod_name="Unknown", mod_path="", is_valid=False
            )

        mod_info = self._mods_cache[mod_id]
        report = ModDependencyReport(
            mod_id=mod_id, mod_name=mod_info["mod_name"], mod_path=mod_info["mod_path"]
        )

        dependencies = mod_info.get("dependencies", [])
        if not dependencies:
            return report

        for dep in dependencies:
            # Обрабатываем разные форматы зависимостей
            if isinstance(dep, dict):
                dep_id = dep.get("packageId", "")
                required_version = dep.get("requiredVersion")
                is_required = dep.get("isRequired", True)
            else:
                dep_id = str(dep)
                required_version = None
                is_required = True

            if not dep_id:
                continue

            # ✅ НОВОЕ: Проверяем является ли зависимость официальным DLC
            if _is_official_dlc(dep_id):
                # DLC не считаются "missing" — помечаем как INFO
                result = DependencyCheckResult(
                    package_id=dep_id,
                    severity=DependencySeverity.INFO,
                    dependency_type=DependencyType.REQUIRED,
                    message=f"Официальное DLC: {DLC_PACKAGE_IDS.get(dep_id.lower(), dep_id)}",
                    is_resolved=True,
                    required_version=required_version,
                )
                report.dependencies.append(result)
                continue

            # Проверяем наличие мода
            if dep_id not in self._mods_cache:
                severity = DependencySeverity.ERROR if is_required else DependencySeverity.WARNING
                dependency_type = (
                    DependencyType.REQUIRED if is_required else DependencyType.OPTIONAL
                )

                result = DependencyCheckResult(
                    package_id=dep_id,
                    severity=severity,
                    dependency_type=dependency_type,
                    message=f"Отсутствует {'обязательный' if is_required else 'опциональный'} мод: {dep_id}",
                    is_resolved=False,
                    required_version=required_version,
                )
                report.dependencies.append(result)
                report.missing_dependencies.append(dep_id)

                if is_required:
                    report.error_count += 1
                    report.is_valid = False
                else:
                    report.warning_count += 1
            else:
                # Мод установлен - проверяем версию
                dep_mod = self._mods_cache[dep_id]
                installed_version = dep_mod.get("version")

                if required_version and installed_version:
                    is_compatible = self._check_version_compatibility(
                        installed_version, required_version
                    )

                    if not is_compatible:
                        result = DependencyCheckResult(
                            package_id=dep_id,
                            severity=DependencySeverity.ERROR,
                            dependency_type=DependencyType.REQUIRED,
                            message=f"Несовместимая версия: требуется {required_version}, установлена {installed_version}",
                            is_resolved=False,
                            installed_version=installed_version,
                            required_version=required_version,
                        )
                        report.dependencies.append(result)
                        report.incompatible_versions.append(dep_id)
                        report.error_count += 1
                        report.is_valid = False

        return report

    def check_all_dependencies(self) -> list[ModDependencyReport]:
        """
        Проверяет зависимости всех модов.

        Returns:
            Список отчетов по каждому моду
        """
        reports = []

        for mod_id in self._mods_cache:
            report = self.check_mod_dependencies(mod_id)
            reports.append(report)

        return reports

    def find_missing_dependencies(self) -> dict[str, list[str]]:
        """
        Находит все отсутствующие зависимости.

        Returns:
            Словарь {mod_id: [список отсутствующих зависимостей]}
        """
        missing = {}

        for mod_id in self._mods_cache:
            mod_info = self._mods_cache[mod_id]
            dependencies = mod_info.get("dependencies", [])
            mod_missing = []

            for dep in dependencies:
                if isinstance(dep, dict):
                    dep_id = dep.get("packageId", "")
                    is_required = dep.get("isRequired", True)
                else:
                    dep_id = str(dep)
                    is_required = True

                if not dep_id:
                    continue

                # ✅ НОВОЕ: Пропускаем официальные DLC
                if _is_official_dlc(dep_id):
                    continue

                if dep_id not in self._mods_cache and is_required:
                    mod_missing.append(dep_id)

            if mod_missing:
                missing[mod_id] = mod_missing

        return missing

    def find_circular_dependencies(self) -> list[list[str]]:
        """
        Находит циклические зависимости между модами.

        Returns:
            Список циклов (каждый цикл - список mod_id)
        """
        cycles = []
        visited = set()
        path = []

        def visit(mod_id: str) -> bool:
            if mod_id in path:
                # Найден цикл
                cycle_start = path.index(mod_id)
                cycle = path[cycle_start:] + [mod_id]
                cycles.append(cycle)
                return True

            if mod_id in visited:
                return False

            visited.add(mod_id)
            path.append(mod_id)

            mod_info = self._mods_cache.get(mod_id, {})
            dependencies = mod_info.get("dependencies", [])

            for dep in dependencies:
                if isinstance(dep, dict):
                    dep_id = dep.get("packageId")
                else:
                    dep_id = str(dep)

                if dep_id and dep_id in self._mods_cache:
                    visit(dep_id)

            path.pop()
            return False

        for mod_id in self._mods_cache:
            visit(mod_id)

        return cycles

    def get_dependency_tree(
        self, mod_id: str, depth: int = 0, max_depth: int = 5
    ) -> dict[str, Any]:
        """
        Строит дерево зависимостей для мода.

        Args:
            mod_id: ID мода
            depth: Текущая глубина
            max_depth: Максимальная глубина

        Returns:
            Словарь с деревом зависимостей
        """
        if depth > max_depth or mod_id not in self._mods_cache:
            return {}

        mod_info = self._mods_cache[mod_id]
        dependencies = mod_info.get("dependencies", [])

        deps = []
        for dep in dependencies:
            if isinstance(dep, dict):
                dep_id = dep.get("packageId")
            else:
                dep_id = str(dep)

            if dep_id and dep_id in self._mods_cache:
                dep_info = self._mods_cache[dep_id]
                deps.append(
                    {
                        "mod_id": dep_id,
                        "mod_name": dep_info.get("mod_name", "Unknown"),
                        "version": dep_info.get("version"),
                        "dependencies": self.get_dependency_tree(dep_id, depth + 1, max_depth).get(
                            "dependencies", []
                        ),
                    }
                )

        return {
            "mod_id": mod_id,
            "mod_name": mod_info.get("mod_name", "Unknown"),
            "version": mod_info.get("version"),
            "dependencies": deps,
        }

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def _check_version_compatibility(self, installed: str, required: str) -> bool:
        """
        Проверяет совместимость версий.

        Args:
            installed: Установленная версия
            required: Требуемая версия

        Returns:
            True если версии совместимы
        """
        # Простая проверка - точное совпадение
        # Можно расширить для поддержки диапазонов (>=1.2, <2.0)
        return installed == required

    def is_valid_version(self, version: str) -> bool:
        """
        Проверяет корректность формата версии.

        Args:
            version: Строка версии

        Returns:
            True если формат версии корректен
        """
        try:
            parts = version.split(".")
            if len(parts) < 2:
                return False
            for part in parts:
                int(part)
            return True
        except (ValueError, AttributeError):
            return False

    def get_mods_by_author(self, author: str) -> list[dict]:
        """
        Возвращает список модов указанного автора.

        Args:
            author: Имя автора

        Returns:
            Список модов автора
        """
        return [
            mod_info
            for mod_info in self._mods_cache.values()
            if mod_info.get("author", "").lower() == author.lower()
        ]

    def get_mods_by_language(self, language: str) -> list[dict]:
        """
        Возвращает список модов с указанным языком.

        Args:
            language: Код языка

        Returns:
            Список модов с языком
        """
        return [
            mod_info
            for mod_info in self._mods_cache.values()
            if language in mod_info.get("supported_languages", [])
        ]

    def get_stats(self) -> dict[str, int]:
        """
        Возвращает статистику по модам.

        Returns:
            Словарь со статистикой
        """
        total_mods = len(self._mods_cache)
        translation_mods = 0
        mods_with_deps = 0

        for mod_info in self._mods_cache.values():
            # Определяем переводные моды
            target_mod_id = mod_info.get("target_mod_id")
            target_content_creator = mod_info.get("target_content_creator")
            package_id = mod_info.get("mod_id", "").lower()

            if target_mod_id or target_content_creator or "translation" in package_id:
                translation_mods += 1

            # Моды с зависимостями
            if mod_info.get("dependencies"):
                mods_with_deps += 1

        return {
            "total_mods": total_mods,
            "translation_mods": translation_mods,
            "regular_mods": total_mods - translation_mods,
            "mods_with_dependencies": mods_with_deps,
        }


# ============================================================================
# ФУНКЦИИ ВЫСОКОГО УРОВНЯ
# ============================================================================


def check_mod_dependencies(
    mods_path: str, mod_id: str, logger: logging.Logger | None = None
) -> ModDependencyReport:
    """
    Проверяет зависимости одного мода.

    Args:
        mods_path: Путь к папке модов
        mod_id: ID мода
        logger: Опциональный логгер

    Returns:
        ModDependencyReport с результатами проверки
    """
    checker = DependencyChecker(mods_path, logger)
    checker.load_mods()
    return checker.check_mod_dependencies(mod_id)


def verify_version_compatibility(installed: str, required: str) -> tuple[bool, str]:
    """
    Проверяет совместимость версий.

    Args:
        installed: Установленная версия
        required: Требуемая версия

    Returns:
        (совместимость, сообщение)
    """
    # Простая проверка
    if installed == required:
        return True, "Версии совместимы"

    # Проверяем мажорные версии
    try:
        inst_major = int(installed.split(".", maxsplit=1)[0])
        req_major = int(required.split(".", maxsplit=1)[0])

        if inst_major != req_major:
            return False, f"Несовместимость мажорных версий: {installed} vs {required}"

        # Проверяем минорные версии
        if len(installed.split(".")) > 1 and len(required.split(".")) > 1:
            inst_minor = int(installed.split(".")[1])
            req_minor = int(required.split(".")[1])

            if inst_minor < req_minor:
                return False, f"Устаревшая версия: {installed}, требуется {required}"

    except (ValueError, IndexError):
        return False, f"Некорректный формат версии: {installed} или {required}"

    return True, "Версии совместимы"


def find_missing_dependencies(
    mods_path: str, logger: logging.Logger | None = None
) -> dict[str, list[str]]:
    """
    Находит все отсутствующие зависимости.

    Args:
        mods_path: Путь к папке модов
        logger: Опциональный логгер

    Returns:
        Словарь {mod_id: [список отсутствующих зависимостей]}
    """
    checker = DependencyChecker(mods_path, logger)
    checker.load_mods()
    return checker.find_missing_dependencies()


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Тестирование dependency_checker")
    print("=" * 60)

    # Тест структуры данных
    print("\n[ТЕСТ] Структуры данных:")

    dep_info = DependencyInfo(
        package_id="test.mod",
        display_name="Test Mod",
        dependency_type=DependencyType.REQUIRED,
        required_version="1.0.0",
        is_installed=False,
    )
    print(f"  DependencyInfo: {dep_info.package_id}")

    check_result = DependencyCheckResult(
        package_id="test.mod",
        severity=DependencySeverity.ERROR,
        dependency_type=DependencyType.REQUIRED,
        message="Тестовая ошибка",
        is_resolved=False,
    )
    print(f"  DependencyCheckResult: {check_result.package_id}")

    # Тест DependencyChecker
    print("\n[ТЕСТ] DependencyChecker:")
    checker = DependencyChecker("C:/Test/Mods")
    print(f"  Создан checker для пути: {checker.mods_path}")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
