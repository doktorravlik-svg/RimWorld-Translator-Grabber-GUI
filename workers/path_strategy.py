# workers/path_strategy.py
"""
Стратегии определения путей сохранения для разных режимов перевода.

Использует паттерн «Стратегия» для разделения логики путей:
- InplaceStrategy: сохраняет файлы внутри папки мода
- SeparateStrategy: сохраняет файлы в output_folder с сохранением структуры
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

from utils.mod_version import get_mod_name


class PathStrategy(ABC):
    """
    Базовый класс стратегии путей.

    Определяет, как вычисляются пути сохранения файлов
    в зависимости от режима перевода.
    """

    @abstractmethod
    def get_mod_output_path(
        self,
        mod_path: str,
        target_lang: str,
        output_folder: Optional[str],
        defs_folders_list: list[str] | None = None
    ) -> str:
        """
        Определяет корневой путь вывода для мода.

        Args:
            mod_path: Путь к исходному моду
            target_lang: Целевой язык
            output_folder: Базовая папка вывода (может быть None)
            defs_folders_list: Список папок Defs (для определения версии)

        Returns:
            Путь к папке для сохранения файлов мода
        """
        pass

    @abstractmethod
    def get_save_path(self, original_path: str, mod_path: str, output_folder: str, mod_name: str) -> str:
        """
        Преобразует исходный путь в путь для сохранения.

        Args:
            original_path: Исходный путь к файлу
            mod_path: Путь к исходному моду
            output_folder: Папка вывода
            mod_name: Имя мода

        Returns:
            Путь для сохранения файла
        """
        pass

    @abstractmethod
    def should_create_backup(self) -> bool:
        """
        Определяет, нужно ли создавать резервные копии.

        Returns:
            True если нужно создавать бэкапы (для inplace режима)
        """
        pass


class InplacePathStrategy(PathStrategy):
    """
    Стратегия для режима inplace (изменение файлов внутри папки мода).
    """

    def get_mod_output_path(
        self,
        mod_path: str,
        target_lang: str,
        output_folder: Optional[str],
        defs_folders_list: list[str] | None = None
    ) -> str:
        """
        Возвращает путь с учётом LoadFolders.xml и существующих папок.

        Args:
            mod_path: Путь к моду
            target_lang: Целевой язык
            output_folder: Папка вывода (не используется для inplace)
            defs_folders_list: Список папок Defs для определения версии мода
        """
        from utils.languages_path_resolver import resolve_target_languages_path

        target_path, _ = resolve_target_languages_path(
            mod_path=mod_path,
            target_lang=target_lang,
            mode="inplace",
            defs_folders_list=defs_folders_list
        )
        return target_path

    def get_save_path(self, original_path: str, mod_path: str, output_folder: str, mod_name: str, target_lang: str = "Russian", source_lang: str = "English") -> str:
        """
        Для inplace режима заменяет папку исходного языка на целевой.

        Пример: .../1.6/Languages/English/Keyed/file.xml
                → .../1.6/Languages/Russian/Keyed/file.xml

        Args:
            original_path: Исходный путь к файлу
            mod_path: Путь к исходному моду
            output_folder: Папка вывода (не используется)
            mod_name: Имя мода (не используется)
            target_lang: Целевой язык (по умолчанию "Russian")
            source_lang: Исходный язык (по умолчанию "English")

        Returns:
            Путь с заменённым языком
        """
        # ✅ ИСПРАВЛЕНО: Правильная замена языка в пути (работает на Windows и Linux)
        # Разбиваем путь на компоненты и заменяем язык
        parts = original_path.replace("\\", "/").split("/")

        # Ищем компонент с исходным языком и заменяем его
        new_parts = []
        for part in parts:
            if part == source_lang:
                new_parts.append(target_lang)
            else:
                new_parts.append(part)

        result = "/".join(new_parts)
        return result.replace("/", os.sep)

    def should_create_backup(self) -> bool:
        """Для inplace режима бэкапы нужны."""
        return True


class SeparatePathStrategy(PathStrategy):
    """
    Стратегия для режима separate (сохранение в отдельную папку).

    Заменяет префикс папки мода на префикс output_folder.
    Сохраняет структуру: output_folder/ModName/Languages/target_lang/...
    """

    def get_mod_output_path(
        self,
        mod_path: str,
        target_lang: str,
        output_folder: Optional[str],
        defs_folders_list: list[str] | None = None
    ) -> str:
        """
        Определяет путь в output_folder.

        Args:
            mod_path: Путь к исходному моду
            target_lang: Целевой язык
            output_folder: Базовая папка вывода
            defs_folders_list: Список папок Defs (не используется для separate)

        Returns:
            Путь: output_folder/ModName/Languages/target_lang
        """
        if not output_folder:
            output_folder = os.path.join(os.path.dirname(mod_path), "Translated")
        mod_name = get_mod_name(mod_path)
        return os.path.join(output_folder, mod_name, "Languages", target_lang)

    def get_save_path(self, original_path: str, mod_path: str, output_folder: str, mod_name: str, target_lang: str = "Russian", source_lang: str = "English") -> str:
        """
        Заменяет префикс папки мода на префикс output_folder.

        ВАЖНО: Также заменяет имя папки исходного языка на целевой язык.
        Это критично для separate режима, чтобы RimWorld понимал,
        что файлы содержат перевод, а не оригинальный текст.

        Пример:
            original_path: C:/RimWorld/Mods/MyMod/Languages/English/Keyed/items.xml
            mod_path: C:/RimWorld/Mods/MyMod
            output_folder: C:/Output
            mod_name: MyMod
            target_lang: Russian
            source_lang: English
            result: C:/Output/MyMod/Languages/Russian/Keyed/items.xml

        Args:
            original_path: Исходный путь к файлу
            mod_path: Путь к исходному моду
            output_folder: Папка вывода
            mod_name: Имя мода
            target_lang: Целевой язык (по умолчанию "Russian")
            source_lang: Исходный язык (по умолчанию "English")

        Returns:
            Новый путь в output_folder с замененным языком
        """
        original_path = os.path.normpath(original_path)
        mod_path = os.path.normpath(mod_path)

        parts = original_path.replace("\\", "/").split("/")
        mod_parts = mod_path.replace("\\", "/").split("/")

        langs_index = -1
        for i in range(len(parts)):
            if parts[i] == "Languages" and i >= len(mod_parts) - 1:
                langs_index = i
                break

        if langs_index == -1:
            return original_path

        new_parts = []
        for i in range(langs_index, len(parts)):
            if parts[i] == source_lang:
                new_parts.append(target_lang)
            else:
                new_parts.append(parts[i])

        new_path = os.path.join(output_folder, mod_name, *new_parts)
        return new_path

    def should_create_backup(self) -> bool:
        """Для separate режима бэкапы не нужны (оригинал не изменяется)."""
        return False
