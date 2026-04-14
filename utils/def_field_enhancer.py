# utils/def_field_enhancer.py
"""
Улучшитель Def-ов - добавляет недостающие поля для определённых типов Def.

Аналог elem_tag_check из Text-grabber.

Добавляет:
- PawnKindDef: labelPlural для lifeStages
- DamageDef: deathMessage
- ThingDef: stuffAdjective, verbs/label
- FactionDef: pawnSingular, leaderTitle
- VEF.Abilities.AbilityDef: jobReportString, verbProperties/label
- BackstoryDef: titleFemale, titleShortFemale
- TraitDef: labelFemale
"""

import xml.etree.ElementTree as ET


def enhance_def_element(elem: ET.Element) -> None:
    """
    Проверяет тип Def и добавляет недостающие поля.

    Args:
        elem: XML элемент Def
    """
    tag = elem.tag

    if tag == "PawnKindDef":
        _enhance_pawn_kind_def(elem)
    elif tag == "DamageDef":
        _enhance_damage_def(elem)
    elif tag == "ThingDef" or tag == "AlienRace.ThingDef_AlienRace":
        if tag == "AlienRace.ThingDef_AlienRace":
            elem.tag = "ThingDef"
        _enhance_thing_def(elem)
    elif tag == "FactionDef":
        _enhance_faction_def(elem)
    elif tag == "VEF.Abilities.AbilityDef":
        _enhance_vef_ability_def(elem)
    elif tag == "BackstoryDef":
        _enhance_backstory_def(elem)
    elif tag == "TraitDef":
        _enhance_trait_def(elem)
    elif tag == "QuestScriptDef":
        _enhance_quest_script_def(elem)


def _enhance_pawn_kind_def(elem: ET.Element) -> None:
    """PawnKindDef: добавляет labelPlural для каждого lifeStages/li."""
    life_stages = elem.find("lifeStages")
    if life_stages is None:
        return

    orig_label = _get_text(elem.find("label")) or _get_text(elem.find("pawnLabel")) or "pawn"

    for li in life_stages:
        if not isinstance(li.tag, str):
            continue

        # Берём label из этого lifeStage или из родительского
        label = _get_text(li.find("label")) or orig_label
        if not label:
            continue

        # Добавляем labelPlural если нет
        if li.find("labelPlural") is None:
            plural_elem = ET.SubElement(li, "labelPlural")
            plural_elem.text = f"{label}s"


def _enhance_damage_def(elem: ET.Element) -> None:
    """DamageDef: добавляет deathMessage если отсутствует."""
    if elem.find("deathMessage") is not None:
        return

    parent_name = elem.get("ParentName", "")
    death_message = ET.SubElement(elem, "deathMessage")

    # Дефолтные deathMessage для разных типов урона
    death_messages = {
        "Flame": "{0} has burned to death.",
        "CutBase": "{0} has been cut to death.",
        "Cut": "{0} has been cut to death.",
        "BluntBase": "{0} has been beaten to death.",
        "Blunt": "{0} has been beaten to death.",
        "Scratch": "{0} has been shredded to death.",
        "Bite": "{0} has been bitten to death.",
        "Bomb": "{0} has been killed in an explosion.",
        "Arrow": "{0} has been shot.",
        "Bullet": "{0} has been shot.",
    }

    death_message.text = death_messages.get(parent_name, "{0} has been killed.")


def _enhance_thing_def(elem: ET.Element) -> None:
    """ThingDef: добавляет verbs/label, stuffAdjective."""
    # Добавляем label в verbs если есть verbClass
    verbs = elem.find("verbs")
    if verbs is not None:
        for li in verbs:
            if li.tag in ("li",) or li.tag.isdigit():
                verb_class = li.find("verbClass")
                if verb_class is not None and li.find("label") is None:
                    label_elem = ET.SubElement(li, "label")
                    label_elem.text = "\u3004"  # Маркер для перевода

    # Добавляем stuffAdjective в stuffProps
    stuff_props = elem.find("stuffProps")
    if stuff_props is not None and stuff_props.find("stuffAdjective") is None:
        label = _get_text(elem.find("label")) or "material"
        stuff_adjective = ET.SubElement(stuff_props, "stuffAdjective")
        stuff_adjective.text = label


