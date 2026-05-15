# verification/checks/smart_revision.py
"""
Умная проверка устаревших/переименованных тегов с помощью RapidFuzz.
Перепроверяет существующие связи Tag->Translation через новый fuzzy-алгоритм.
"""

from config.language_constants import DEFAULT_TARGET_LANGUAGE
from loguru import logger
import os
from typing import Any

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult
from translation.matching import find_existing_translation


class SmartRevisionCheck(VerificationCheck):
    """
    Умная проверка устаревших/переименованных тегов с помощью RapidFuzz.
    Перепроверяет существующие связи Tag->Translation через новый fuzzy-алгоритм.
    """

    @property
    def name(self) -> str:
        return "smart_revision"

    @property
    def description(self) -> str:
        return "Поиск устаревших переводов с помощью fuzzy-сравнения DefName"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_path = mod_info.get("mod_path", "")
        issues = []
        revisited = []  # (tag, file, current_translation, fuzzy_score, suggestion)

        # Сканируем DefInjected файлы перевода
        lang_folder = context.get("target_language", DEFAULT_TARGET_LANGUAGE)
        lang_path = os.path.join(mod_path, "Languages", lang_folder, "DefInjected")
        if not os.path.exists(lang_path):
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Нет DefInjected файлов для проверки",
            )

        # Собираем теги и их переводы
        from verification.xml_parser import XMLParser
        parser = XMLParser()
        existing_map = {}  # tagname -> translation + file

        for root_dir, _, files in os.walk(lang_path):
            for filename in files:
                if not filename.endswith(".xml"):
                    continue
                file_path = os.path.join(root_dir, filename)
                result = parser.parse(file_path)
                if result.success and result.root is not None:
                    for child in result.root:
                        if child.tag and child.text and child.text.strip():
                            tag = child.tag
                            # Пропускаем _OBSOLETE_
                            if tag.startswith("_OBSOLETE_"):
                                tag = tag[len("_OBSOLETE_"):]
                            existing_map[tag] = {
                                "translation": child.text.strip(),
                                "file": file_path,
                            }

        if not existing_map:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Нет переводов для проверки",
            )

        # Для каждого тега делаем fuzzy-перепроверку
        for tag, info in existing_map.items():
            current_translation = info["translation"]
            file_path = info["file"]

            # Пытаемся найти лучший перевод через fuzzy (без контекста — просто по тегу)
            try:
                fuzzy_val, fuzzy_source = find_existing_translation(
                    tagname=tag,
                    existing_map=existing_map,
                    existing_index={t: i["file"] for t, i in existing_map.items()},
                    logger=logger,
                    mode="strict",
                    fuzzy=True,
                    original_text=None,
                    use_anchors=False,
                    target_language=lang_folder,
                )

                if fuzzy_val and fuzzy_val != current_translation:
                    # Fuzzy нашёл ДРУГОЙ перевод — возможен устаревший
                    # Вычисляем score через rapidfuzz для точности
                    try:
                        from rapidfuzz import fuzz
                        # Разбираем tag на части для сравнения
                        t_lower = tag.lower()
                        t_parts = t_lower.split('.', 1)
                        if len(t_parts) >= 2:
                            t_def_part = t_parts[0].split('_', 1)
                            if len(t_def_part) >= 2:
                                t_def_name = t_def_part[1]
                                # Лучший кандидат — тот, чей DefName максимально похож
                                best_score = 0
                                for other_tag in existing_map:
                                    if other_tag == tag:
                                        continue
                                    o_lower = other_tag.lower()
                                    o_parts = o_lower.split('.', 1)
                                    if len(o_parts) < 2:
                                        continue
                                    o_def_part = o_parts[0].split('_', 1)
                                    if len(o_def_part) < 2:
                                        continue
                                    score = fuzz.ratio(t_def_name, o_def_part[1])
                                    if score > best_score:
                                        best_score = score

                                if best_score < 60:
                                    issues.append(
                                        {
                                            "tag": tag,
                                            "file": file_path,
                                            "current": current_translation[:60],
                                            "suggested": fuzzy_val[:60],
                                            "score": best_score,
                                        }
                                    )
                    except ImportError:
                        # Без rapidfuzz считаем низкий порог
                        issues.append({"tag": tag, "file": file_path, "note": "fuzzy mismatch"})

            except Exception as e:
                logger.debug(f"Ошибка fuzzy-перепроверки {tag}: {e}")

        if issues:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity="warning",
                message=f"Найдено {len(issues)} устаревших/переименованных тегов",
                details={"issues": issues, "count": len(issues)},
            )
        else:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message="Устаревшие теги не обнаружены",
            )
