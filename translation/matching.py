# matching.py
"""
Модуль для поиска и сопоставления существующих переводов.

Предоставляет функции для поиска лучших совпадений переводов
на основе точного, нечётного и контекстного matching.
"""

import os
from collections import defaultdict
from typing import Any


def find_existing_translation(
    tagname: str,
    existing_map: dict[str, str],
    existing_index: dict[str, str],
    logger: Any | None = None,
    mode: str = "strict",
    fuzzy: bool = False,
) -> tuple[str | None, str | None]:
    """
    Ищет существующий перевод для указанного тега.

    Алгоритм поиска:
    1. Точное совпадение
    2. Case-insensitive совпадение
    3. Варианты с заменой '.' на '_' и наоборот
    4. Поиск по базовой части (до первой '.')
    5. Loose режим: поиск по последнему токену
    6. Fuzzy режим: поиск по частичному совпадению ключа

    Args:
        tagname: Имя тега для поиска
        existing_map: Карта существующих переводов {key: value}
        existing_index: Индекс файлов {key: filepath}
        logger: Логгер для записи сообщений
        mode: Режим поиска ('strict' или 'loose')
        fuzzy: Включить нечёткий поиск (для новых/переименованных тегов)

    Returns:
        Кортеж (перевод, путь_к_файлу) или (None, None) если не найдено
    """
    if not tagname:
        return None, None
    t = (tagname or "").strip()
    if not t:
        return None, None
    if t in existing_map and existing_map[t].strip():
        if logger:
            logger.debug(f"find_existing_translation({mode}): exact {t}")
        return existing_map[t], existing_index.get(t)
    low = t.lower()
    for k, v in existing_map.items():
        if k and k.lower() == low and v and v.strip():
            if logger:
                logger.debug(f"find_existing_translation({mode}): case-insensitive {k} for {t}")
            return v, existing_index.get(k)
    alts = {t.replace(".", "_"), t.replace("_", ".")}
    for alt in alts:
        if alt in existing_map and existing_map[alt].strip():
            if logger:
                logger.debug(f"find_existing_translation({mode}): variant {alt} for {t}")
            return existing_map[alt], existing_index.get(alt)
        for k, v in existing_map.items():
            if k and k.lower() == alt.lower() and v and v.strip():
                if logger:
                    logger.debug(
                        f"find_existing_translation({mode}): variant case-insensitive {k} for {t}"
                    )
                return v, existing_index.get(k)
    parts = t.split(".")
    if len(parts) > 1:
        base = parts[0]
        if base in existing_map and existing_map[base].strip():
            if logger:
                logger.debug(f"find_existing_translation({mode}): base {base} for {t}")
            return existing_map[base], existing_index.get(base)
        for suf in (
            "label",
            "description",
            "desc",
            "labelNoun",
            "labelnoun",
            "labelnounpretty",
            "jobString",
        ):
            cand = f"{base}.{suf}"
            if cand in existing_map and existing_map[cand].strip():
                if logger:
                    logger.debug(f"find_existing_translation({mode}): base.suffix {cand} for {t}")
                return existing_map[cand], existing_index.get(cand)
            for k, v in existing_map.items():
                if k and k.lower() == cand.lower() and v and v.strip():
                    if logger:
                        logger.debug(
                            f"find_existing_translation({mode}): base.suffix case-insensitive {k} for {t}"
                        )
                    return v, existing_index.get(k)
    if mode == "loose":
        last = t.split(".")[-1].split("_")[-1].lower()
        for k, v in existing_map.items():
            if not k or not v or not v.strip():
                continue
            kk = k.split(".")[-1].split("_")[-1].lower()
            if kk == last:
                if logger:
                    logger.debug(f"find_existing_translation(loose): last-token {last} -> {k}")
                return v, existing_index.get(k)

    # Fuzzy режим: поиск по частичному совпадению ключа (как RimTrans)
    if fuzzy:
        # Извлекаем ключевые части тега
        t_parts = set(t.lower().replace(".", " ").replace("_", " ").split())

        best_match = None
        best_score = 0

        for k, v in existing_map.items():
            if not k or not v or not v.strip():
                continue

            k_parts = set(k.lower().replace(".", " ").replace("_", " ").split())

            # Считаем совпадающие части
            common = t_parts & k_parts
            score = len(common) / max(len(t_parts), len(k_parts))

            # Нужно минимум 40% совпадения (для fuzzy как RimTrans)
            if score > 0.4 and score > best_score:
                best_score = score
                best_match = (v, existing_index.get(k))

        if best_match:
            if logger:
                logger.debug(
                    f"find_existing_translation(fuzzy): {best_score:.0%} match {best_match[1]} for {t}"
                )
            return best_match

    if logger:
        logger.debug(f"find_existing_translation({mode}): no match for {t}")
    return None, None


def find_best_existing_file_for_def(
    defname: str,
    tags: list,
    existing_index: Dict[str, str],
    existing_map: Dict[str, str],
    defs_source_rel: Dict[str, str],
    logger: Optional[Any] = None,
) -> Optional[str]:
    """
    Находит лучший существующий файл для defname на основе тегов.

    Приоритет выбора:
    1. Файл с именем содержащим defname
    2. Файл из той же rel папки
    3. Файл с наибольшим количеством совпадений тегов

    Args:
        defname: Имя дефиниции
        tags: Список тегов для поиска
        existing_index: Индекс файлов {key: filepath}
        existing_map: Карта существующих переводов
        defs_source_rel: Карта {defname: rel_folder} из источника
        logger: Логгер для записи сообщений

    Returns:
        Путь к лучшему файлу или None
    """
    if logger:
        logger.debug(f"Selecting existing file for {defname} (tags count {len(tags)})")
    path_to_tags = defaultdict(set)
    for tag in tags:
        p = existing_index.get(tag)
        if p:
            txt = existing_map.get(tag, "")
            if txt and txt.strip():
                path_to_tags[p].add(tag)
    if not path_to_tags:
        for tag in tags:
            alts = {tag, tag.replace(".", "_"), tag.replace("_", ".")}
            for alt in alts:
                p = existing_index.get(alt)
                if p:
                    txt = existing_map.get(alt, "")
                    if txt and txt.strip():
                        path_to_tags[p].add(tag)
    if not path_to_tags:
        if logger:
            logger.debug("No existing files contain non-empty translations for these tags")
        return None
    def_low = defname.lower()
    for p in list(path_to_tags.keys()):
        try:
            if def_low in os.path.basename(p).lower():
                if logger:
                    logger.debug(f"Chose by filename contains defname: {p}")
                if os.path.isdir(p):
                    candidate_file = os.path.join(p, f"{defname}.xml")
                    if os.path.exists(candidate_file):
                        return candidate_file
                    continue
                return p
        except Exception:
            continue
    rel = defs_source_rel.get(defname)
    if rel:
        for p in list(path_to_tags.keys()):
            try:
                if rel.lower() in p.lower():
                    if logger:
                        logger.debug(f"Chose by same rel folder {rel}: {p}")
                    if os.path.isdir(p):
                        candidate_file = os.path.join(p, f"{defname}.xml")
                        if os.path.exists(candidate_file):
                            return candidate_file
                        continue
                    return p
            except Exception:
                continue
    best = None
    best_count = 0
    for p, s in path_to_tags.items():
        if len(s) > best_count:
            best_count = len(s)
            best = p
    if best:
        if logger:
            logger.debug(f"Chose by most matches: {best} ({best_count})")
        if os.path.isdir(best):
            candidate_file = os.path.join(best, f"{defname}.xml")
            if os.path.exists(candidate_file):
                return candidate_file
            return None
        return best
    return None
