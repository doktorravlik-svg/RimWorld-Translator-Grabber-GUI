# gui/styling/color_manager.py
"""
Управление цветами для RimWorld Translator Grabber.
"""

from gui.utils import safe_configure


def apply_colors(config: dict, style, widgets: dict, log_callback=None):
    """
    Применить пользовательские цвета из конфига ко всем виджетам.

    Args:
        config: Словарь конфигурации
        style: ttkbootstrap Style
        widgets: Словарь виджетов для применения цветов
            Ожидает ключи: log_text (опционально)
        log_callback: Функция для логирования
    """
    text_color = config.get("text_color")
    bg_color = config.get("bg_color")
    accent_color = config.get("accent_color")

    if text_color:
        safe_configure(style, "TLabel", foreground=text_color)
        safe_configure(style, "TLabelframe", foreground=text_color)
        safe_configure(style, "TLabelframe.Label", foreground=text_color)
        safe_configure(style, "TCheckbutton", foreground=text_color)
        safe_configure(style, "TRadiobutton", foreground=text_color)

    if bg_color:
        safe_configure(style, "TFrame", background=bg_color)
        safe_configure(style, "TLabel", background=bg_color)
        safe_configure(style, "TLabelframe", background=bg_color)
        safe_configure(style, "TCheckbutton", background=bg_color)
        safe_configure(style, "TRadiobutton", background=bg_color)

    if accent_color:
        safe_configure(style, "TButton", background=accent_color)
        safe_configure(style, "Accent.TButton", background=accent_color)
        safe_configure(style, "TNotebook.Tab", background=accent_color)
        style.map("TNotebook.Tab", background=[("selected", accent_color)])

    if text_color and bg_color:
        safe_configure(style, "TEntry", fieldbackground=bg_color, foreground=text_color)
        safe_configure(style, "TCombobox", fieldbackground=bg_color, foreground=text_color)

    # Цвета логов
    log_bg_color = config.get("log_bg_color")
    log_text_color = config.get("log_text_color")

    if "log_text" in widgets:
        if log_bg_color:
            widgets["log_text"].config(bg=log_bg_color)
        if log_text_color:
            widgets["log_text"].config(fg=log_text_color)

        # Цвета тегов логов
        tag_colors = {
            "info": config.get("log_info_color", "#4fc3f7"),
            "warning": config.get("log_warning_color", "#ffb74d"),
            "error": config.get("log_error_color", "#ef5350"),
            "success": config.get("log_success_color", "#66bb6a"),
        }
        for tag_name, color in tag_colors.items():
            widgets["log_text"].tag_config(tag_name, foreground=color)

    if log_callback:
        log_callback(
            f"Цвета: текст={text_color or 'по умол.'}, фон={bg_color or 'по умол.'}, "
            f"акцент={accent_color or 'по умол.'}, логи: фон={log_bg_color or 'по умол.'}, "
            f"текст={log_text_color or 'по умол.'}"
        )
