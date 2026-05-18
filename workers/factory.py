# workers/factory.py
"""
Фабрика для создания Worker-ов в зависимости от режима перевода.

Исправляет проблему: ранее объекты работали почти одинаково,
так как логика путей была смешана в одном классе.
Теперь используются разные классы с правильными стратегиями путей.
"""

from typing import Any

from .translation_worker import TranslationWorker
from .separate_worker import SeparateWorker


def create_translation_worker(
    mode: str,
    mods_folder: str,
    source_lang: str = "English",
    source_langs: list[str] | None = None,
    target_lang: str = "Russian",
    output_folder: str | None = None,
    logger: Any | None = None,
    create_backup: bool = True,
    selected_mods: list[str] | None = None,
    force_update: bool = False,
    fuzzy: bool = True,
    engine_names: list[str] | None = None,
    auto_detect_source_lang: bool = True,
    auto_split_glossary: bool = True,
) -> TranslationWorker:
    """
    Создает Worker для перевода в зависимости от режима.

    Args:
        mode: Режим перевода ('inplace', 'separate', 'merge')
        mods_folder: Папка с модами
        source_lang: Исходный язык
        source_langs: Список исходных языков (для многоязычного перевода)
        target_lang: Целевой язык
        output_folder: Папка вывода (для separate режима)
        logger: Логгер
        create_backup: Создавать ли резервные копии
        selected_mods: Список выбранных модов
        force_update: Принудительное обновление
        fuzzy: Использовать fuzzy поиск
        engine_names: Список движков перевода

    Returns:
        Экземпляр TranslationWorker (или подкласса)

    Raises:
        ValueError: Если указан неизвестный режим
    """
    if mode == "separate":
        from utils.debug_logger import log_info
        print(f"DEBUG FACTORY: Creating SeparateWorker with mode='{mode}'")
        log_info(f"DEBUG factory: Creating SeparateWorker with mode='{mode}'")
        return SeparateWorker(
            mods_folder=mods_folder,
            source_lang=source_lang,
            source_langs=source_langs,
            target_lang=target_lang,
            output_folder=output_folder,
            logger=logger,
            create_backup=False,
            selected_mods=selected_mods,
            force_update=force_update,
            fuzzy=fuzzy,
            engine_names=engine_names,
            auto_detect_source_lang=auto_detect_source_lang,
            auto_split_glossary=auto_split_glossary,
        )
    elif mode in ("inplace", "merge"):
        from utils.debug_logger import log_info
        print(f"DEBUG FACTORY: Creating TranslationWorker with mode='{mode}'")
        log_info(f"DEBUG factory: Creating TranslationWorker with mode='{mode}'")
        return TranslationWorker(
            mods_folder=mods_folder,
            source_lang=source_lang,
            source_langs_list=source_langs,
            target_lang=target_lang,
            output_folder=output_folder,
            logger=logger,
            mode=mode,
            create_backup=create_backup,
            selected_mods=selected_mods,
            force_update=force_update,
            fuzzy=fuzzy,
            engine_names=engine_names,
            auto_detect_source_lang=auto_detect_source_lang,
            auto_split_glossary=auto_split_glossary,
        )
    else:
        raise ValueError(
            f"Неизвестный режим: '{mode}'. "
            f"Поддерживаемые режимы: 'inplace', 'separate', 'merge'"
        )


def get_available_modes() -> list[str]:
    """
    Возвращает список поддерживаемых режимов.

    Returns:
        Список строк с именами режимов
    """
    return ["inplace", "separate", "merge"]


def get_worker_class(mode: str):
    """
    Возвращает класс Worker-а для указанного режима.

    Args:
        mode: Режим перевода

    Returns:
        Класс Worker-а

    Raises:
        ValueError: Если указан неизвестный режим
    """
    if mode == "separate":
        return SeparateWorker
    elif mode in ("inplace", "merge"):
        return TranslationWorker
    else:
        raise ValueError(f"Неизвестный режим: '{mode}'")