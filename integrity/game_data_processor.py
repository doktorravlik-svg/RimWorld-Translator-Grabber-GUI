# game_data_processor.py
"""
Модуль для загрузки и обработки официальных данных игры RimWorld.

✅ ОБНОВЛЕНО: Поддержка .tar архивов в RimWorld 1.6
"""

import os
import re
import tarfile
import xml.etree.ElementTree as ET

# ✅ ОБНОВЛЕНО: 2026-04 — добавлен Odyssey (1.6)
# ✅ СИСТЕМА РАСШИРЯЕМА — новые DLC добавляются только сюда
OFFICIAL_DLC = [
    "Core",  # Базовая игра (1.0)
    "Royalty",  # DLC 1 (1.1) — Империя, психические силы
    "Ideology",  # DLC 2 (1.3) — Идеологии, ритуалы
    "Biotech",  # DLC 3 (1.4) — Дети, генетика, механоиды
    "Anomaly",  # DLC 4 (1.5) — Ужас, аномалии, эксперименты
    "Odyssey",  # DLC 5 (1.6) — Новые биомы, фракции — 11 июля 2025
]

# ✅ Маппинг packageId → имя DLC (для верификации зависимостей)
DLC_PACKAGE_IDS = {
    "ludeon.rimworld": "Core",
    "ludeon.rimworld.royalty": "Royalty",
    "ludeon.rimworld.ideology": "Ideology",
    "ludeon.rimworld.biotech": "Biotech",
    "ludeon.rimworld.anomaly": "Anomaly",
    "ludeon.rimworld.odyssey": "Odyssey",
}

# ✅ Steam AppID для каждого DLC (для справки)
DLC_STEAM_APPIDS = {
    "Core": "294100",  # Базовая игра
    "Royalty": "1149640",  # DLC 1
    "Ideology": "1392840",  # DLC 2
    "Biotech": "1826140",  # DLC 3
    "Anomaly": "2380740",  # DLC 4
    "Odyssey": "3022790",  # DLC 5 (11.07.2025)
}


class GameReferenceManager:
    def __init__(self, game_path: str, lang="Russian"):
        self.game_path = game_path
        self.lang = lang
        self.reference_db = {}  # Ключ -> Перевод
        self.special_symbols = set()

    def _get_lang_folder_name(self, base_path: str) -> str | None:
        """
        Находит папку языка, учитывая что в RimWorld 1.6+ языки могут быть в .tar архивах.

        Проверяет:
        1. Распакованную папку (например, "Russian (Русский)")
        2. .tar архив (например, "Russian.tar")

        Args:
            base_path: Путь к папке Languages

        Returns:
            Путь к папке языка или None
        """
        if not os.path.exists(base_path):
            return None

        # Варианты названий для русского языка
        lang_variants = [
            self.lang,  # "Russian"
            f"{self.lang} (Русский)",  # "Russian (Русский)"
            "Russian (Русский).tar",  # .tar архив
            f"{self.lang}.tar",  # "Russian.tar"
        ]

        for variant in lang_variants:
            path = os.path.join(base_path, variant)
            if os.path.exists(path):
                return path

        # Если не нашли точное совпадение, ищем по частичному
        for item in os.listdir(base_path):
            if self.lang.lower() in item.lower():
                return os.path.join(base_path, item)

        return None

    def _extract_tar_to_temp(self, tar_path: str) -> str:
        """
        Извлекает .tar архив во временную папку.

        Args:
            tar_path: Путь к .tar архиву

        Returns:
            Путь к временной папке с извлечёнными файлами
        """
        import tempfile

        temp_dir = tempfile.mkdtemp(prefix="rimworld_lang_")

        try:
            with tarfile.open(tar_path, "r") as tar:
                tar.extractall(path=temp_dir)
        except Exception as e:
            print(f"Ошибка извлечения {tar_path}: {e}")
            return None

        return temp_dir

    def load_all_official_data(self) -> bool:
        """Загружает все строки из игры и DLC."""
        data_path = os.path.join(self.game_path, "Data")
        if not os.path.exists(data_path):
            return False

        for dlc in OFFICIAL_DLC:
            dlc_lang_path = os.path.join(data_path, dlc, "Languages")
            if os.path.exists(dlc_lang_path):
                self._scan_languages_folder(dlc_lang_path)

        return len(self.reference_db) > 0

    def _scan_languages_folder(self, languages_path: str):
        """
        Сканирует папку Languages, обрабатывая как распакованные папки, так и .tar архивы.

        Args:
            languages_path: Путь к папке Languages
        """
        lang_folder = self._get_lang_folder_name(languages_path)

        if not lang_folder:
            return

        # Проверяем, это .tar архив или папка
        if lang_folder.endswith(".tar"):
            # Извлекаем во временную папку
            temp_dir = self._extract_tar_to_temp(lang_folder)
            if temp_dir:
                try:
                    self._scan_dir(temp_dir)
                finally:
                    # Очищаем временную папку
                    import shutil

                    shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            # Обычная папка
            self._scan_dir(lang_folder)

    def _scan_dir(self, path: str):
        """Рекурсивно ищет XML и вытягивает строки."""
        for root, _, files in os.walk(path):
            for fn in files:
                if fn.endswith(".xml"):
                    self._parse_file(os.path.join(root, fn))

    def _parse_file(self, file_path: str):
        try:
            tree = ET.parse(file_path)
            for child in tree.getroot():
                if child.text and child.tag:
                    val = child.text.strip()
                    self.reference_db[child.tag] = val
                    # Собираем спецсимволы (например {0}, [Name])
                    found = re.findall(r"\{.*?\}|\[.*?\]|\(\^Cap\)", val)
                    self.special_symbols.update(found)
        except ET.ParseError as e:
            print(f"Ошибка парсинга XML в файле {file_path}: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка при чтении файла {file_path}: {e}")
