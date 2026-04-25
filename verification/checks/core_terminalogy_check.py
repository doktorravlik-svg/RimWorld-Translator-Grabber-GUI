# verification/checks/core_terminalogy_check.py
"""
Проверка консистентности терминологии с официальными переводами Core.

Сравнивает переводы мода с официальными переводами из Core/DLC,
выявляет расхождения в терминологии (например, "Сталь" vs "Железо").

Реализует рекомендацию из документа:
"Проверка на терминологическую консистенцию"
"""

import logging
import os

from rapidfuzz import fuzz

from ..verification_coordinator import VerificationCheck, CheckResult

logger = logging.getLogger(__name__)


class CoreTerminologyConsistencyCheck(VerificationCheck):
    """
    Проверяет, что переводы мода соответствуют официальной терминологии Core.
    """

    @property
    def name(self) -> str:
        return "core_terminalogy_consistency"

    @property
    def description(self) -> str:
        return "Проверка соответствия переводов официальным терминам Core"

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
                message="GameDataLoader недоступен, пропуск проверки Core терминологии",
            )

        issues = []
        scanned = 0

        try:
            from verification.xml_parser import XMLParser

            parser = XMLParser()

            # Сканируем переводы мода (Keyed и DefInjected)
            lang_path = os.path.join(mod_path, "Languages", lang_folder)
            if not os.path.exists(lang_path):
                return CheckResult(
                    check_name=self.name,
                    passed=True,
                    severity="info",
                    message=f"Нет переводов для языка {lang_folder}",
                )

            # 1. Сканируем Keyed файлы
            keyed_dir = os.path.join(lang_path, "Keyed")
            if os.path.exists(keyed_dir):
                for root_dir, _, files in os.walk(keyed_dir):
                    for filename in files:
                        if not filename.endswith(".xml"):
                            continue
                        file_path = os.path.join(root_dir, filename)
                        result = parser.parse(file_path)
                        if result.success and result.entries:
                            for key, translated_value in result.entries.items():
                                if not translated_value or not translated_value.strip():
                                    continue
                                self._check_translation(
                                    key=key,
                                    translated=translated_value.strip(),
                                    file_path=file_path,
                                    game_data=game_data_loader,
                                    issues=issues,
                                )
                                scanned += 1

            # 2. Сканируем DefInjected файлы
            def_injected_dir = os.path.join(lang_path, "DefInjected")
            if os.path.exists(def_injected_dir):
                for root_dir, _, files in os.walk(def_injected_dir):
                    for filename in files:
                        if not filename.endswith(".xml"):
                            continue
                        file_path = os.path.join(root_dir, filename)
                        result = parser.parse(file_path)
                        if result.success and result.entries:
                            for key, translated_value in result.entries.items():
                                if not translated_value or not translated_value.strip():
                                    continue
                                self._check_translation(
                                    key=key,
                                    translated=translated_value.strip(),
                                    file_path=file_path,
                                    game_data=game_data_loader,
                                    issues=issues,
                                )
                                scanned += 1

        except Exception as e:
            logger.error(f"Ошибка при проверке Core терминологии: {e}")
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Ошибка проверки: {e}",
            )

        # Собираем статистику
        matched = sum(1 for i in issues if i.get("status") == "matched")
        mismatched = sum(1 for i in issues if i.get("status") == "mismatched")

        if mismatched > 0:
            details = {
                "scanned": scanned,
                "matched": matched,
                "mismatched": mismatched,
                "issues": issues[:20],
            }
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="warning",
                message=f"Найдено {mismatched} расхождений с Core переводом из {matched} проверенных",
                details=details,
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message=f"Все {scanned} переводов соответствуют Core терминологии",
                details={"scanned": scanned, "matched": matched},
            )

    def _check_translation(
        self,
        key: str,
        translated: str,
        file_path: str,
        game_data,
        issues: list,
    ):
        """
        Проверяет один перевод против официального Core перевода.
        """
        try:
            # Прямой поиск официального перевода по ключу
            official_translation = game_data.reference_db.get(key)
            matched_key = key

            # Если не найден, пробуем найти похожий ключ через RapidFuzz
            if not official_translation:
                similar_key = self._find_similar_key(key, game_data.reference_db, threshold=85)
                if similar_key:
                    official_translation = game_data.reference_db.get(similar_key)
                    matched_key = similar_key

            if not official_translation:
                # Ключ не найден в Core — возможно, это новый Def или мод-специфичный
                return

            # Сравниваем через fuzz.ratio
            similarity = fuzz.ratio(translated, official_translation)

            # Пороги
            THRESHOLD_EXCELLENT = 100
            THRESHOLD_GOOD = 90

            if similarity >= THRESHOLD_EXCELLENT:
                issues.append({
                    "key": key,
                    "matched_key": matched_key,
                    "file": file_path,
                    "mod_translation": translated,
                    "core_translation": official_translation,
                    "similarity": similarity,
                    "status": "matched",
                })
            elif similarity >= THRESHOLD_GOOD:
                issues.append({
                    "key": key,
                    "matched_key": matched_key,
                    "file": file_path,
                    "mod_translation": translated,
                    "core_translation": official_translation,
                    "similarity": similarity,
                    "status": "good_mismatch",
                })
            else:
                issues.append({
                    "key": key,
                    "matched_key": matched_key,
                    "file": file_path,
                    "mod_translation": translated,
                    "core_translation": official_translation,
                    "similarity": similarity,
                    "status": "mismatched",
                })

        except Exception as e:
            logger.debug(f"Ошибка проверки ключа {key}: {e}")

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
