# verification/checks/grammar_consistency_checker.py

class GrammarConsistencyChecker:
    """
    Проверка согласования родов и падежей в списках RulePackDef
    Стандарт 2026 года, поддержка русского и украинского языков
    """

    def __init__(self, lang_code="ru"):
        self.lang_code = lang_code.lower()

        # Типичные окончания для проверки родов и падежей
        self.SUFFIX_RULES = {
            'ru': {
                'mas': (['ый', 'ий', 'ой', 'ин', 'ов'], ['ая', 'ия', 'ое', 'ее']),
                'fem': (['ая', 'ия', 'ья'], ['ый', 'ий', 'ое', 'ее']),
                'neu': (['ое', 'ее'], ['ый', 'ий', 'ая', 'ия']),
                'gen': (['а', 'я', 'и', 'ы', 'ов', 'ей'], ['ый', 'ий', 'ая']),
                'dat': (['у', 'ю', 'е'], []),
                'acc': (['а', 'я', 'у', ''], []),
                'ins': (['ом', 'ым', 'ой', 'ей'], []),
                'prep': (['е', 'и'], [])
            },
            'uk': {
                'mas': (['ий', 'ий', 'ой', 'ин', 'ов'], ['а', 'я', 'е', 'є']),
                'fem': (['а', 'я', 'ья'], ['ий', 'ий', 'е', 'є']),
                'neu': (['е', 'є'], ['ий', 'ий', 'а', 'я']),
                'gen': (['а', 'я', 'и', 'у', 'ів', 'ей'], ['ий', 'ий', 'а']),
                'dat': (['ові', 'ю', 'еві'], []),
                'acc': (['а', 'я', ''], []),
                'ins': (['ом', 'им', 'ою', 'єю'], []),
                'prep': (['і', 'у', 'ові'], [])
            }
        }

        self.exceptions = {"судья", "папа", "дідусь", "чоловік"}

    def check_list_consistency(self, token_name, words):
        """
        Проверка согласованности списка токенов
        token_name: имя токена, например 'weapon_adjective_mas'
        words: список слов из RulePackDef
        """
        errors = []

        if self.lang_code not in self.SUFFIX_RULES:
            return errors

        rules = self.SUFFIX_RULES[self.lang_code]

        # Определяем ожидаемый род/падеж по суффиксу в названии токена
        expected_key = None
        for key in rules.keys():
            if f"_{key}" in token_name.lower():
                expected_key = key
                break

        if not expected_key:
            return errors

        allowed, forbidden = rules[expected_key]

        for word in words:
            word = word.strip().lower()
            if not word or word in self.exceptions:
                continue

            # Жесткая проверка окончаний
            if any(word.endswith(f) for f in forbidden):
                errors.append({
                    "type": "GENDER_MISMATCH",
                    "severity": "warning",
                    "token": token_name,
                    "word": word,
                    "expected": expected_key,
                    "msg": f"Слово '{word}' не соответствует ожидаемому роду/падежу {expected_key}"
                })

        return errors
