# verification/checks/core_auto_fill.py
"""
Предлагает использовать официальный перевод Core для стандартных строк.

Когда мод переводит строку, которая уже есть в официальных переводах Core,
этот check предлагает заменить перевод на официальный (для консистентности).

Реализует рекомендацию:
"Автозаполнение из официальной локализации"
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


class CoreAutoFillCheck(VerificationCheck):
    """
    Предлагает автоисправление: использовать официальный перевод Core,
    если мод переводит ту же строку, что и в базовой игре, но с другим текстом.
    """

    @property
    def name(self) -> str:
        return "core_auto_fill"

    @property
    def description(self) -> str:
        return "Предложение использовать официальные переводы Core"

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
                message="GameDataLoader недоступен, пропуск предложений автоисправления",
            )

        suggestions = []
        scanned = 0

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

            # Сканируем DefInjected и Keyed
            for subdir in ["Keyed", "DefInjected"]:
                scan_dir = os.path.join(lang_path, subdir)
                if not os.path.exists(scan_dir):
                    continue
                for root_dir, _, files in os.walk(scan_dir):
                    for filename in files:
                        if not filename.endswith(".xml"):
                            continue
                        file_path = os.path.join(root_dir, filename)
                        result = parser.parse(file_path)
                        if result.success and result.entries:
                            for key, translated_value in result.entries.items():
                                if not translated_value or not translated_value.strip():
                                    continue
                                # Ищем официальный перевод по тому же ключу
                                official_translation = game_data_loader.reference_db.get(key)
                                if official_translation and official_translation != translated_value:
                                    # Сравниваем similarity
                                    similarity = fuzz.ratio(translated_value, official_translation)
                                    if similarity < 100:
                                        # Предлагаем заменить на официальный
                                        suggestions.append({
                                            "key": key,
                                            "file": file_path,
                                            "mod_translation": translated_value,
                                            "core_translation": official_translation,
                                            "similarity": similarity,
                                        })
                                scanned += 1

        except Exception as e:
            logger.error(f"Ошибка при проверке автоисправления: {e}")
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="error",
                message=f"Ошибка проверки: {e}",
            )

        if suggestions:
            details = {
                "scanned": scanned,
                "suggestions": suggestions[:10],
                "count": len(suggestions),
            }
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="info",  # Это не ошибка, а предложение
                message=f"Найдено {len(suggestions)} переводов, расходящихся с Core. Рекомендуется заменить на официальные.",
                details=details,
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message=f"Все {scanned} переводов совпадают с официальными",
                details={"scanned": scanned},
            )
