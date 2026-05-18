# config/language_constants.py
"""
Централизованные константы для поддерживаемых языков.
"""

# Полный список поддерживаемых языков (все языки RimWorld 1.5+)
SUPPORTED_LANGUAGES = [
    # Основные языки
    "English",
    "Russian",
    "German",
    "French",
    "Spanish",
    "Italian",
    "Polish",
    "Portuguese",
    "PortugueseBrazilian",
    # Азиатские языки
    "Chinese",
    "ChineseSimplified",
    "ChineseTraditional",
    "Japanese",
    "Korean",
    "Thai",
    "Vietnamese",
    # Европейские языки
    "Czech",
    "Dutch",
    "Swedish",
    "Turkish",
    "Ukrainian",
    "Hungarian",
    "Romanian",
    "Catalan",
    # Другие языки
    "Arabic",
    "Finnish",
    "Norwegian",
    "Danish",
]

# Маппинг языков на короткие коды
LANGUAGE_CODE_MAP = {
    "russian": "ru",
    "english": "en",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "chinese": "zh",
    "chinesesimplified": "zh",
    "chinesetraditional": "zh-Hant",
    "japanese": "ja",
    "korean": "ko",
    "polish": "pl",
    "portuguese": "pt",
    "portuguesebrazilian": "pt-BR",
    "italian": "it",
    "czech": "cs",
    "dutch": "nl",
    "swedish": "sv",
    "turkish": "tr",
    "ukrainian": "uk",
    "hungarian": "hu",
    "romanian": "ro",
    "catalan": "ca",
    "arabic": "ar",
    "finnish": "fi",
    "norwegian": "no",
    "danish": "da",
    "thai": "th",
    "vietnamese": "vi",
}

# Язык по умолчанию
DEFAULT_SOURCE_LANGUAGE = "English"
DEFAULT_TARGET_LANGUAGE = "Russian"
DEFAULT_VERIFICATION_LANGUAGE = "Russian"
