# verification/checks/rulepack_validator.py
import re


class RulePackValidator:
    """
    Валидатор RulePackDef для RimWorld 1.6+
    Стандарт 2026 года, проверка синтаксиса, токенов и весов
    """

    VANILLA_TOKENS = {
        "pawn_nameDef", "pawn_label", "pawn_gender", "pawn_pronoun",
        "pawn_possessive", "thing_label", "faction_name", "count"
    }

    def verify(self, xml_content):
        errors = []

        # 1. Проверка синтаксиса "токен -> текст"
        li_contents = re.findall(r"<li>(.*?)</li>", xml_content)
        for content in li_contents:
            if "->" not in content:
                errors.append({
                    "type": "RULEPACK_INVALID_SYNTAX",
                    "severity": "error",
                    "content": content[:60],
                    "msg": "Отсутствует стрелка '->' в определении правила"
                })
            elif "—" in content or "–" in content:
                errors.append({
                    "type": "RULEPACK_WRONG_ARROW",
                    "severity": "error",
                    "content": content[:60],
                    "msg": "Используйте '->' вместо тире"
                })

        # 2. Проверка битых ссылок на токены
        defined = set(re.findall(r"(\w+)->", xml_content))
        used = set(re.findall(r"\[(\w+)\]", xml_content))

        for u in used:
            if u not in defined and u not in self.VANILLA_TOKENS:
                errors.append({
                    "type": "RULEPACK_UNKNOWN_TOKEN",
                    "severity": "warning",
                    "token": u,
                    "msg": f"Токен [{u}] используется, но не определен внутри этого RulePackDef"
                })

        # 3. Проверка весов
        errors.extend(self.verify_weights(xml_content))

        return errors

    def verify_weights(self, xml_line, original_line=None, full_analysis=False):
        """
        Комплексная весовая валидация для RulePackDef:
        - Формат весов (скобки, точки, запятые)
        - Проверку потерь весов при переводе
        - Балансировку весов (пропорции между правилами)
        """
        errors = []

        # Поиск неправильного разделителя (запятая)
        if re.search(r"<li>\(\d+,\d+\)", xml_line):
            errors.append({
                "type": "RULEPACK_WEIGHT_COMMA",
                "severity": "error",
                "msg": "Используйте точку в весах: (2.5) вместо (2,5)"
            })

        # Поиск веса без скобок
        if re.search(r"<li>\d+\.\d+->", xml_line):
            errors.append({
                "type": "RULEPACK_WEIGHT_NO_BRACKETS",
                "severity": "error",
                "msg": "Вес должен быть в скобках: (1.5)name->..."
            })

        # Сверка с оригиналом - потеря веса
        if original_line:
            orig_weight = re.search(r"\((.*?)\)", original_line)
            tran_weight = re.search(r"\((.*?)\)", xml_line)

            if orig_weight and not tran_weight:
                errors.append({
                    "type": "RULEPACK_WEIGHT_LOST",
                    "severity": "warning",
                    "msg": f"В оригинале был вес ({orig_weight.group(1)}), а в переводе он утерян"
                })

        # Полный анализ балансировки весов
        if full_analysis:
            weights = re.findall(r"\(([\d\.]+)\)", xml_line)
            if len(weights) > 1:
                try:
                    weight_values = [float(w) for w in weights]
                    total = sum(weight_values)
                    avg = total / len(weight_values)
                    # Проверка на сильный дисбаланс
                    max_weight = max(weight_values)
                    min_weight = min(weight_values)
                    if max_weight > 0 and min_weight / max_weight < 0.1 and max_weight > 5.0:
                        errors.append({
                            "type": "RULEPACK_WEIGHT_IMBALANCE",
                            "severity": "warning",
                            "msg": f"Сильный дисбаланс весов: min={min_weight}, max={max_weight} (соотношение {min_weight/max_weight:.2%})"
                        })
                except (ValueError, ZeroDivisionError):
                    pass

        return errors
