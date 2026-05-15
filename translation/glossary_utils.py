MAX_GLOSSARY_SIZE = 5000

CATEGORY_PREFIXES = {
    "weapon": "weapons",
    "armor": "armor",
    "helmet": "armor",
    "apparel": "clothing",
    "cloth": "clothing",
    "steel": "materials",
    "wood": "materials",
    "metal": "materials",
    "plasteel": "materials",
    "component": "materials",
    "advanced": "materials",
    "plant": "plants",
    "tree": "plants",
    "berry": "plants",
    "crop": "plants",
}

LANG_CODE_MAP = {
    "russian": "ru", "english": "en", "german": "de", "french": "fr",
    "spanish": "es", "chinese": "zh", "japanese": "ja", "korean": "ko",
    "polish": "pl", "portuguese": "pt", "portuguesebrazilian": "pt-br",
    "italian": "it", "ukrainian": "uk", "czech": "cs", "dutch": "nl",
    "swedish": "sv", "turkish": "tr", "hungarian": "hu", "romanian": "ro",
    "arabic": "ar", "finnish": "fi", "norwegian": "no", "danish": "da",
    "thai": "th", "vietnamese": "vi", "catalan": "ca",
}


def get_lang_code_from_name(target_language: str) -> str:
    return LANG_CODE_MAP.get(target_language.lower(), target_language.lower()[:2])


def determine_category(term: str) -> str | None:
    term_lower = term.lower() if isinstance(term, str) else term
    for prefix, category in CATEGORY_PREFIXES.items():
        if prefix in term_lower:
            return category
    return None