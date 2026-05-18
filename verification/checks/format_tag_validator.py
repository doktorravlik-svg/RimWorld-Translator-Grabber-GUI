# verification/checks/format_tag_validator.py
"""
Проверка тегов форматирования и логических токенов
RimWorld 1.6+ — валидация <link>, <b>, <i>, [PAWN_gender ? ... : ...] и т.д.
Стандарт 2026 года
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TagValidationRule:
    """Правило валидации тега"""
    name: str
    tag_pattern: str
    required_closing: bool = True
    allow_nesting: bool = False
    rimworld_standard: bool = True


class FormatTagValidator:
    """
    Проверка тегов форматирования и логических конструкций.

    Обеспечивает:
    - Корректность XML-подобных тегов (<link>, <b>, <i>, <color>, <size> и др.)
    - Согласованность открывающих/закрывающих тегов
    - Корректность логических токенов [PAWN_gender ? ... : ...]
    - Корректность условных конструкций и выборов
    - Правильность ссылок (ссылки на Def'ы)
    """

    def __init__(self):
        # Стандартные теги RimWorld
        self.rules = {
            "link": TagValidationRule(
                name="link",
                tag_pattern=r"link",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "b": TagValidationRule(
                name="b",
                tag_pattern=r"b",
                required_closing=True,
                allow_nesting=True,
                rimworld_standard=True,
            ),
            "i": TagValidationRule(
                name="i",
                tag_pattern=r"i",
                required_closing=True,
                allow_nesting=True,
                rimworld_standard=True,
            ),
            "color": TagValidationRule(
                name="color",
                tag_pattern=r"color",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "size": TagValidationRule(
                name="size",
                tag_pattern=r"size",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "u": TagValidationRule(
                name="u",
                tag_pattern=r"u",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "sup": TagValidationRule(
                name="sup",
                tag_pattern=r"sup",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "sub": TagValidationRule(
                name="sub",
                tag_pattern=r"sub",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=True,
            ),
            "nobr": TagValidationRule(
                name="nobr",
                tag_pattern=r"nobr",
                required_closing=True,
                allow_nesting=False,
                rimworld_standard=False,  # Не стандартный, но поддерживается
            ),
        }

        # Логические токены и конструкции
        self.logical_tokens = [
            r"\[PAWN_gender\s*\?.*?:.*?\]",
            r"\[PAWN_possessive\s*\?.*?:.*?\]",
            r"\[PAWN_pronoun\s*\?.*?:.*?\]",
            r"\[PAWN_objective\s*\?.*?:.*?\]",
            r"\[select\s*\?.*?:.*?\]",
            r"\[Rand\s*\([^)]+\)\]",
            r"\[Plural\s*\([^)]+\)\]",
            r"\[Replace\s*\([^)]+\)\]",
            r"\[Key\s*:[^\]]+\]",
            r"\[GetStat\s*:[^\]]+\]",
            r"\[HasStat\s*:[^\]]+\]",
            r"\[Skill\s*:[^\]]+\]",
        ]

        # Вложенные теги должны быть правильно закрыты
        self.nesting_tags = {"color", "size", "b", "i", "u", "sup", "sub"}

    def verify(self, text: str, original_text: str = "", context: dict = None) -> list[dict]:
        """
        Проверяет форматирование и логические токены.

        Args:
            text: Проверяемый текст
            original_text: Оригинальный текст (для сравнения)
            context: Контекст проверки

        Returns:
            Список найденных проблем
        """
        findings = []
        context = context or {}

        # 1. Проверка парных тегов
        findings.extend(self._check_tag_pairs(text))

        # 2. Проверка вложенности
        findings.extend(self._check_nesting(text))

        # 3. Проверка логических токенов
        findings.extend(self._check_logical_tokens(text, original_text))

        # 4. Проверка ссылок
        findings.extend(self._check_links(text))

        # 5. Проверка атрибутов тегов
        findings.extend(self._check_tag_attributes(text))

        # 6. Проверка специальных конструкций [PAWN_...]
        findings.extend(self._check_pawn_tokens(text, original_text, context))

        # 7. Проверка пустых тегов
        findings.extend(self._check_empty_tags(text))

        # 8. Если есть оригинал — сравниваем структуру тегов
        if original_text:
            findings.extend(self._compare_tag_structure(text, original_text))

        return findings

    def _check_tag_pairs(self, text: str) -> list[dict]:
        """Проверяет наличие парных открывающих/закрывающих тегов"""
        findings = []

        for tag_name, rule in self.rules.items():
            if not rule.required_closing:
                continue

            open_pattern = rf"<{tag_name}\b[^>]*>"
            close_pattern = rf"</{tag_name}>"

            open_tags = re.findall(open_pattern, text)
            close_tags = re.findall(close_pattern, text)

            if len(open_tags) != len(close_tags):
                findings.append({
                    "type": "FORMAT_UNPAIRED_TAG",
                    "severity": "error",
                    "tag": tag_name,
                    "msg": f"Непарный тег <{tag_name}>: открыто {len(open_tags)}, закрыто {len(close_tags)}",
                    "opens": len(open_tags),
                    "closes": len(close_tags),
                })

        return findings

    def _check_nesting(self, text: str) -> list[dict]:
        """Проверяет корректность вложенности тегов"""
        findings = []

        # Собираем все теги по порядку
        tag_pattern = r"</?(\w+)(?:\s+[^>]*)?>"
        tags = re.finditer(tag_pattern, text)

        stack = []
        for match in tags:
            tag_name = match.group(1).lower()
            is_closing = match.group(0).startswith("</")

            if tag_name not in self.rules:
                continue

            if not is_closing:
                stack.append((tag_name, match.start()))
            else:
                # Ищем соответствующий открывающий тег
                found = False
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == tag_name:
                        found = True
                        # Проверяем неправильную вложенность
                        for j in range(i + 1, len(stack)):
                            findings.append({
                                "type": "FORMAT_BAD_NESTING",
                                "severity": "error",
                                "msg": f"Некорректная вложенность: <{stack[j][0]}> внутри <{tag_name}>",
                                "outer": tag_name,
                                "inner": stack[j][0],
                            })
                        stack = stack[:i]
                        break

                if not found:
                    findings.append({
                        "type": "FORMAT_UNPAIRED_CLOSING",
                        "severity": "error",
                        "msg": f"Закрывающий тег </{tag_name}> без открывающего",
                    })

        # Остались незакрытые теги
        for tag_name, pos in stack:
            findings.append({
                "type": "FORMAT_UNCLOSED_TAG",
                "severity": "error",
                "msg": f"Тег <{tag_name}> не закрыт",
            })

        return findings

    def _check_logical_tokens(self, text: str, original: str) -> list[dict]:
        """Проверяет логические токены [PAWN_...], [select], [Rand], [Plural] и т.д."""
        findings = []

        all_logical_tokens = re.findall(r'\[([^\]]+(?:\][^\]]+)*?)\]', text)

        for token in all_logical_tokens:
            # Проверка на незакрытые вложенные скобки
            if token.count('[') != token.count(']'):
                findings.append({
                    "type": "FORMAT_UNBALANCED_BRACKETS",
                    "severity": "error",
                    "msg": f"Несбалансированные скобки в токене: [{token}]",
                })
                continue

            token_lower = token.lower()

            # Проверка [PAWN_gender]
            if "pawn_gender" in token_lower:
                # Ожидаемый формат: [PAWN_gender ? мужской_род : женский_род]
                if "?" not in token or ":" not in token:
                    findings.append({
                        "type": "FORMAT_LOGICAL_MALFORMED",
                        "severity": "error",
                        "token": f"[{token}]",
                        "msg": "Некорректный формат [PAWN_gender ? ... : ...]: отсутствует ? или :",
                    })

                parts = token.split("?", 1)
                if len(parts) == 2:
                    options_part = parts[1].split(":", 1)
                    if len(options_part) != 2:
                        findings.append({
                            "type": "FORMAT_LOGICAL_MALFORMED",
                            "severity": "error",
                            "token": f"[{token}]",
                            "msg": "[PAWN_gender] должен иметь формат: [PAWN_gender ? мужской : женский]",
                        })

            # Проверка [select]
            if token_lower.startswith("select"):
                if "?" not in token or ":" not in token:
                    findings.append({
                        "type": "FORMAT_LOGICAL_MALFORMED",
                        "severity": "error",
                        "token": f"[{token}]",
                        "msg": "[select] должен иметь формат: [select значение ? если_равно : если_не_равно]",
                    })

            # Проверка [Rand]
            if "rand" in token_lower:
                # Должны быть скобки
                if "(" not in token:
                    findings.append({
                        "type": "FORMAT_LOGICAL_MALFORMED",
                        "severity": "warning",
                        "token": f"[{token}]",
                        "msg": "[Rand] требует скобок: [Rand(min, max)]",
                    })

            # Проверка [Plural] и [Replace]
            if any(x in token_lower for x in ["plural", "replace"]):
                if "(" not in token:
                    findings.append({
                        "type": "FORMAT_LOGICAL_MALFORMED",
                        "severity": "error",
                        "token": f"[{token}]",
                        "msg": f"[{token.split()[0] if token else '...'}] требует скобок с аргументами",
                    })

            # Проверка [Key:...]
            if token_lower.startswith("key"):
                if ":" not in token:
                    findings.append({
                        "type": "FORMAT_LOGICAL_MALFORMED",
                        "severity": "error",
                        "token": f"[{token}]",
                        "msg": "[Key:...] должен содержать двоеточие и имя ключа",
                    })

        return findings

    def _check_pawn_tokens(self, text: str, original: str, context: dict) -> list[dict]:
        """Специальная проверка токенов [PAWN_...]"""
        findings = []

        # Ищем все уникальные PAWN-токены
        pawn_tokens = re.findall(r'\[PAWN_(\w+)\b', text)
        known_tokens = {
            "gender", "possessive", "pronoun", "objective",
            "name_def", "name", "label", "pawn",
        }

        for token in set(pawn_tokens):
            if token.lower() not in known_tokens:
                findings.append({
                    "type": "FORMAT_UNKNOWN_PAWN_TOKEN",
                    "severity": "warning",
                    "token": token,
                    "msg": f"Неизвестный PAWN-токен: [PAWN_{token}]. Возможно, опечатка?",
                })

        # Проверяем, что [PAWN_gender] имеет оба варианта
        gender_pattern = r'\[PAWN_gender\s*\?\s*(.*?)\s*:\s*(.*?)\]'
        for match in re.finditer(gender_pattern, text, re.IGNORECASE):
            masculine = match.group(1).strip()
            feminine = match.group(2).strip()

            if not masculine or not feminine:
                findings.append({
                    "type": "FORMAT_INCOMPLETE_GENDER",
                    "severity": "error",
                    "msg": "[PAWN_gender] должен содержать и мужской, и женский варианты",
                })

            # Проверяем, не слишком ли похожи варианты (частая ошибка)
            if masculine and feminine:
                masculine_clean = re.sub(r'\[.*?\]', '', masculine)
                feminine_clean = re.sub(r'\[.*?\]', '', feminine)
                if masculine_clean == feminine_clean and masculine_clean:
                    findings.append({
                        "type": "FORMAT_GENDER_SAME",
                        "severity": "warning",
                        "msg": f"[PAWN_gender]: мужской и женский варианты совпадают ('{masculine_clean}') — верно ли это?",
                    })

        return findings

    def _check_links(self, text: str) -> list[dict]:
        """Проверяет теги <link>"""
        findings = []

        # <link=URL>текст</link>
        link_pattern = r'<link\s*=[^>]*>'
        links = re.finditer(link_pattern, text)

        for match in links:
            link_tag = match.group(0)

            # Проверяем наличие закрывающего </link>
            # (общее количество проверяется в _check_tag_pairs)

            # Проверяем, есть ли URL
            if '=' not in link_tag:
                findings.append({
                    "type": "FORMAT_LINK_NO_URL",
                    "severity": "error",
                    "msg": "Тег <link> не содержит URL: используйте <link=URL>...",
                })

        return findings

    def _check_tag_attributes(self, text: str) -> list[dict]:
        """Проверяет атрибуты в тегах"""
        findings = []

        # <color=...>
        color_tags = re.finditer(r'<color\s*=[^>]*>', text)
        for match in color_tags:
            attr = match.group(0)
            # Проверяем наличие значения
            if re.search(r'<color\s*=(?:\s*|$)', attr):
                findings.append({
                    "type": "FORMAT_TAG_NO_VALUE",
                    "severity": "error",
                    "tag": "color",
                    "msg": "Тег <color> не содержит значения цвета",
                })

        # <size=...>
        size_tags = re.finditer(r'<size\s*=[^>]*>', text)
        for match in size_tags:
            attr = match.group(0)
            if re.search(r'<size\s*=(?:\s*|$)', attr):
                findings.append({
                    "type": "FORMAT_TAG_NO_VALUE",
                    "severity": "error",
                    "tag": "size",
                    "msg": "Тег <size> не содержит значения размера",
                })

        return findings

    def _check_empty_tags(self, text: str) -> list[dict]:
        """Проверяет пустые теги (без содержимого)"""
        findings = []

        empty_tags = re.findall(r'<(b|i|u|color|size|link)\b[^>]*>\s*</\1>', text)
        if empty_tags:
            findings.append({
                "type": "FORMAT_EMPTY_TAG",
                "severity": "warning",
                "msg": f"Обнаружено пустых тегов: {len(empty_tags)}. Возможно, лишнее форматирование",
            })

        return findings

    def _compare_tag_structure(self, translated: str, original: str) -> list[dict]:
        """Сравнивает структуру тегов между оригиналом и переводом"""
        findings = []

        # Считаем теги в оригинале и переводе
        for tag_name in self.rules:
            open_pattern = rf"<{tag_name}\b"
            orig_count = len(re.findall(open_pattern, original))
            trans_count = len(re.findall(open_pattern, translated))

            if orig_count != trans_count:
                findings.append({
                    "type": "FORMAT_TAG_COUNT_MISMATCH",
                    "severity": "warning",
                    "tag": tag_name,
                    "msg": f"Разное количество тегов <{tag_name}>: оригинал={orig_count}, перевод={trans_count}",
                })

        # Считаем логические токены
        logical_pattern = r'\[[^\]]+(?:\?|:)\]'  # токены с ? или :
        orig_logical = set(re.findall(logical_pattern, original))
        trans_logical = set(re.findall(logical_pattern, translated))

        # Проверяем наличие PAWN_ токенов
        pawn_orig = set(re.findall(r'\[PAWN_\w+\b', original, re.IGNORECASE))
        pawn_trans = set(re.findall(r'\[PAWN_\w+\b', translated, re.IGNORECASE))

        missing_pawn = pawn_orig - pawn_trans
        extra_pawn = pawn_trans - pawn_orig

        if missing_pawn:
            findings.append({
                "type": "FORMAT_MISSING_PAWN_TOKEN",
                "severity": "error",
                "tokens": list(missing_pawn),
                "msg": f"В переводе отсутствуют PAWN-токены из оригинала: {missing_pawn}",
            })

        if extra_pawn:
            findings.append({
                "type": "FORMAT_EXTRA_PAWN_TOKEN",
                "severity": "warning",
                "tokens": list(extra_pawn),
                "msg": f"В переводе есть лишние PAWN-токены: {extra_pawn}",
            })

        return findings