# grabber_settings.py
# Расширенные правила извлечения текста, вдохновлённые Text-grabber (kamikadza13/Text-grabber).

# --- Явный список тегов, которые мы хотим извлекать из Defs и Languages
WHITELIST_TAGS = {
    # основные
    "label", "labelShort", "pawnLabel", "pawnLabelNoun", "labelNoun", "labelNounPretty",
    "description", "reportString", "jobString", "verb", "gerund", "helpText",
    # inspect / UI
    "baseInspectLine", "inspectString", "explanation", "explanationText", "explanationLabel",
    "summary", "hint", "tooltip", "useLabel", "beginLetterLabel", "beginLetter",
    "recoveryMessage", "deathMessage", "text", "title",
    # stages / menu / settings
    "stages", "title", "menuLabel", "settingsLabel", "settingsDesc", "skillLabel",
    # letters / notifications
    "letterLabel", "letterText", "notification", "notificationLabel",
    # fallback common tokens
    "labelNoun", "jobString", "reportString"
}

# --- Теги, которые категорически НЕ хотим вытаскивать (технические)
BLACKLIST_TAGS = {
    "defName", "modContentPack", "modMetaData", "Abstract",
    "workerClass", "driverClass", "graphicData", "texture", "sound",
    "costList", "thingClass", "statBases", "comps", "verbs", "verbsProperties"
}

# --- Префиксы/фрагменты, при совпадении с которыми ключ пропускается
BLACKLIST_PATTERNS = [
    "internal_", "debug_", "tmp_", "icon", "texture", "sprite", "gfx", "xmlextensions",
    "sound_", "audio_", "shader", "mesh", "costList", "workGiver", "workerClass"
]

# --- Ключи, которые в Keyed-файлах следует записывать как прямые теги в целевой Language
# (добавляйте сюда ключи, которые в исходном моде используются как глобальные прямые строки)
KEYED_AS_DIRECT = {
    # примеры (добавьте по необходимости):
    # "SomeGlobalLabel", "Another_Global_Key"
}

# --- Опции поведения
# Если True — использовать агрессивный grabber как последний шанс (может добавить шум)
AGGRESSIVE_FALLBACK = False

# --- Дополнительные настройки (порог/фильтры)
# Минимальная длина строки, чтобы считать её полезной (1 — отключено)
MIN_TEXT_LENGTH = 2

# Список суффиксов, которые часто означают UI‑поле и должны быть в приоритете
PRIORITY_SUFFIXES = {"label", "description", "reportString", "jobString", "title", "text", "tooltip"}
