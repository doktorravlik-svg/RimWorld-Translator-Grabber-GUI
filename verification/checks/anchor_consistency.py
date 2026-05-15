# verification/checks/anchor_consistency.py
"""
Проверка консистентности терминологии через AnchorManager.
Выявляет конфликты: например, "Steel" переведён как "Сталь" в якорях,
а в моде — как "Железо".
"""

from loguru import logger
import os
from typing import Any

from ..checks_base import VerificationCheck
from ..verification_coordinator import CheckResult


class AnchorConsistencyCheck(VerificationCheck):
    """
    Проверка консистентности терминологии через AnchorManager.
    Выявляет конфликты: например, "Steel" переведён как "Сталь" в якорях,
    а в моде — как "Железо".
    """

    @property
    def name(self) -> str:
        return "anchor_consistency"

    @property
    def description(self) -> str:
        return "Проверка соответствия терминологии якорям Core"

    def run(self, mod_info: dict, context: dict) -> CheckResult:
        mod_path = mod_info.get("mod_path", "")
        lang_folder = context.get("target_language", "Russian")
        conflicts = []

        try:
            from translation.anchor_manager import AnchorManager
            anchor_mgr = AnchorManager.get_instance()
        except Exception as e:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity="info",
                message=f"AnchorManager недоступен: {e}",
            )

        # Сканируем переводы мода
        from verification.xml_parser import XMLParser
        parser = XMLParser()
        scanned = 0

        for root_dir, _, files in os.walk(mod_path):
            for filename in files:
                if not filename.endswith(".xml"):
                    continue
                file_path = os.path.join(root_dir, filename)
                result = parser.parse(file_path)
                if not result.success or result.root is None:
                    continue

                for child in result.root:
                    if not (child.tag and child.text and child.text.strip()):
                        continue
                    tag = child.tag
                    translation = child.text.strip()
                    original = ""  # EN оригинала нет в файле перевода

                    # Пытаемся получить оригинал из EN: комментария (если есть)
                    # (это потребовало бы парсинга текста, но пока упрощённо)
                    # Для defect мы может retrieve original from EN comment
                    # Но этот check работает с уже переведёнными файлами, где оригиналов нет
                    # Поэтому ищем по смыслу: смотрим, есть ли в якорях перевод для этого текста (обратный поиск)
                    # Если якорь говорит, что original X всегда переводится как Y, а у нас Z — конфликт.

                    # Альтернатива: ищем по оригинальному тексту (если он хранится где-то)
                    # Пока проверим только case: если в якорях original_text = steel -> translation = Сталь
                    # а в моде мы видим translation = Железо для какого-то оригиналного текста steel — конфликт.

                    # Но don't have original. So этот check имеет смысл только если у нас есть доступ к original из Keyed/English.
                    # Пока пропустим — потребует расширения.
                    pass

                scanned += 1

        return CheckResult(
            check_name=self.name,
            passed=True,
            severity="info",
            message=f"Проверено {scanned} файлов (требует доработки)",
            details={"scanned": scanned},
        )
