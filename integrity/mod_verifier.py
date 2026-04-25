# mod_verifier.py - Верификация модов RimWorld
import os
import lxml.etree as etree
from verification.xml_parser import safe_parse_xml


class ModVerifier:
    """Класс для верификации модов RimWorld"""

    def __init__(self, mods_folder: str, logger=None):
        self.mods_folder = mods_folder
        self.logger = logger
        self.results = []

    def verify_all_mods(self) -> list[dict]:
        """
        Проверяет все моды в папке.

        Returns:
            Список результатов проверки
        """
        self.results = []

        if not self.mods_folder or not os.path.exists(self.mods_folder):
            return self.results

        for item in os.listdir(self.mods_folder):
            mod_path = os.path.join(self.mods_folder, item)
            if not os.path.isdir(mod_path):
                continue

            result = self.verify_mod(mod_path)
            self.results.append(result)

        return self.results

    def verify_mod(self, mod_path: str) -> dict:
        """
        Проверяет отдельный мод.

        Args:
            mod_path: Путь к папке мода

        Returns:
            Словарь с результатами проверки
        """
        result = {
            "mod_name": os.path.basename(mod_path),
            "mod_path": mod_path,
            "errors": [],
            "warnings": [],
            "info": [],
        }

        # Проверка About.xml
        self._verify_about(mod_path, result)

        # Проверка Defs
        self._verify_defs(mod_path, result)

        # Проверка Languages
        self._verify_languages(mod_path, result)

        return result

    def _verify_about(self, mod_path: str, result: dict):
        """Проверка About.xml"""
        about_path = os.path.join(mod_path, "About", "About.xml")

        if not os.path.exists(about_path):
            result["errors"].append("Отсутствует About.xml")
            return

        try:
            root = safe_parse_xml(about_path)
            if root is None:
                result["errors"].append("Не удалось распарсить About.xml")
                return
            package_id = root.find("packageId")
            if package_id is None or not package_id.text or not package_id.text.strip():
                result["errors"].append("Отсутствует packageId")
            else:
                result["info"].append(f"PackageId: {package_id.text.strip()}")

            # Проверка name
            name = root.find("name")
            if name is None or not name.text or not name.text.strip():
                result["warnings"].append("Отсутствует название мода")

            # Проверка author
            author = root.find("author")
            if author is None or not author.text or not author.text.strip():
                result["warnings"].append("Отсутствует автор")

            # Проверка supportedVersions
            supported_versions = root.find("supportedVersions")
            if supported_versions is None:
                result["warnings"].append("Отсутствует supportedVersions")

        except etree.XMLSyntaxError as e:
            result["errors"].append(f"Ошибка парсинга About.xml: {e}")
        except Exception as e:
            result["errors"].append(f"Неожиданная ошибка при проверке About.xml: {e}")

    def _verify_defs(self, mod_path: str, result: dict):
        """Проверка папки Defs"""
        defs_found = False

        # Ищем Defs в разных местах
        for version in ["1.6", "1.5", "1.4", "1.3", ""]:
            defs_path = (
                os.path.join(mod_path, version, "Defs")
                if version
                else os.path.join(mod_path, "Defs")
            )
            if os.path.exists(defs_path):
                defs_found = True
                # Проверяем XML файлы
                xml_count = 0
                error_count = 0
                for root, dirs, files in os.walk(defs_path):
                    for filename in files:
                        if filename.endswith(".xml"):
                            xml_count += 1
                            filepath = os.path.join(root, filename)
                            try:
                                safe_parse_xml(filepath)
                            except etree.XMLSyntaxError:
                                error_count += 1
                                result["errors"].append(f"Ошибка XML: {filepath}")

                result["info"].append(f"Defs: {xml_count} XML файлов, {error_count} ошибок")
                break

        if not defs_found:
            result["warnings"].append("Папка Defs не найдена")

    def _verify_languages(self, mod_path: str, result: dict):
        """Проверка папки Languages"""
        langs_found = False

        for version in ["1.6", "1.5", "1.4", "1.3", ""]:
            langs_path = (
                os.path.join(mod_path, version, "Languages")
                if version
                else os.path.join(mod_path, "Languages")
            )
            if os.path.exists(langs_path):
                langs_found = True
                languages = []
                for item in os.listdir(langs_path):
                    lang_path = os.path.join(langs_path, item)
                    if os.path.isdir(lang_path):
                        languages.append(item)

                        # Проверяем XML файлы в языке
                        xml_count = 0
                        error_count = 0
                        for root, dirs, files in os.walk(lang_path):
                            for filename in files:
                                if filename.endswith(".xml"):
                                    xml_count += 1
                                    filepath = os.path.join(root, filename)
                                    try:
                                        safe_parse_xml(filepath)
                                    except etree.XMLSyntaxError:
                                        error_count += 1
                                        result["errors"].append(f"Ошибка XML: {filepath}")

                result["info"].append(f"Languages: {', '.join(languages)}")
                break

        if not langs_found:
            result["info"].append("Languages: не найдено")


def verify_mods(mods_folder: str, logger=None) -> list[dict]:
    """
    Удобная функция для верификации модов.

    Args:
        mods_folder: Путь к папке с модами
        logger: Логгер

    Returns:
        Список результатов проверки
    """
    verifier = ModVerifier(mods_folder, logger)
    return verifier.verify_all_mods()
