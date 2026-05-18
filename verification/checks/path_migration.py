# verification/checks/path_migration.py
"""
Проверка изменений пуей XML (миграция тегов).

Обнаруживает, когда тег переехал в другой файл или подпапку после обновления игры.
Например, раньше <label> был в ThingDef/Weapon/..., а теперь в DefInjected/ThingDef/Weapon/...

Реализует рекомендацию:
"Валидация 'Смерти' тега: В RimWorld часто меняется вложенность."
"""

from loguru import logger
import os
import re
from typing import Any

try:
    from fuzzywuzzy import fuzz
except ImportError:
    def fuzz_ratio(s1, s2):
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        return 100 if s1_lower == s2_lower else 0
    class fuzz:
        ratio = staticmethod(fuzz_ratio)

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class PathMigrationCheck(VerificationCheck):
    """
    Проверяет, соответствуют ли пути к тегам в моде текущей структуре игры.
    Если путь изменился, но DefName совпадает, предлагает автоматический перенос.
    """

    @property
    def name(self) -> str:
        return "path_migration"

    @property
    def description(self) -> str:
        return "Проверка актуальности путей тегов (миграция после обновлений)"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_id = mod_info["mod_id"]
        mod_path = mod_info.get("mod_path", "")
        lang_folder = context.get("target_language", "Russian")

        game_data_loader = context.get("game_data_loader")
        if not game_data_loader or not hasattr(game_data_loader, "key_to_file"):
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="GameDataLoader без key_to_file, пропуск проверки пути",
            )

        issues = []
        scanned = 0
        migrated = 0

        try:
            from verification.xml_parser import XMLParser

            parser = XMLParser()

            lang_path = os.path.join(mod_path, "Languages", lang_folder)
            if not os.path.exists(lang_path):
                return CheckResult(
                    check_name=self.name,
                    passed=True,
                    severity="info",
                    message=f"Нет переводов для языка {lang_folder}",
                )

            # Сканируем DefInjected файлы
            def_injected_dir = os.path.join(lang_path, "DefInjected")
            if not os.path.exists(def_injected_dir):
                return CheckResult(
                    check_name=self.name,
                    passed=True,
                    severity="info",
                    message="Нет DefInjected файлов для проверки пути",
                )

            for root_dir, _, files in os.walk(def_injected_dir):
                for filename in files:
                    if not filename.endswith(".xml"):
                        continue
                    file_path = os.path.join(root_dir, filename)
                    result = parser.parse(file_path)
                    if not result.success or not result.entries:
                        continue

                    for key in result.entries.keys():
                        if not key:
                            continue
                        scanned += 1

                        # Есть ли этот ключ в Core?
                        if key not in game_data_loader.reference_db:
                            # Возможно, ключ переименовали или переместили
                            # Пробуем найти похожий ключ в Core
                            similar_key = self._find_similar_key(key, game_data_loader.reference_db)
                            if similar_key:
                                core_file = game_data_loader.key_to_file.get(similar_key, "")
                                # Сравниваем относительные пути после DefInjected/ или Keyed/
                                mod_rel = self._get_relative_structure(file_path, lang_folder, mod_path)
                                core_rel = self._extract_core_structure(core_file)
                                if mod_rel and core_rel and mod_rel != core_rel:
                                    migrated += 1
                                    issues.append({
                                        "key": key,
                                        "file": file_path,
                                        "similar_key": similar_key,
                                        "core_file": core_file,
                                        "mod_structure": mod_rel,
                                        "core_structure": core_rel,
                                    })

        except Exception as e:
            logger.error(f"Ошибка при проверке миграции путей: {e}")
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Ошибка проверки: {e}",
            )

        if migrated > 0:
            details = {
                "scanned": scanned,
                "migrated": migrated,
                "issues": issues[:20],
            }
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="warning",
                message=f"Найдено {migrated} тегов, возможна миграция путей",
                details=details,
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message=f"Все {scanned} тегов находятся в актуальных путях",
                details={"scanned": scanned},
            )

    def _find_similar_key(self, key: str, reference_db: dict, threshold: int = 85) -> str | None:
        """Ищет похожий ключ в справочной базе через RapidFuzz."""
        best_match = None
        best_score = 0
        for ref_key in reference_db.keys():
            score = fuzz.ratio(key, ref_key)
            if score >= threshold and score > best_score:
                best_score = score
                best_match = ref_key
        return best_match

    def _get_relative_structure(self, file_path: str, lang_folder: str, mod_path: str) -> str:
        """
        Возвращает относительный путь от папки Languages/{lang} до файла,
        нормализованный для сравнения.
        Пример: DefInjected/ThingDef/Weapon/Gun.xml
        """
        try:
            # Находим базовую папку Languages/{lang}
            base = os.path.join(mod_path, "Languages", lang_folder)
            if os.path.exists(base):
                rel = os.path.relpath(file_path, base)
                # Нормализуем для кросс-платформенности
                return rel.replace("\\", "/")
            # Если нет такой, берем от mod_path
            rel = os.path.relpath(file_path, mod_path)
            return rel.replace("\\", "/")
        except Exception:
            return ""

    def _extract_core_structure(self, core_file: str) -> str:
        """Извлекает структуру пути из Core файла (часть после Languages/.../DefInjected/ или Keyed/)"""
        try:
            # Ищем начало DefInjected или Keyed в пути
            match = re.search(r"(?:DefInjected|Keyed)[\\/].*", core_file)
            if match:
                return match.group(0).replace("\\", "/")
            # Или берем от папки Languages
            match = re.search(r"Languages[\\/].*", core_file)
            if match:
                return match.group(0).replace("\\", "/")
            return os.path.basename(core_file)
        except Exception:
            return ""