def _enhance_faction_def(elem: ET.Element) -> None:
    """FactionDef: добавляет pawnSingular и leaderTitle."""
    if elem.find("pawnSingular") is None:
        pawn_singular = ET.SubElement(elem, "pawnSingular")
        pawn_singular.text = "member"

    if elem.find("leaderTitle") is None:
        leader_title = ET.SubElement(elem, "leaderTitle")
        leader_title.text = "leader"


def _enhance_vef_ability_def(elem: ET.Element) -> None:
    """VEF.Abilities.AbilityDef: добавляет jobReportString и verbProperties/label."""
    # Добавляем jobReportString
    if elem.find("jobReportString") is None:
        job_report = ET.SubElement(elem, "jobReportString")
        job_report.text = "Using ability: {0}"

    # Добавляем verbProperties/label
    label_text = _get_text(elem.find("label"))
    if not label_text:
        return

    verb_props = elem.find("verbProperties")
    if verb_props is None:
        verb_props = ET.SubElement(elem, "verbProperties")

    if verb_props.find("label") is None:
        label_elem = ET.SubElement(verb_props, "label")
        label_elem.text = label_text


def _enhance_backstory_def(elem: ET.Element) -> None:
    """BackstoryDef: добавляет titleFemale, titleShortFemale."""
    title = _get_text(elem.find("title")) or _get_text(elem.find("titleShort")) or ""

    if elem.find("titleFemale") is None:
        title_female = ET.SubElement(elem, "titleFemale")
        title_female.text = title

    if elem.find("titleShortFemale") is None:
        title_short_female = ET.SubElement(elem, "titleShortFemale")
        title_short_female.text = title


def _enhance_trait_def(elem: ET.Element) -> None:
    """TraitDef: добавляет labelFemale для каждого degreeDatas/li."""
    degree_datas = elem.find("degreeDatas")
    if degree_datas is None:
        return

    for li in degree_datas:
        if li.find("labelFemale") is None:
            label = _get_text(li.find("label")) or _get_text(elem.find("label")) or ""
            label_female = ET.SubElement(li, "labelFemale")
            label_female.text = label


def _enhance_quest_script_def(elem: ET.Element) -> None:
    """
    QuestScriptDef: обрабатывает slateRef ноды и заменяет $variable.

    Text-grabber заменяет $variable на реальные значения из QuestNode_Set.
    """
    # Собираем все QuestNode_Set значения
    variable_values = {}
    for node_set in elem.findall(".//QuestNode_Set"):
        name_elem = node_set.find("name")
        value_elem = node_set.find("value")
        if name_elem is not None and value_elem is not None:
            if name_elem.text and value_elem.text:
                variable_values[name_elem.text.strip()] = value_elem.text.strip()

    # Заменяем $variable в slateRef элементах
    for slate_ref in elem.findall(".//slateRef"):
        if slate_ref.text and "$" in slate_ref.text:
            text = slate_ref.text
            for var_name, var_value in variable_values.items():
                text = text.replace(f"${var_name}", var_value)
                text = text.replace(f"{{{var_name}}}", var_value)
            slate_ref.text = text

    # Также заменяем в обычных текстовых элементах
    _replace_variables_in_element(elem, variable_values)


def _get_text(elem: ET.Element | None) -> str | None:
    """Безопасно получает текст из элемента."""
    if elem is not None and elem.text:
        return elem.text.strip()
    return None


def _replace_variables_in_element(elem: ET.Element, variables: dict) -> None:
    """Рекурсивно заменяет $variable во всех текстовых элементах."""
    if not variables:
        return

    # Заменяем в тексте текущего элемента
    if elem.text and "$" in elem.text:
        for var_name, var_value in variables.items():
            elem.text = elem.text.replace(f"${var_name}", var_value)
            elem.text = elem.text.replace(f"{{{var_name}}}", var_value)

    # Рекурсивно обрабатываем детей
    for child in elem:
        if isinstance(child.tag, str):
            _replace_variables_in_element(child, variables)
