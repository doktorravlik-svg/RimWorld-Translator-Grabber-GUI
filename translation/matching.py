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
    original_text: str | None = None,
    use_anchors: bool = True,
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

    # Fuzzy режим: поиск по частичному совпадению ключа (как RimTrans) - УЛУЧШЕННЫЙ
    if fuzzy:
        # Используем rapidfuzz для точного нечёткого сравнения
        try:
            from rapidfuzz import fuzz
        except ImportError:
            fuzz = None

        if fuzz:
            best_match = None
            best_score = 0
            best_defname_similarity = 0

            t_lower = t.lower()
            # Разделяем t на части один раз
            t_parts = t_lower.split('.', 1)
            if len(t_parts) < 2:
                # Нет поля после точки - пропускаем fuzzy
                pass
            else:
                t_def_part = t_parts[0]
                t_def_parts = t_def_part.split('_', 1)
                if len(t_def_parts) >= 2:
                    t_def_type, t_def_name = t_def_parts
                    t_field = t_parts[1] if len(t_parts) > 1 else ""

                    for k, v in existing_map.items():
                        if not k or not v or not v.strip():
                            continue

                        k_lower = k.lower()
                        k_parts = k_lower.split('.', 1)
                        if len(k_parts) < 2:
                            continue

                        k_def_part = k_parts[0]
                        k_def_parts = k_def_part.split('_', 1)
                        if len(k_def_parts) < 2:
                            continue

                        k_def_type, k_def_name = k_def_parts
                        k_field = k_parts[1] if len(k_parts) > 1 else ""

                        # 1. DefType должен совпадать
                        if t_def_type != k_def_type and not (
                            (t_def_type.endswith('def') and k_def_type.endswith('def')) or
                            (t_def_type.rstrip('s') == k_def_type.rstrip('s'))
                        ):
                            continue

                        # 2. DefName должен быть очень похож (>= 80%)
                        defname_sim = fuzz.ratio(t_def_name, k_def_name)
                        if defname_sim < 80:
                            continue

                        # 3. Поле должно быть очень похожим
                        field_sim = fuzz.ratio(t_field, k_field) if t_field and k_field else 100
                        if field_sim < 90:
                            continue

                        # Общая оценка
                        overall_score = (defname_sim * 0.7) + (field_sim * 0.3)

                        if overall_score > best_score:
                            best_score = overall_score
                            best_defname_similarity = defname_sim
                            best_match = (v, existing_index.get(k), k)

            if best_match:
                v, path, matched_key = best_match
                # Логируем подозрительные совпадения для ручной проверки
                if 80 <= best_defname_similarity < 92:
                    try:
                        with open("fuzzy_review_needed.log", "a", encoding="utf-8") as f:
                            f.write(f"[DefName:{best_defname_similarity:.0f}%] {t}\n")
                            f.write(f"      Matched: {matched_key}\n")
                            f.write(f"      File: {path}\n")
                            f.write(f"      Value: {v[:80]}\n")
                            f.write("-" * 60 + "\n")
                    except Exception:
                        pass

                if logger:
                    logger.info(
                        f"✅ Fuzzy: {t} → {matched_key} (DefName: {best_defname_similarity:.0f}%, overall: {best_score:.0f}%)"
                    )
                return v, path

        else:
            # Fallback без rapidfuzz - используем difflib
            import difflib

            best_match = None
            best_ratio = 0
            best_key = None

            for k, v in existing_map.items():
                if not k or not v or not v.strip():
                    continue

                ratio = difflib.SequenceMatcher(None, t.lower(), k.lower()).ratio()
                if ratio > 0.85 and ratio > best_ratio:  # Очень высокий порог
                    best_ratio = ratio
                    best_match = (v, existing_index.get(k))
                    best_key = k

            if best_match:
                if logger:
                    logger.info(f"✅ Fuzzy (fallback): {t} → {best_key} ({best_ratio:.0%})")
                return best_match

    # ✅ EN ЯКОРЯ - ПОИСК ПО ОРИГИНАЛЬНОМУ ТЕКСТУ С УЧЁТОМ КОНТЕКСТА (DefType)
    # Самый надёжный способ: учитывает и смысл, и тип Def'а
    if use_anchors and original_text is not None:
        try:
            from translation.anchor_manager import AnchorManager
            anchor_mgr = AnchorManager.get_instance()
            # Извлекаем DefType из tagname как контекст
            context = ""
            if '_' in tagname:
                context = tagname.split('_', 1)[0]
            anchor_translation = anchor_mgr.find(original_text.strip(), context=context)
            if anchor_translation:
                if logger:
                    logger.info(
                        f"✅ EN якорь найден (ctx={context}): "
                        f"'{original_text[:60]}' -> '{anchor_translation[:60]}'"
                    )
                return anchor_translation, "anchor_db"
        except Exception as e:
            if logger:
                logger.debug(f"AnchorManager error: {e}")

    if logger:
        logger.debug(f"find_existing_translation({mode}): no match for {t}")
    return None, None


def find_best_existing_file_for_def(
    defname: str,
    tags: list,
    existing_index: dict[str, str],
    existing_map: dict[str, str],
    defs_source_rel: dict[str, str],
    logger: Any | None = None,
) -> str | None:
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


__all__ = [
    "find_existing_translation",
]
