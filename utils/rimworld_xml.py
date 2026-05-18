# Импорт настроек для фильтрации тегов

import re

# Паттерн для фильтрации векторов и кортежей (например, "(0.92, 1 ,0.92)", "(0, 0, 0.42)")
VECTOR_PATTERN = re.compile(r'^\s*\([^)]*\)\s*$')

# Полный список переводимых тегов RimWorld 
TRANSLATABLE_TAGS = {
    # Базовые теги
    "label",
    "labelShort",
    "labelPlural",
    "labelNoun",
    "labelNounPretty",
    "description",
    "desc",
    "text",
    "title",
    "tooltip",
    "helpText",
    # Специфичные Def-теги
    "reportString",
    "jobString",
    "ingestCommandString",
    "ingestReportString",
    "skillLabel",
    "pawnLabel",
    "pawnLabelNoun",
    "pawnSingular",
    "pawnsPlural",
    "deathMessage",
    "useLabel",
    "verb",
    "gerund",
    "beginLetterLabel",
    "beginLetter",
    "recoveryMessage",
    "letterLabel",
    "letterText",
    "notification",
    "baseInspectLine",
    # Teги для Ideology
    "ideoName",
    "member",
    "theme",
    "leaderTitle",
    "structureLabel",
    # Теги для RecipeDef
    "jobString",
    # Теги для ThingDef (материалы)
    "stuffAdjective",
    "adjective",
    # Теги для QuestDef
    "summary",
    # Теги для BackstoryDef
    "titleShort",
    "titleFemale",
    "titleMale",
    "baseDesc",
    # Теги для Weapon/Verb
    "commandDesc",
    "commandLabel",
    "chargeNoun",
    "cooldownGerund",
    # Дополнительные теги из Text-grabber
    "customLabel",
    "customLetterLabel",
    "customLetterText",
    "outOfFuelMessage",
    "name",
    # slateRef теги для QuestScriptDef (из Text-grabber)
    "slateRef",
    "slate",
}

# Частичные совпадения тегов 
def _is_vector_or_tuple(text: str) -> bool:
    """
    Проверяет, является ли текст вектором или кортежем.
    Например: "(0.92, 1 ,0.92)", "(0, 0, 0.42)", "(1,0,0)"
    
    Args:
        text: Проверяемый текст
        
    Returns:
        True если текст выглядит как вектор или кортеж
    """
    if not text:
        return False
    return bool(VECTOR_PATTERN.match(text))


PARTIAL_TAG_MATCHES = [
    "Message",
    "Label",
    "Title",
    "Text",
    "gerund",
    "Explanation",
    "description",
    "Hint",
    "Name",
]


def extract_subfields(
    element,
    prefix="",
    logger=None,
    whitelist_tags=None,
    blacklist_tags=None,
    blacklist_patterns=None,
    min_text_length=2,
    max_text_length=200,
    partial_tag_matches=None,
    enable_space_fallback=True,
):
    """
    Извлекает переводимые поля из XML элемента с учетом вложенности и списков.

    Args:
        element: XML элемент для извлечения
        prefix: Префикс ключа (для вложенности)
        logger: Логгер
        whitelist_tags: Набор тегов для извлечения (по умолчанию TRANSLATABLE_TAGS)
        blacklist_tags: Набор тегов для пропуска
        blacklist_patterns: Список паттернов для фильтрации по ключу
        min_text_length: Минимальная длина текста для извлечения
        max_text_length: Максимальная длина текста
        partial_tag_matches: Список частичных совпадений тегов
        enable_space_fallback: Включить fallback по пробелу
    """
    # Значения по умолчанию
    if whitelist_tags is None:
        whitelist_tags = TRANSLATABLE_TAGS
    if blacklist_tags is None:
        blacklist_tags = set()
    if blacklist_patterns is None:
        blacklist_patterns = []
    if partial_tag_matches is None:
        partial_tag_matches = PARTIAL_TAG_MATCHES

    fields = {}
    list_counters = {}

    for child in element:
        tag = child.tag
        if not isinstance(tag, str):
            continue

        # ✅ Пропускаем blacklist теги
        if tag in blacklist_tags:
            continue

        # ✅ Пропускаем defName (всегда)
        if tag == "defName":
            continue

        # ✅ Для RulePackDef: полностью пропускаем rulesStrings как обычное поле
        # Все тексты должны извлекаться только как ._list через <li> элементы
        full_key = f"{prefix}.{tag}" if prefix else tag
        if "rulePack.rulesStrings" in full_key and tag == "rulesStrings":
            # Пропускаем rulesStrings - его дети <li> обработаются рекурсивно
            if len(child) > 0:
                fields.update(
                    extract_subfields(
                        child,
                        full_key,
                        logger,
                        whitelist_tags,
                        blacklist_tags,
                        blacklist_patterns,
                        min_text_length,
                    )
                )
            continue

        # Обработка списков <li>
        if tag == "li":
            # RulePackDef: собираем <li> в список с уникальным ключом
            if "rulePack.rulesStrings" in prefix:
                # ✅ ИСПРАВЛЕНО: Используем полный префикс включая defName
                # Это гарантирует что списки разных RulePackDef не перемешиваются
                cur_pre = prefix
                if child.text and child.text.strip():
                    text = child.text.strip()
                    if len(text) >= min_text_length and len(text) < max_text_length:
                        fields[f"{cur_pre}._list"] = fields.get(f"{cur_pre}._list", []) + [text]
                continue
            else:
                idx = list_counters.get("li", 0)
                list_counters["li"] = idx + 1
                cur_pre = f"{prefix}.{idx}" if prefix else str(idx)
        else:
            cur_pre = full_key

        # ✅ Проверяем whitelist — тег должен быть в списке разрешённых
        tag_matches_whitelist = tag in whitelist_tags
        if not tag_matches_whitelist and whitelist_tags and partial_tag_matches:
            for partial in partial_tag_matches:
                if partial.lower() in tag.lower():
                    tag_matches_whitelist = True
                    break

        if whitelist_tags and not tag_matches_whitelist:
            # Fallback по пробелу
            if enable_space_fallback and child.text and child.text.strip() and " " in child.text:
                text = child.text.strip()
                if len(text) >= min_text_length and len(text) < max_text_length:
                    fields[cur_pre] = text

            # Рекурсивно обрабатываем детей
            if len(child) > 0:
                fields.update(
                    extract_subfields(
                        child,
                        cur_pre,
                        logger,
                        whitelist_tags,
                        blacklist_tags,
                        blacklist_patterns,
                        min_text_length,
                    )
                )
            continue

        # ✅ Проверяем blacklist_patterns
        if blacklist_patterns:
            key_lower = cur_pre.lower()
            if any(pattern.lower() in key_lower for pattern in blacklist_patterns):
                continue

        # ✅ Извлекаем текст
        if child.text and child.text.strip():
            text = child.text.strip()
            if len(text) >= min_text_length:
                # ✅ Пропускаем вектора и кортежи (например, "(0.92, 1, 0.92)")
                if _is_vector_or_tuple(text):
                    continue
                fields[cur_pre] = text

        # Рекурсивная обработка детей
        if len(child) > 0:
            fields.update(
                extract_subfields(
                    child,
                    cur_pre,
                    logger,
                    whitelist_tags,
                    blacklist_tags,
                    blacklist_patterns,
                    min_text_length,
                )
            )

    return fields
