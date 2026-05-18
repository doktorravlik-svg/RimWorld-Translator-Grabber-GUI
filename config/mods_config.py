# mods_config.py - Управление списком активных модов RimWorld
from loguru import logger
import os
import sys

from lxml import etree
from verification.xml_parser import safe_parse_xml


def get_config_folder() -> str | None:
    """
    Получить путь к папке конфигурации RimWorld.

    Returns:
        Путь к папке Config или None
    """
    # Windows
    if sys.platform == "win32":
        return os.path.join(
            os.path.expandvars(r"%USERPROFILE%"),
            "AppData",
            "LocalLow",
            "Ludeon Studios",
            "RimWorld by Ludeon Studios",
            "Config",
        )
    # Linux
    elif sys.platform == "linux":
        # Проверяем $XDG_DATA_HOME (стандарт XDG Base Directory)
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            xdg_path = os.path.join(xdg_data_home, "unity3d", "Ludeon Studios", "RimWorld by Ludeon Studios", "Config")
            if os.path.exists(xdg_path):
                return xdg_path
        
        home = os.path.expanduser("~")
        paths = [
            os.path.join(
                home, ".config", "unity3d", "Ludeon Studios", "RimWorld by Ludeon Studios", "Config"
            ),
            os.path.join(home, ".steam", "steam", "steamapps", "common", "RimWorld", "Config"),
            # Proton/Wine Steam игры в Linux
            os.path.join(home, ".local", "share", "Steam", "steamapps", "common", "RimWorld", "Config"),
        ]
        for path in paths:
            if os.path.exists(path):
                return path
    # macOS
    elif sys.platform == "darwin":
        home = os.path.expanduser("~")
        return os.path.join(
            home,
            "Library",
            "Application Support",
            "Steam",
            "steamapps",
            "common",
            "RimWorld",
            "RimWorldMac.app",
            "Config",
        )
    return None


def get_mods_config_path() -> str | None:
    """
    Получить путь к файлу ModsConfig.xml.

    Returns:
        Путь к ModsConfig.xml или None
    """
    config_folder = get_config_folder()
    if config_folder:
        return os.path.join(config_folder, "ModsConfig.xml")
    return None


def get_active_mods() -> set[str]:
    """
    Получить множество packageId активных модов из ModsConfig.xml.

    Поддерживает оба формата:
    - RimWorld 1.5 и ниже: <modIds>
    - RimWorld 1.6 и выше: <activeMods>

    Returns:
        Множество packageId активных модов
    """
    active_mods = set()
    config_path = get_mods_config_path()

    if not config_path or not os.path.exists(config_path):
        return active_mods

    try:
        root = safe_parse_xml(config_path)
        if root is None:
            return active_mods

        # ✅ RimWorld 1.6+: Ищем activeMods
        active_mods_elem = root.find("activeMods")
        if active_mods_elem is not None:
            for li in active_mods_elem.findall("li"):
                if li.text:
                    active_mods.add(li.text.strip())

        # ✅ RimWorld 1.5 и ниже: Ищем modIds (для совместимости)
        mod_ids_elem = root.find("modIds")
        if mod_ids_elem is not None:
            for li in mod_ids_elem.findall("li"):
                if li.text:
                    active_mods.add(li.text.strip())

    except Exception as e:
        logger.error(f"Ошибка чтения ModsConfig.xml: {e}")

    return active_mods


def set_active_mods(active_mods: set[str]) -> bool:
        """
        Установить список активных модов в ModsConfig.xml.

        Args:
            active_mods: Множество packageId активных модов

        Returns:
            True при успехе
        """
        config_path = get_mods_config_path()
        if not config_path:
            return False

        try:
            # Создаём XML дерево
            root = etree.Element("ModsConfigData")

            version = etree.SubElement(root, "version")
            version.text = "1.5.4243 rev1204"

            mod_ids = etree.SubElement(root, "modIds")
            for mod_id in sorted(active_mods):
                li = etree.SubElement(mod_ids, "li")
                li.text = mod_id

            # ✅ ИСПРАВЛЕНО: Используем ElementTree для записи
            tree = etree.ElementTree(root)
            tree.write(config_path, encoding="utf-8", xml_declaration=True, pretty_print=True)

            return True

        except Exception as e:
            logger.error(f"Ошибка записи ModsConfig.xml: {e}")
            return False


def is_mod_active(mod_id: str) -> bool:
    """
    Проверить, активен ли мод.

    Args:
        mod_id: packageId мода

    Returns:
        True если мод активен
    """
    active_mods = get_active_mods()
    return mod_id in active_mods


def toggle_mod(mod_id: str, active: bool) -> bool:
    """
    Включить или отключить мод.

    Args:
        mod_id: packageId мода
        active: True для включения, False для отключения

    Returns:
        True при успехе
    """
    active_mods = get_active_mods()

    if active:
        active_mods.add(mod_id)
    else:
        active_mods.discard(mod_id)

    return set_active_mods(active_mods)


class ModsConfigManager:
    """
    Менеджер конфигурации модов.

    Предоставляет интерфейс для управления списком активных модов.
    """

    def __init__(self):
        self._active_mods: set[str] = set()
        self._load()

    def _load(self):
        """Загрузить список активных модов"""
        self._active_mods = get_active_mods()

    def save(self):
        """Сохранить список активных модов"""
        set_active_mods(self._active_mods)

    def is_active(self, mod_id: str) -> bool:
        """Проверить, активен ли мод"""
        return mod_id in self._active_mods

    def set_active(self, mod_id: str, active: bool):
        """Установить статус мода"""
        if active:
            self._active_mods.add(mod_id)
        else:
            self._active_mods.discard(mod_id)

    def toggle(self, mod_id: str):
        """Переключить статус мода"""
        if mod_id in self._active_mods:
            self._active_mods.discard(mod_id)
        else:
            self._active_mods.add(mod_id)

    def get_active(self) -> set[str]:
        """Получить множество активных модов"""
        return self._active_mods.copy()

    def get_count(self) -> int:
        """Получить количество активных модов"""
        return len(self._active_mods)

    def enable_all(self, mod_ids: list[str]):
        """Включить все указанные моды"""
        self._active_mods.update(mod_ids)

    def disable_all(self, mod_ids: list[str]):
        """Отключить все указанные моды"""
        self._active_mods -= set(mod_ids)

    def enable_only(self, mod_ids: list[str]):
        """Включить только указанные моды, остальные отключить"""
        self._active_mods = set(mod_ids)
