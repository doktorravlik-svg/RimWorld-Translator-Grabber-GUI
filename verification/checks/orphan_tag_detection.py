# verification/checks/orphan_tag_detection.py
"""
Обнаружение сиротских (orphan) тегов переводов.

Моды часто копируют куски XML из Core. При обновлении игры пути в Core могут измениться,
и старые теги становятся недействительными. Этот check обнаруживает такие теги.

Реализует рекомендацию:
"Валидация «сиротских» (Orphan) тегов"
"""

from loguru import logger
import os
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


class OrphanTagDetectionCheck(VerificationCheck):
    """
    Проверяет, существуют ли Def-теги, на которые ссылаются переводы,
    в текущей версии игры (Core/DLC). Если нет — помечает как сироты (orphan).
    """

    @property
    def name(self) -> str:
        return "orphan_tag_detection"

    @property
    def description(self) -> str:
        return "Обнаружение устаревших (сиротских) тегов переводов"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_id = mod_info["mod_id"]
        mod_path = mod_info.get("mod_path", "")
        lang_folder = context.get("target_language", "Russian")

        game_data_loader = context.get("game_data_loader")
        if not game_data_loader:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="GameDataLoader недоступен, пропуск проверки сиротских тегов",
            )

        issues = []
        scanned = 0
        orphaned = 0

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

            # Сканируем DefInjected файлы (там находятся основные Def-теги)
            def_injected_dir = os.path.join(lang_path, "DefInjected")
            if not os.path.exists(def_injected_dir):
                return CheckResult(
                    check_name=self.name,
                    passed=True,
                    severity="info",
                    message="Нет DefInjected файлов для проверки",
                )

            for root_dir, _, files in os.walk(def_injected_dir):
                for filename in files:
                    if not filename.endswith(".xml"):
                        continue
                    file_path = os.path.join(root_dir, filename)
                    result = parser.parse(file_path)
                    if result.success and result.entries:
                        for key in result.entries.keys():
                            if not key:
                                continue
                            scanned += 1
                            # Проверяем существование ключа в официальных данных
                            if key not in game_data_loader.reference_db:
                                # Ключ не найден — возможно, удалён из игры
                                orphaned += 1
                                # Пробуем найти похожий ключ через RapidFuzz (возможно, путь изменился)
                                suggestion = self._find_similar_key(key, game_data_loader.reference_db)
                                issues.append({
                                    "key": key,
                                    "file": file_path,
                                    "suggestion": suggestion,
                                    "status": "orphan",
                                })

        except Exception as e:
            logger.error(f"Ошибка при проверке сиротских тегов: {e}")
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Ошибка проверки: {e}",
            )

        if orphaned > 0:
            details = {
                "scanned": scanned,
                "orphaned": orphaned,
                "issues": issues[:20],
            }
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="warning",
                message=f"Найдено {orphaned} сиротских тегов из {scanned} проверенных",
                details=details,
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message=f"Все {scanned} тегов существуют в текущей версии игры",
                details={"scanned": scanned},
            )

    def _find_similar_key(self, key: str, reference_db: dict, threshold: int = 85) -> str | None:
        """
        Ищет похожий ключ в справочной базе через RapidFuzz.
        Может указывать на изменение пути (переименование Def).
        """
        best_match = None
        best_score = 0

        for ref_key in reference_db.keys():
            score = fuzz.ratio(key, ref_key)
            if score >= threshold and score > best_score:
                best_score = score
                best_match = ref_key

        return best_match
