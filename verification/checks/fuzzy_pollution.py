# verification/checks/fuzzy_pollution.py
"""
Обнаружение «fuzzy-загрязнения» — массовых ложных совпадений
от одного префикса (например, Kurin_* → все в один файл).
"""

import logging
import os
from typing import Any

from ..verification_coordinator import VerificationCheck, CheckResult
from translation.matching import find_existing_translation

logger = logging.getLogger(__name__)


class FuzzyPollutionCheck(VerificationCheck):
    """
    Обнаружение «fuzzy-загрязнения» — массовых ложных совпадений
    от одного префикса (например, Kurin_* → все в один файл).
    """

    @property
    def name(self) -> str:
        return "fuzzy_pollution"

    @property
    def description(self) -> str:
        return "Проверка массовых fuzzy-совпадений от одного префикса"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_path = mod_info.get("mod_path", "")
        lang_folder = context.get("target_language", "Russian")
        lang_path = os.path.join(mod_path, "Languages", lang_folder, "DefInjected")

        if not os.path.exists(lang_path):
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Нет DefInjected файлов для проверки",
            )

        # Собираем все теги
        from verification.xml_parser import XMLParser
        parser = XMLParser()
        all_tags = []  # (tag, file)

        for root_dir, _, files in os.walk(lang_path):
            for filename in files:
                if not filename.endswith(".xml"):
                    continue
                file_path = os.path.join(root_dir, filename)
                result = parser.parse(file_path)
                if result.success and result.root is not None:
                    for child in result.root:
                        if child.tag and isinstance(child.tag, str):
                            all_tags.append((child.tag, file_path))

        if len(all_tags) < 10:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Недостаточно тегов для анализа загрязнения",
            )

        # Для каждого тега пытаемся найти его потенциальный fuzzy-матч
        pollution_map = {}  # prefix -> count of fuzzy matches pointing to same file
        existing_map = {t: "" for t, _ in all_tags}
        existing_index = {t: f for t, f in all_tags}

        for tag, file_path in all_tags:
            try:
                fuzzy_val, fuzzy_path = find_existing_translation(
                    tagname=tag,
                    existing_map=existing_map,
                    existing_index=existing_index,
                    logger=logger,
                    fuzzy=True,
                    use_anchors=False,
                )
                if fuzzy_val and fuzzy_path and fuzzy_path != file_path:
                    # Fuzzy связывает тег с ДРУГИМ файлом — фиксируем
                    prefix = tag.split('_')[0] if '_' in tag else tag
                    key = (prefix, fuzzy_path)
                    pollution_map[key] = pollution_map.get(key, 0) + 1
            except Exception:
                pass

        # Проверяем: есть ли префиксы, у которых >30% тегов ссылаются на один файл-цель
        suspicious = []
        total_tags_by_prefix = {}
        for tag, _ in all_tags:
            prefix = tag.split('_')[0] if '_' in tag else tag
            total_tags_by_prefix[prefix] = total_tags_by_prefix.get(prefix, 0) + 1

        for (prefix, target_file), count in pollution_map.items():
            total = total_tags_by_prefix.get(prefix, 1)
            ratio = count / total
            if ratio >= 0.3:
                suspicious.append(
                    {
                        "prefix": prefix,
                        "target_file": target_file,
                        "matched_count": count,
                        "total_count": total,
                        "ratio": f"{ratio:.1%}",
                    }
                )

        if suspicious:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="warning",
                message=f"Обнаружено {len(suspicious)} префиксов с массовым fuzzy-совпадением (>30%)",
                details={"suspicious": suspicious},
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Fuzzy-загрязнение не обнаружено",
            )
