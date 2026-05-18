# verification/checks/lang_detector.py
import re


class LangDetector:
    """
    Детектор непереведенного английского текста
    Специальная логика для RulePackDef
    Стандарт 2026 года
    """

    def verify(self, text, original_text=None):
        errors = []

        # Если перевод 1-в-1 совпадает с оригиналом и там есть латиница
        if original_text and text.strip() == original_text.strip() and re.search(r'[a-zA-Z]{4,}', text):
            errors.append({
                "type": "CRITICAL_UNTRANSLATED",
                "severity": "error",
                "msg": "Текст полностью совпадает с оригиналом (не переведён)"
            })

        # Поиск английских слов длиннее 4 символов среди кириллицы
        eng_words = re.findall(r'\b[a-zA-Z]{5,}\b', text)
        if eng_words:
            errors.append({
                "type": "WARNING_ENG_WORD",
                "severity": "warning",
                "msg": f"Найдены английские слова: {', '.join(eng_words)}",
                "words": eng_words
            })

        # ✅ НОВОЕ: Проверка на смешанный язык (двухязычный контент)
        mixed_lang_errors = self._check_mixed_language(text)
        errors.extend(mixed_lang_errors)

        return errors

    def _check_mixed_language(self, text):
        """
        Проверяет наличие смешанного языка в тексте.
        Полезно для обнаружения случаев, когда в переводе остались английские слова
        рядом с переведёнными фразами.
        """
        errors = []
        
        if not text or not text.strip():
            return errors
            
        try:
            cyrillic_pattern = re.compile(r'[А-Яа-яЁё]')
            latin_pattern = re.compile(r'[A-Za-z]{4,}')
            
            has_cyrillic = bool(cyrillic_pattern.search(text))
            has_latin = bool(latin_pattern.search(text))
            
            if has_cyrillic and has_latin:
                latin_words = latin_pattern.findall(text)
                if len(latin_words) >= 3:
                    errors.append({
                        "type": "MIXED_LANGUAGE_CONTENT",
                        "severity": "warning",
                        "msg": f"Обнаружен смешанный язык: найдены английские слова '{', '.join(latin_words[:3])}' рядом с кириллицей",
                        "words": latin_words
                    })
        except Exception:
            pass
                
        return errors

    def verify_rulepack_line(self, xml_line):
        """Специальная проверка для строк RulePackDef -> значение"""
        errors = []
        if "->" in xml_line:
            # Извлекаем только правую часть (сам текст/результат правила)
            _, result = xml_line.split("->", 1)

            # Удаляем токены в скобках [pawn_nameDef], чтобы они не считались английским текстом
            clean_text = re.sub(r'\[.*?\]', '', result).strip()

            # Если после очистки от токенов остался английский текст
            if re.search(r'[a-zA-Z]{3,}', clean_text):
                errors.append({
                    "type": "RULEPACK_UNTRANSLATED_VAL",
                    "severity": "warning",
                    "msg": f"В результате правила найден английский текст: '{clean_text[:50]}'"
                })
        return errors
