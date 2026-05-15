# paths_config.py
"""
Централизованное управление путями для всех модулей проекта.

Этот модуль предоставляет единый интерфейс для получения путей к папкам модов
для grabber, translator, editor и других компонентов.

✅ РЕШАЕТ ПРОБЛЕМУ: Модуль фильтров не подхватывает папку модов
✅ ИСПРАВЛЕНО: Использует общий lock с ConfigManager для предотвращения гонок данных

Поддерживает:
- platformdirs для автоматического определения стандартных путей
- Ручную настройку через gui_config.json
- Fallback пути по умолчанию
"""

import json
import os
import shutil
import tempfile
import threading
from typing import Literal
from loguru import logger

# ✅ ИСПРАВЛЕНО: Импортируем общий lock для предотвращения гонок данных
from utils.locks import config_lock

# Импорт platformdirs с fallback
try:
    from platformdirs import PlatformDirs

    HAS_PLATFORMDIRS = True
except ImportError:
    HAS_PLATFORMDIRS = False


# Типы модулей для получения путей
ModuleType = Literal["grabber", "translator", "editor", "verifier", "default"]


class PathsConfig:
    """
    Централизованный менеджер путей для всех модулей.

    Пример использования:
        paths = PathsConfig()
        mods_path = paths.get_mods_path("grabber")
        output_path = paths.get_output_path("translator")
        game_path = paths.get_game_path()
        backup_path = paths.get_backup_folder()
    """

    DEFAULT_CONFIG_FILE = "gui_config.json"
    APP_NAME = "RimWorldTranslator"
    APP_AUTHOR = "RimProg"

    def __init__(self, config_file: str | None = None):
        """
        Инициализация менеджера путей.

        Args:
            config_file: Путь к файлу конфигурации (по умолчанию gui_config.json)
        """
        self.config_file: str = config_file or self.DEFAULT_CONFIG_FILE
        self.config = self._load_config()
        self.config = self._migrate_config(self.config)
        self._initialize_paths()

    def _load_config(self) -> dict:
        """Загружает конфигурацию из JSON файла"""
        try:
            with open(self.config_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"⚠️ Конфигурационный файл не найден: {self.config_file}")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            # ✅ ИСПРАВЛЕНО: Создаём бэкап повреждённого файла
            backup_path = f"{self.config_file}.bak"
            try:
                shutil.copy2(self.config_file, backup_path)
                logger.warning(f"⚠️ Повреждённый конфиг создан бэкап: {backup_path}")
            except Exception:
                pass
            logger.error(f"⚠️ Ошибка парсинга JSON: {e}")
            return self._get_default_config()

    def _migrate_config(self, config: dict) -> dict:
        """
        Миграция старых конфигов к новому формату.

        Копирует старые поля в новые, если они существуют.
        """
        # Если есть mods_folder, но нет paths.default_mods
        if config.get("mods_folder") and not config.get("paths", {}).get("default_mods"):
            config.setdefault("paths", {})["default_mods"] = config["mods_folder"]

        # Если есть output_folder, но нет paths.output_overrides
        if config.get("output_folder") and not config.get("paths", {}).get("output_overrides"):
            config.setdefault("paths", {}).setdefault("output_overrides", {})

        # Если есть game_path, но нет paths.game_path
        if config.get("game_path") and not config.get("paths", {}).get("game_path"):
            config.setdefault("paths", {})["game_path"] = config["game_path"]

        return config

    def _get_default_config(self) -> dict:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "mods_folder": "",
            "output_folder": "",
            "game_path": "",
            "presets": {},
            "paths": {
                "default_mods": "",
                "game_path": "",
                "temp_folder": "",
                "backup_folder": "",
                "cache_folder": "",
                "module_overrides": {},
                "output_overrides": {},
            },
        }

    def _initialize_paths(self):
        """Инициализирует пути из конфигурации"""
        # Базовые пути из корня конфига (для обратной совместимости)
        self.base_mods_folder = self.config.get("mods_folder", "")
        self.base_output_folder = self.config.get("output_folder", "")
        self.base_game_path = self.config.get("game_path", "")
        self.presets = self.config.get("presets", {})

        # Новые централизованные настройки путей
        paths_config = self.config.get("paths", {})
        self.default_mods = paths_config.get("default_mods", self.base_mods_folder)
        self.game_path = paths_config.get("game_path", self.base_game_path)
        self.temp_folder = paths_config.get("temp_folder", "")
        self.backup_folder = paths_config.get("backup_folder", "")
        self.cache_folder = paths_config.get("cache_folder", "")
        self.module_overrides = paths_config.get("module_overrides", {})
        self.output_overrides = paths_config.get("output_overrides", {})

    # ==================== МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ПУТЕЙ ====================

    def get_mods_path(self, module: ModuleType = "default") -> str:
        """
        Получает путь к папке модов для указанного модуля.

        Логика приоритетов:
        1. Индивидуальное переопределение для модуля (если есть)
        2. Путь по умолчанию (default_mods)
        3. Устаревший mods_folder (для обратной совместимости)

        Args:
            module: Тип модуля (grabber, translator, editor, verifier, default)

        Returns:
            Путь к папке модов
        """
        # 1. Проверяем индивидуальное переопределение
        if module in self.module_overrides:
            override_path = self.module_overrides[module]
            if override_path:  # Не пустая строка
                return override_path

        # 2. Возвращаем путь по умолчанию
        if self.default_mods:
            return self.default_mods

        # 3. Обратная совместимость
        return self.base_mods_folder

    def get_output_path(self, module: ModuleType = "default") -> str:
        """
        Получает выходную папку для указанного модуля.

        Args:
            module: Тип модуля

        Returns:
            Путь к выходной папке
        """
        # Проверяем индивидуальные настройки вывода
        if module in self.output_overrides:
            override_path = self.output_overrides[module]
            if override_path:
                return override_path

        # Путь по умолчанию
        if self.base_output_folder:
            return self.base_output_folder

        # По умолчанию: подпапка Translated в папке модов
        mods_path = self.get_mods_path(module)
        if mods_path:
            return os.path.join(mods_path, "Translated")

        return ""

    def get_game_path(self) -> str:
        """
        Получает путь к игре RimWorld.

        Returns:
            Путь к папке с игрой или пустая строка
        """
        return self.game_path or self.base_game_path

    def get_temp_folder(self) -> str:
        """
        Получает временную папку.

        Приоритеты:
        1. Из конфига (paths.temp_folder)
        2. platformdirs (user_cache_path)
        3. Системная temp папка

        Returns:
            Путь к временной папке
        """
        # 1. Из конфига
        if self.temp_folder:
            return self.temp_folder

        # 2. platformdirs
        if HAS_PLATFORMDIRS:
            dirs = PlatformDirs(self.APP_NAME, self.APP_AUTHOR)
            return str(dirs.user_cache_path / "temp")

        # 3. Fallback - системная temp
        return tempfile.gettempdir()

    def get_backup_folder(self) -> str:
        """
        Получает папку для резервных копий.

        Приоритеты:
        1. Из конфига (paths.backup_folder)
        2. platformdirs (user_data_path / backups)
        3. Fallback (~/.rimworld_translator/backups)

        Returns:
            Путь к папке бэкапов
        """
        # 1. Из конфига
        if self.backup_folder:
            return self.backup_folder

        # 2. platformdirs
        if HAS_PLATFORMDIRS:
            dirs = PlatformDirs(self.APP_NAME, self.APP_AUTHOR)
            return str(dirs.user_data_path / "backups")

        # 3. Fallback
        return os.path.join(os.path.expanduser("~"), f".{self.APP_NAME.lower()}", "backups")

    def get_cache_folder(self) -> str:
        """
        Получает папку для кэша.

        Приоритеты:
        1. Из конфига (paths.cache_folder)
        2. platformdirs (user_cache_path)
        3. Fallback (~/.rimworld_translator/cache)

        Returns:
            Путь к папке кэша
        """
        # 1. Из конфига
        if self.cache_folder:
            return self.cache_folder

        # 2. platformdirs
        if HAS_PLATFORMDIRS:
            dirs = PlatformDirs(self.APP_NAME, self.APP_AUTHOR)
            return str(dirs.user_cache_path)

        # 3. Fallback
        return os.path.join(os.path.expanduser("~"), f".{self.APP_NAME.lower()}", "cache")

    def get_preset_path(self, preset_name: str) -> str:
        """
        Получает путь из пресета по названию.

        Args:
            preset_name: Название пресета (Steam Workshop, Local Mods, Custom)

        Returns:
            Путь из пресета или пустая строка
        """
        return self.presets.get(preset_name, "")

    def get_available_presets(self) -> list[str]:
        """Возвращает список доступных пресетов"""
        return list(self.presets.keys())

    # ==================== МЕТОДЫ ДЛЯ УСТАНОВКИ ПУТЕЙ ====================

    def set_mods_path(self, path: str, module: ModuleType = "default", save: bool = False):
        """
        Устанавливает путь к папке модов.

        Args:
            path: Новый путь
            module: Тип модуля (default для всех)
            save: Сохранить изменения в файл
        """
        if module == "default":
            # Устанавливаем для всех модулей
            self.default_mods = path
            self.config["paths"] = self.config.get("paths", {})
            self.config["paths"]["default_mods"] = path
        else:
            # Индивидуальное переопределение
            self.module_overrides[module] = path
            self.config["paths"] = self.config.get("paths", {})
            self.config["paths"]["module_overrides"] = self.module_overrides

        if save:
            self.save_config()

    def set_output_path(self, path: str, save: bool = False):
        """
        Устанавливает выходную папку.

        Args:
            path: Новый путь
            save: Сохранить изменения в файл
        """
        self.base_output_folder = path
        self.config["output_folder"] = path

        if save:
            self.save_config()

    def set_game_path(self, path: str, save: bool = False):
        """
        Устанавливает путь к игре.

        Args:
            path: Новый путь
            save: Сохранить изменения в файл
        """
        self.game_path = path
        self.config["game_path"] = path
        self.config.setdefault("paths", {})["game_path"] = path

        if save:
            self.save_config()

    def set_backup_folder(self, path: str, save: bool = False):
        """
        Устанавливает папку для бэкапов.

        Args:
            path: Новый путь
            save: Сохранить изменения в файл
        """
        self.backup_folder = path
        self.config.setdefault("paths", {})["backup_folder"] = path

        if save:
            self.save_config()

    # ==================== СЛУЖЕБНЫЕ МЕТОДЫ ====================

    def save_config(self):
        """Сохраняет текущую конфигурацию в файл с блокировкой"""
        # ✅ ИСПРАВЛЕНО: Используем общий lock для предотвращения гонок данных
        with config_lock:
            try:
                with open(self.config_file, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
            except Exception as e:
                logger.error(f"⚠️ Ошибка сохранения конфигурации: {e}")

    def reload_config(self):
        """Перезагружает конфигурацию из файла"""
        self.config = self._load_config()
        self.config = self._migrate_config(self.config)
        self._initialize_paths()

    def is_module_path_overridden(self, module: ModuleType) -> bool:
        """
        Проверяет, переопределён ли путь для модуля.

        Args:
            module: Тип модуля

        Returns:
            True если путь переопределён
        """
        return module in self.module_overrides and bool(self.module_overrides[module])

    def get_all_paths_summary(self) -> dict:
        """
        Возвращает сводку всех путей.

        Returns:
            Словарь с путями для всех модулей
        """
        return {
            "default_mods": self.default_mods,
            "default_output": self.base_output_folder,
            "game_path": self.game_path,
            "temp_folder": self.get_temp_folder(),
            "backup_folder": self.get_backup_folder(),
            "cache_folder": self.get_cache_folder(),
            "modules": {
                "grabber": self.get_mods_path("grabber"),
                "translator": self.get_mods_path("translator"),
                "editor": self.get_mods_path("editor"),
                "verifier": self.get_mods_path("verifier"),
            },
            "presets": self.presets,
            "overrides": self.module_overrides,
            "platformdirs_available": HAS_PLATFORMDIRS,
        }

    def __str__(self) -> str:
        """Строковое представление конфигурации"""
        summary = self.get_all_paths_summary()
        lines = [
            "PathsConfig:",
            f"  Default Mods: {summary['default_mods']}",
            f"  Default Output: {summary['default_output']}",
            f"  Game Path: {summary['game_path']}",
            f"  Temp Folder: {summary['temp_folder']}",
            f"  Backup Folder: {summary['backup_folder']}",
            f"  Cache Folder: {summary['cache_folder']}",
            f"  PlatformDirs: {'✅' if summary['platformdirs_available'] else '❌'}",
            "  Modules:",
        ]
        for module, path in summary["modules"].items():
            override = " (override)" if self.is_module_path_overridden(module) else ""
            lines.append(f"    {module}: {path}{override}")
        if summary["presets"]:
            lines.append("  Presets:")
            for name, path in summary["presets"].items():
                lines.append(f"    {name}: {path}")
        return "\n".join(lines)


# ✅ Глобальный экземпляр для использования в других модулях
_paths_config_instance: PathsConfig | None = None


def get_paths_config() -> PathsConfig:
    """
    Получает глобальный экземпляр PathsConfig (Singleton).

    Returns:
        Экземпляр PathsConfig
    """
    global _paths_config_instance
    if _paths_config_instance is None:
        _paths_config_instance = PathsConfig()
    return _paths_config_instance


def reset_paths_config():
    """Сбрасывает глобальный экземпляр (для тестов)"""
    global _paths_config_instance
    _paths_config_instance = None


# ✅ Функции-помощники для быстрого доступа
def get_mods_path(module: ModuleType = "default") -> str:
    """Быстрое получение пути к папке модов"""
    return get_paths_config().get_mods_path(module)


def get_output_path(module: ModuleType = "default") -> str:
    """Быстрое получение выходной папки"""
    return get_paths_config().get_output_path(module)


def get_game_path() -> str:
    """Быстрое получение пути к игре"""
    return get_paths_config().get_game_path()


def get_temp_folder() -> str:
    """Быстрое получение временной папки"""
    return get_paths_config().get_temp_folder()


def get_backup_folder() -> str:
    """Быстрое получение папки бэкапов"""
    return get_paths_config().get_backup_folder()


def get_cache_folder() -> str:
    """Быстрое получение папки кэша"""
    return get_paths_config().get_cache_folder()


def set_mods_path(path: str, module: ModuleType = "default", save: bool = False):
    """Быстрая установка пути к папке модов"""
    get_paths_config().set_mods_path(path, module, save)


def set_game_path(path: str, save: bool = False):
    """Быстрая установка пути к игре"""
    get_paths_config().set_game_path(path, save)


if __name__ == "__main__":
    # Тестирование PathsConfig...
    logger.info("Тестирование PathsConfig...")
    logger.info("=" * 60)

    paths = PathsConfig()
    logger.info(paths)

    logger.info("\n" + "=" * 60)
    logger.info("Пути для модулей:")
    logger.info(f"  Grabber: {paths.get_mods_path('grabber')}")
    logger.info(f"  Translator: {paths.get_mods_path('translator')}")
    logger.info(f"  Editor: {paths.get_mods_path('editor')}")
    logger.info(f"  Verifier: {paths.get_mods_path('verifier')}")

    logger.info("\n" + "=" * 60)
    logger.info("Дополнительные пути:")
    logger.info(f"  Game Path: {paths.get_game_path()}")
    logger.info(f"  Temp Folder: {paths.get_temp_folder()}")
    logger.info(f"  Backup Folder: {paths.get_backup_folder()}")
    logger.info(f"  Cache Folder: {paths.get_cache_folder()}")
    logger.info(f"  PlatformDirs: {'✅ Доступен' if HAS_PLATFORMDIRS else '❌ Не установлен'}")
