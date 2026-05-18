# utils/mod_cache.py
"""
Кэширование списка модов для ускорения загрузки.
Сохраняет информацию о модах в JSON файл и использует его при повторном запуске.
"""

import json
import os
import time
from typing import Optional


class ModsCache:
    """
    Кэш списка модов.

    Хранит информацию о модах:
    - Список модов с их путями
    - Время последнего сканирования
    - Время изменения папки модов (mtime)
    """

    CACHE_FILENAME = ".mods_cache.json"
    CACHE_TTL = 300  # Время жизни кэша: 5 минут

    def __init__(self, cache_file: Optional[str] = None):
        """
        Args:
            cache_file: Путь к файлу кэша (если None, используется .mods_cache.json в папке модов)
        """
        self.cache_file = cache_file
        self.cache = {
            "mods": [],
            "last_scan": 0,
            "folder_mtime": 0,
            "folder": "",
        }

    def _get_cache_path(self, mods_folder: str) -> str:
        """Возвращает путь к файлу кэша"""
        if self.cache_file:
            return self.cache_file
        return os.path.join(mods_folder, self.CACHE_FILENAME)

    def load(self, mods_folder: str) -> Optional[list]:
        """
        Загружает кэш если он валиден.

        Args:
            mods_folder: Путь к папке модов

        Returns:
            Список модов из кэша или None если кэш невалиден
        """
        if not os.path.exists(mods_folder):
            return None

        cache_path = self._get_cache_path(mods_folder)
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                self.cache = json.load(f)

            # Проверяем валидность кэша
            current_mtime = os.path.getmtime(mods_folder)
            cache_age = time.time() - self.cache.get("last_scan", 0)

            # Кэш валиден если:
            # 1. Папка не изменялась
            # 2. Кэш моложе TTL
            if (
                self.cache.get("folder") == mods_folder
                and self.cache.get("folder_mtime") == current_mtime
                and cache_age < self.CACHE_TTL
            ):
                return self.cache.get("mods", [])

        except (json.JSONDecodeError, OSError) as e:
            print(f"Ошибка загрузки кэша: {e}")

        return None

    def save(self, mods_folder: str, mods_list: list) -> None:
        """
        Сохраняет список модов в кэш.

        Args:
            mods_folder: Путь к папке модов
            mods_list: Список модов для сохранения
        """
        if not os.path.exists(mods_folder):
            return

        cache_path = self._get_cache_path(mods_folder)

        try:
            self.cache = {
                "mods": mods_list,
                "last_scan": time.time(),
                "folder_mtime": os.path.getmtime(mods_folder),
                "folder": mods_folder,
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)

        except OSError as e:
            print(f"Ошибка сохранения кэша: {e}")

    def clear(self, mods_folder: str) -> None:
        """Очищает кэш"""
        cache_path = self._get_cache_path(mods_folder)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass

    def is_valid(self, mods_folder: str) -> bool:
        """Проверяет валидность кэша"""
        return self.load(mods_folder) is not None

    def get_stats(self) -> dict:
        """Возвращает статистику кэша"""
        return {
            "cached_mods": len(self.cache.get("mods", [])),
            "last_scan": self.cache.get("last_scan", 0),
            "cache_age": time.time() - self.cache.get("last_scan", 0) if self.cache.get("last_scan") else 0,
            "is_valid": bool(self.cache.get("mods")),
        }


# Глобальный экземпляр кэша
_mods_cache = ModsCache()


def get_mods_cache() -> ModsCache:
    """Возвращает глобальный экземпляр кэша модов"""
    return _mods_cache


def scan_mods_with_cache(mods_folder: str, force_rescan: bool = False) -> list:
    """
    Сканирует папку модов с использованием кэша.

    Args:
        mods_folder: Путь к папке модов
        force_rescan: Принудительное пересканирование (игнорирование кэша)

    Returns:
        Список путей к модам
    """
    cache = get_mods_cache()

    # Пробуем загрузить из кэша
    if not force_rescan:
        cached_mods = cache.load(mods_folder)
        if cached_mods is not None:
            return cached_mods

    # Сканируем папку
    mods_list = _scan_mods_direct(mods_folder)

    # Сохраняем в кэш
    cache.save(mods_folder, mods_list)

    return mods_list


def _scan_mods_direct(mods_folder: str) -> list:
    """Прямое сканирование папки модов (без кэша)"""
    mods = []

    if not os.path.exists(mods_folder):
        return mods

    try:
        for item in os.listdir(mods_folder):
            item_path = os.path.join(mods_folder, item)
            if os.path.isdir(item_path):
                # Проверяем наличие About.xml
                about_path = os.path.join(item_path, "About", "About.xml")
                if os.path.exists(about_path):
                    mods.append(item_path)
    except OSError as e:
        print(f"Ошибка сканирования папки: {e}")

    return mods
