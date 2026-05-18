# verification/checks/llm_detector.py
"""
Модуль детекции машинного перевода (LLM-детектор)
Специализируется на поиске галлюцинаций падежей и стилистики, характерных для нейросетевых переводов
Стандарт 2026 года для RimWorld 1.6+
"""

import re
from dataclasses import dataclass


@dataclass
class LLMIndicator:
    """Индикатор машинного перевода"""
    pattern: str
    description: str
    severity: str
    fix_suggestion: str = ""


class LLMDetector:
    """
    Детектор машинного перевода (LLM-галлюцинаций).

    Выявляет признаки нейросетевого перевода:
    - Нестандартные конструкции падежей
    - Излишняя «гладкость» и отсутствие естественных ошибок
    - Характерные для LLM стилистические шаблоны
    - Неправильные контекстные выборы
    """

    def __init__(self):
        self.indicators = self._build_indicators()

        # Типичные ошибки падежей, которые делают LLM (особенно при переводе с агл.)
        self.case_hallucinations = [
            # LLM путает творительный и предложный
            (r"при [а-я]{3,}ом\b", "Творительный падеж вместо предложного: 'при [чем-то]ом'"),
            # Лишний предлог или его отсутствие в сложных конструкциях
            (r"с целью для того чтобы\b", "Избыточный перевод с агл. to: 'с целью для того чтобы'"),
            # Характерная агл./LLM ошибка: it is -> это есть
            (r"это есть (\w+[аяиеё])\b", "LLM-перевод конструкции 'it is': используйте просто 'это' или 'это [прилагательное]'"),
            # Прямолинейный перевод there is/are
            (r"там (является|есть) [а-я]+", "Прямолинейный перевод there is/are: напишите естественно"),
            # Избыточное использование пассивного залога (характерно для нейросетей)
            (r"(был|была|было|были) (\w+ен|\w+ена|\w+ено|\w+ены) (кем-то|кем-либо)",
             "Канцелярит/LLM-перевод: пассивный залог + 'кем-то' — перефразируйте"),
            # Характерная ошибка: of = про/о (сверхбуквальный перевод)
            (r"о [а-я]{3,}е \b(\w{4,})\b", "Возможно, буквальный перевод of: проверьте контекст"),
            # Страдание от конструкции «make + do»
            (r"сделать (кто-то) (\w+ым|\w+ой)", "LLM-перевод make+прил: лучше 'заставить кого-то сделать что-то'"),
            # Страдательный залог там, где нужен активный
            (r"бывает? (\w+ен|\w+ена|\w+ено)", "Пассивный залог в описании обыденного: перефразируйте"),
        ]

        # LLM-style filler words and phrases
        self.llm_filler = [
            (r"\bкак бы\b", "Слишком разговорно/stilted — типично для машинного перевода"),
            (r"\bвполне очевидно(,)? что\b", "Шаблонное начало — характерно для LLM"),
            (r"\bдостаточно интересно(,)? что\b", "Шаблонное вступление — признак машинного текста"),
            (r"\bнеобходимо отметить\b", "Канцелярит — часто генерируется нейросетями"),
            (r"\bследует отметить\b", "Канцелярит — признак машинного перевода"),
        ]

        # Unnatural word choices (agl. artifacts)
        self.unatural_choices = [
            # Wrong lexical choice: house -> дом (OK) but building -> сооружение (LLM)
            (r"\b(сооружение|здание|конструкция)\b(?! (?:Def|XML|xml))",
             "Потенциально неестественный выбор слова — проверьте контекст (возможно, буквальный перевод)",
             ["building", "structure", "facility"]),
            # Overly complex for simple concepts
            (r"\bв связи с тем что\b", "Простая мысль в сложной форме — признак машинного перевода", []),
            (r"\bв силу того что\b", "Излишне усложнено — перефразируйте на 'поскольку' или 'потому что'", []),
        ]

        # LLM tendency to overuse certain stylistic constructions
        self.overuse_patterns = [
            (r"\bв\s+то\s+время\s+как\b", "Сравнительная конструкция — может быть признаком машинного перевода"),
            (r"\bнаряду\s+с\b", "Шаблонное сравнение — характерно для машинного текста"),
        ]

    def _build_indicators(self) -> list[LLMIndicator]:
        """Построить список индикаторов машинного перевода"""
        return [
            LLMIndicator(
                pattern=r"\b(является|представляет собой)\b.*\bкоторый\b",
                description="Перегруженное определительное прилагательное — характерно для LLM",
                severity="warning",
                fix_suggestion="Разбейте на два предложения или упростите",
            ),
            LLMIndicator(
                pattern=r"\b(важно|необходимо|следует)\b.*\bучитывать\b",
                description="Бюрократический/машинный стиль",
                severity="info",
                fix_suggestion="Упростите формулировку",
            ),
        ]

    def verify(self, text: str, original_text: str = "", context: dict = None) -> list[dict]:
        """
        Проверка текста на признаки машинного перевода.

        Args:
            text: Текст перевода
            original_text: Оригинальный текст (на английском)
            context: Контекст проверки (например, {'is_rulepack': True})

        Returns:
            Список найденных индикаторов
        """
        findings = []
        context = context or {}

        # 1. Проверка падежных галлюцинаций
        findings.extend(self._check_case_hallucinations(text))

        # 2. Проверка канцеляритов и LLM-шаблонов
        findings.extend(self._check_llm_fillers(text))

        # 3. Проверка неестественного выбора слов
        findings.extend(self._check_unnatural_words(text, original_text))

        # 4. Проверка перегруженных конструкций
        findings.extend(self._check_overuse_patterns(text))

        # 5. Проверка прямолинейного перевода
        if original_text:
            findings.extend(self._check_literal_translation(text, original_text))

        # 6. Для RulePackDef - специальные проверки
        if context.get("is_rulepack") or context.get("rulepack_check"):
            findings.extend(self._check_rulepack_llm_artifacts(text))

        # 7. Проверка индикаторов LLM
        findings.extend(self._check_llm_indicators(text))

        return findings

    def _check_case_hallucinations(self, text: str) -> list[dict]:
        """Проверяет типичные ошибки падежей от LLM"""
        findings = []
        for pattern, description in self.case_hallucinations:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append({
                    "type": "LLM_CASE_HALLUCINATION",
                    "severity": "warning",
                    "msg": description,
                    "pattern": pattern,
                })
        return findings

    def _check_llm_fillers(self, text: str) -> list[dict]:
        """Проверяет наличие LLM-шаблонов и фраз-паразитов"""
        findings = []
        for pattern, description in self.llm_filler:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                findings.append({
                    "type": "LLM_FILLER_PATTERN",
                    "severity": "info",
                    "msg": f"{description} (найдено: {matches[0]})",
                })
        return findings

    def _check_unnatural_words(self, text: str, original: str) -> list[dict]:
        """Ищет неестественный выбор слов (буквальный перевод)"""
        findings = []
        for pattern, description, triggers in self.unatural_choices:
            if re.search(pattern, text, re.IGNORECASE):
                # Проверяем, был ли в оригинале триггер
                has_trigger = any(
                    tr.lower() in original.lower()
                    for tr in triggers
                ) if original else True
                findings.append({
                    "type": "LLM_UNNATURAL_WORD",
                    "severity": "warning" if has_trigger else "info",
                    "msg": f"{description} {f'(ориг. содержит {triggers})' if has_trigger else ''}",
                    "matched": re.search(pattern, text, re.IGNORECASE).group(0),
                })
        return findings

    def _check_overuse_patterns(self, text: str) -> list[dict]:
        """Проверяет избыточное использование стилистических конструкций"""
        findings = []
        for pattern, description in self.overuse_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append({
                    "type": "LLM_OVERUSE_PATTERN",
                    "severity": "info",
                    "msg": description,
                })
        return findings

    def _check_literal_translation(self, translated: str, original: str) -> list[dict]:
        """Проверяет признаки прямолинейного (словарного) перевода"""
        findings = []

        # Слишком длинные предложения с множеством союзов — признак машинного перевода
        long_sentences = re.split(r'[.!?]+', translated)
        for sent in long_sentences:
            words = sent.split()
            if len(words) > 35:
                findings.append({
                    "type": "LLM_LONG_SENTENCE",
                    "severity": "warning",
                    "msg": f"Очень длинное предложение ({len(words)} слов) — типично для машинного перевода",
                })

        # Проверка типичных агл. конструкций
        agl_patterns = [
            (r"\bit is (clear|obvious|evident) that\b", "Прямолинейный перевод it is clear that"),
            (r"\bthis is (important|crucial|essential)\b", "Прямолинейный this is [adj] — упростите"),
            (r"\bdue to the fact that\b", "Буквальный перевод due to the fact that — используйте 'поскольку'"),
            (r"\bin order to\b", "In order to — избыточно, достаточно просто 'чтобы' или 'для'"),
        ]

        for pattern, description in agl_patterns:
            if re.search(pattern, translated, re.IGNORECASE):
                findings.append({
                    "type": "LLM_LITERAL_TRANSLATION",
                    "severity": "warning",
                    "msg": description,
                })

        return findings

    def _check_rulepack_llm_artifacts(self, text: str) -> list[dict]:
        """Особые проверки для RulePackDef"""
        findings = []

        # LLM часто добавляет лишние слова в короткие rule-результаты
        li_contents = re.findall(r"<li>(.*?)\)?->(.*?)(?:</li>|$)", text, re.DOTALL)
        for full, result in li_contents:
            clean_result = re.sub(r'\[.*?\]', '', result).strip()
            words = clean_result.split()
            # Слишком длинный или сложный результат для простого правила
            if len(words) > 20:
                findings.append({
                    "type": "LLM_RULEPACK_VERBOSE",
                    "severity": "warning",
                    "msg": f"Правило генерирует слишком длинный/сложный результат ({len(words)} слов) — возможна LLM-модификация",
                    "preview": clean_result[:80] + "..." if len(clean_result) > 80 else clean_result,
                })

        return findings

    def _check_llm_indicators(self, text: str) -> list[dict]:
        """Проверка общих индикаторов LLM-генерации"""
        findings = []
        for indicator in self.indicators:
            if re.search(indicator.pattern, text, re.IGNORECASE):
                findings.append({
                    "type": "LLM_STYLE_INDICATOR",
                    "severity": indicator.severity,
                    "msg": indicator.description,
                    "fix_suggestion": indicator.fix_suggestion,
                })
        return findings

    def verify_batch(self, texts: list[tuple[str, str]], context: dict = None) -> list[list[dict]]:
        """Пакетная проверка текста"""
        return [self.verify(text, original, context) for text, original in texts]
