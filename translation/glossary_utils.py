MAX_GLOSSARY_SIZE = 1500

CATEGORY_PREFIXES = {
    # Weapons
    "mortar": "weapons",
    "rocket launcher": "weapons",
    "sniper rifle": "weapons",
    "shotgun": "weapons",
    "rifle": "weapons",
    "pistol": "weapons",
    "knife": "weapons",
    "club": "weapons",
    "stick": "weapons",
    "axe": "weapons",
    "chainsaw": "weapons",
    "laser": "weapons",
    "plasma": "weapons",
    "neutron": "weapons",
    "explosive": "weapons",
    "frag": "weapons",
    "high explosive": "weapons",
    "smoke": "weapons",
    "incendiary": "weapons",
    "emp": "weapons",
    "turret": "weapons",
    "auto turret": "weapons",
    "flak cannon": "weapons",

    # Armor/Clothing
    "armor": "armor",
    "helmet": "armor",
    "apparel": "clothing",
    "uniform": "clothing",
    "suit": "clothing",

    # Materials
    "steel": "materials",
    "wood": "materials",
    "metal": "materials",
    "plasteel": "materials",
    "iron": "materials",
    "component": "materials",
    "advanced component": "materials",
    "cloth": "materials",
    "material": "materials",

    # Plants
    "plant": "plants",
    "tree": "plants",
    "berry": "plants",
    "crop": "plants",
    "flower": "plants",
    "fruit": "plants",
    "seed": "plants",
    "leaf": "plants",
    "root": "plants",
    "stem": "plants",
    "branch": "plants",

    # Pawns/Characters
    "pawn": "pawns",
    "colonist": "pawns",
    "pawnkind": "pawns",
    "character": "pawns",
    "creature": "pawns",
    "monster": "pawns",
    "baby": "pawns",
    "child": "pawns",
    "adult": "pawns",
    "old": "pawns",

    # Skills
    "skill": "skills",
    "passion": "skills",
    "learning": "skills",
    "study": "skills",
    "intelligence": "skills",
    "artistic": "skills",
    "physical": "skills",
    "manual": "skills",
    "crafting": "skills",
    "construction": "skills",
    "farming": "skills",
    "mining": "skills",
    "doctoring": "skills",
    "shooting": "skills",
    "melee": "skills",
    "animal handling": "skills",
    "animal training": "skills",
    "animal breeding": "skills",
    "plant cutting": "skills",
    "plant growing": "skills",
    "cooking": "skills",
    "smithing": "skills",
    "tailoring": "skills",

    # Health/Medical
    "health": "medical",
    "injury": "medical",
    "disease": "medical",
    "infection": "medical",
    "treatment": "medical",
    "surgery": "medical",
    "wound": "medical",
    "bleeding": "medical",
    "fracture": "medical",
    "pain": "medical",
    "body": "medical",
    "head": "medical",
    "arm": "medical",
    "leg": "medical",
    "torso": "medical",

    # Rooms/Buildings
    "room": "buildings",
    "bedroom": "buildings",
    "barracks": "buildings",
    "hospital": "buildings",
    "prison": "buildings",
    "kitchen": "buildings",
    "dining": "buildings",
    "workshop": "buildings",
    "manufacturing": "buildings",
    "research": "buildings",
    "wall": "buildings",
    "floor": "buildings",
    "roof": "buildings",
    "door": "buildings",
    "window": "buildings",
    "furniture": "buildings",
    "table": "buildings",
    "chair": "buildings",
    "chest": "buildings",
    "storage": "buildings",

    # Technology
    "tech level": "technology",
    "neolithic": "technology",
    "medieval": "technology",
    "industrial": "technology",
    "spacer": "technology",
    "elite": "technology",

    # Quality
    "quality": "quality",
    "masterwork": "quality",
    "legendary": "quality",
    "awful": "quality",
    "poor": "quality",
    "normal": "quality",
    "good": "quality",
    "excellent": "quality",

    # Food
    "food": "food",
    "meal": "food",
    "fresh": "food",
    "rotting": "food",
    "raw": "food",
    "cooked": "food",

    # Social
    "social": "social",
    "relationship": "social",
    "opinion": "social",
    "friend": "social",
    "enemy": "social",
    "family": "social",
    "kin": "social",
    "love": "social",
    "marriage": "social",
    "war": "social",
    "peace": "social",
    "diplomacy": "social",

    # World/Biome
    "biome": "world",
    "temperature": "world",
    "cold": "world",
    "heat": "world",
    "flood": "world",
    "drought": "world",
    "storm": "world",
    "snow": "world",
    "rain": "world",
    "season": "world",
    "forest": "world",
    "grove": "world",
    "garden": "world",
    "field": "world",
    "meadow": "world",
    "plain": "world",

    # Mood/Psychology
    "mood": "psychology",
    "mental break": "psychology",
    "thought": "psychology",
    "need": "psychology",
    "inspiration": "psychology",
    "hedonist": "psychology",
    "ascetic": "psychology",
    "psychopath": "psychology",

    # Animals
    "beast": "animals",
    "animal": "animals",
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
    term_words = term_lower.split()
    
    # First check for exact matches (term is a category keyword itself)
    for keyword, category in CATEGORY_PREFIXES.items():
        if term_lower == keyword:
            return category
    
    # Then check for prefix matches
    for prefix, category in CATEGORY_PREFIXES.items():
        if prefix in term_lower:
            return category
        for word in term_words:
            if word.startswith(prefix) or prefix in word:
                return category
    return None