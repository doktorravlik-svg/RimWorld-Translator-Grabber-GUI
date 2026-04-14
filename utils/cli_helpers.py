# cli_helpers.py
"""
Module containing command-line interface helper functions for language processing tools.
Provides utilities for displaying language tables, prompting users, and creating backups.
"""

import os


def display_language_table(languages, source_lang_info=None):
    """
    Display a formatted table showing language statistics.

    Args:
        languages (dict): Dictionary containing language information
        source_lang_info (dict, optional): Source language information for comparison
    """
    print("\n" + "=" * 70)
    print(f"{'Язык':<20} {'Keyed':<10} {'DefInjected':<12} {'Всего ключей':<15} {'Статус':<10}")
    print("=" * 70)

    for lang_name, info in sorted(languages.items()):
        status = "✓ Готов" if info["total_keys"] > 0 else "✗ Пусто"
        if source_lang_info and source_lang_info.get(lang_name):
            src_total_keys = source_lang_info[lang_name]["total_keys"]
            if src_total_keys > 0:
                status = f"{(info['total_keys'] / src_total_keys * 100):.1f}%"
        print(
            f"{lang_name:<20} {info['keyed_files']:<10} {info['def_files']:<12} {info['total_keys']:<15} {status:<10}"
        )
    print("=" * 70)


def prompt_yes_no(prompt, default="y", interactive=True):
    """
    Prompt the user for a yes/no response.

    Args:
        prompt (str): Question to ask the user
        default (str): Default response ('y' or 'n')
        interactive (bool): Whether to actually prompt the user

    Returns:
        bool: True if user answered yes, False otherwise
    """
    default = default.lower()
    choices = "Y/n" if default == "y" else "y/N"
    if not interactive:
        return default in ("y", "yes")

    try:
        answer = input(f"{prompt} ({choices}): ").strip().lower()
        if answer == "":
            answer = default
    except KeyboardInterrupt:
        answer = default
    except Exception:
        answer = default

    return answer in ("y", "yes")


def create_backup(directory, logger):
    """
    Создать резервную копию директории через централизованный менеджер.

    Args:
        directory (str): Path to directory to backup
        logger: Logger object for recording events

    Returns:
        str: Path to backup directory, or None if backup failed
    """
    from utils.backup_manager import get_backup_manager

    if not os.path.exists(directory):
        logger.warning(f"Директория для резервной копии не найдена: {directory}")
        return None

    backup_manager = get_backup_manager()
    return backup_manager.create_backup(directory, logger=logger)
