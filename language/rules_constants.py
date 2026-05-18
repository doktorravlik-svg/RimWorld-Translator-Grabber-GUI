from dataclasses import dataclass
from typing import Dict, List, Set, Optional

@dataclass
class LanguageConfig:
    code: str
    name: str
    capitalizes_nouns: bool
    capitalizes_sentence_start: bool
    capitalizes_proper_nouns: bool
    has_gender: bool
    has_cases: bool
    pronoun_cases: Dict[str, Dict[str, str]]
    fuzzy_defname_threshold: int = 80
    fuzzy_field_threshold: int = 90

PLACEHOLDER_PATTERNS = [
    r'\{0\}', r'\{1\}', r'\{\d+\}',
    r'%s', r'%d',
    r'\$([A-Za-z_][A-Za-z0-9_]*)',
    r'\[[A-Za-z_]+\]',
    r'\(\^Cap\)',
    r'\<\/?li\>',
    r'\\n',
]

UNTRANSLATABLE_TERMS = {"RimWorld", "Ludeon", "Steam", "Tynan", "rjw", "cum"}

CORRECTION_RULES = {
    # RU
    " егоная ": " его ", " еёная ": " её ", " ихняя ": " их ", "тся ": "ться ",
    # UK
    " самий кращий ": " найкращий ",
    " люба помилка ": " будь-яка помилка ",
    " на протязі ": " протягом ",
    " приймає участь ": " бере участь ",
    # Исправление битых тегов RimWorld
    "< li >": "<li>",
    "< /li >": "</li>",
    "<li> ": "<li>",
    " </li>": "</li>",
    "( ^Cap)": "(^Cap)",
    "(^ Cap)": "(^Cap)",
}

# Карта замены символов для предотвращения смешивания алфавитов
ALPHABET_FIX_MAP = {
    'uk': {
        'ы': 'и', 'э': 'е', 'ё': 'йо', 'ъ': "'",
        'i': 'і', # Замена латинской i на украинскую і
    },
    'ru': {
        'і': 'и', 'ї': 'и', 'є': 'е', 'ґ': 'г'
    }
}

PRONOUN_DECLENSIONS: Dict[str, LanguageConfig] = {
    'ru': LanguageConfig(
        code='ru', name='Русский', capitalizes_nouns=False,
        capitalizes_sentence_start=True, capitalizes_proper_nouns=True,
        has_gender=True, has_cases=True,
        pronoun_cases={
            'я': {'им': 'я', 'род': 'меня', 'дат': 'мне', 'вин': 'меня', 'твор': 'мной', 'пред': 'мне'},
            'он': {'им': 'он', 'род': 'его', 'дат': 'ему', 'вин': 'его', 'твор': 'им', 'пред': 'нем'},
            'она': {'им': 'она', 'род': 'её', 'дат': 'ей', 'вин': 'её', 'твор': 'ею', 'пред': 'ней'},
            'они': {'им': 'они', 'род': 'их', 'дат': 'им', 'вин': 'их', 'твор': 'ими', 'пред': 'них'},
            'пешка': {'им': 'пешка', 'род': 'пешки', 'дат': 'пешке', 'вин': 'пешку', 'твор': 'пешкой', 'пред': 'пешке'},
        },
        fuzzy_defname_threshold=80,
        fuzzy_field_threshold=90,
    ),
    'uk': LanguageConfig(
        code='uk', name='Українська', capitalizes_nouns=False,
        capitalizes_sentence_start=True, capitalizes_proper_nouns=True,
        has_gender=True, has_cases=True,
        pronoun_cases={
            'я': {'им': 'я', 'род': 'мене', 'дат': 'мені', 'вин': 'мене', 'твор': 'мною', 'пред': 'мені'},
            'він': {'им': 'він', 'род': 'його', 'дат': 'йому', 'вин': 'його', 'твор': 'ним', 'пред': 'ньому'},
            'вона': {'им': 'вона', 'род': 'її', 'дат': 'їй', 'вин': 'її', 'твор': 'нею', 'пред': 'ній'},
            'пішак': {'им': 'пішак', 'род': 'пішака', 'дат': 'пішаку', 'вин': 'пішака', 'твор': 'пішаком', 'пред': 'пішаку'},
        },
        fuzzy_defname_threshold=85,
        fuzzy_field_threshold=92,
    ),
    'en': LanguageConfig(
        code='en', name='English', capitalizes_nouns=False,
        capitalizes_sentence_start=True, capitalizes_proper_nouns=True,
        has_gender=False, has_cases=False,
        pronoun_cases={
            'i': {'им': 'I', 'род': 'me', 'дат': 'me', 'вин': 'me', 'твор': 'with me', 'пред': 'at me'},
            'he': {'им': 'he', 'род': 'him', 'дат': 'him', 'вин': 'him', 'твор': 'with him', 'пред': 'at him'},
        },
        fuzzy_defname_threshold=85,
        fuzzy_field_threshold=92,
    ),
    'de': LanguageConfig(
        code='de', name='Deutsch', capitalizes_nouns=True,
        capitalizes_sentence_start=True, capitalizes_proper_nouns=True,
        has_gender=True, has_cases=True,
        pronoun_cases={
            'ich': {'им': 'ich', 'род': 'mir', 'дат': 'mir', 'вин': 'mich', 'твор': 'mit mir', 'пред': 'bei mir'},
        },
        fuzzy_defname_threshold=82,
        fuzzy_field_threshold=91,
    ),
}
