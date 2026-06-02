# gui/styling/font_manager.py
"""
Управление шрифтами для RimWorld Translator Grabber.
"""

from gui.utils import safe_configure


def get_font_tuple(config: dict, key: str, default_family: str, default_size: int) -> tuple:
    """
    Получить шрифт из конфига в формате (family, size).

    Args:
        config: Словарь конфигурации
        key: Ключ шрифта в конфиге
        default_family: Семейство шрифта по умолчанию
        default_size: Размер шрифта по умолчанию

    Returns:
        Кортеж (family, size)
    """
    font_cfg = config.get(key, {})
    family = font_cfg.get("family", default_family)
    size = font_cfg.get("size", default_size)
    return (family, size)


def apply_fonts(config: dict, style, widgets: dict, log_callback=None):
    """
    Применить шрифты из конфига ко всем виджетам.

    Args:
        config: Словарь конфигурации
        style: ttkbootstrap Style
        widgets: Словарь виджетов для применения шрифтов
            Ожидает ключи: log_text, status_label (опционально)
        log_callback: Функция для логирования
    """
    main_font = get_font_tuple(config, "main_font", "Segoe UI", 9)
    log_font = get_font_tuple(config, "log_font", "Consolas", 10)
    tree_font = get_font_tuple(config, "tree_font", "Segoe UI", 9)

    # Применяем основной шрифт через стили
    safe_configure(style, "TLabel", font=main_font)
    safe_configure(style, "TButton", font=main_font)
    safe_configure(style, "TEntry", font=main_font)
    safe_configure(style, "TCombobox", font=main_font)
    safe_configure(style, "TCheckbutton", font=main_font)
    safe_configure(style, "TRadiobutton", font=main_font)
    safe_configure(style, "TNotebook.Tab", font=main_font)
    safe_configure(style, "TLabelframe", font=main_font)
    safe_configure(style, "TLabelframe.Label", font=(*main_font, "bold"))

    # Применяем шрифт дерева
    safe_configure(style, "Treeview", font=tree_font)
    safe_configure(style, "Treeview.Heading", font=(*tree_font, "bold"))

    # Применяем шрифт логов
    if "log_text" in widgets:
        widgets["log_text"].config(font=log_font)

    # Обновляем статус-бар
    if "status_label" in widgets:
        widgets["status_label"].config(font=main_font)

    if log_callback:
        log_callback(f"Шрифты: основной={main_font}, логи={log_font}, дерево={tree_font}")
