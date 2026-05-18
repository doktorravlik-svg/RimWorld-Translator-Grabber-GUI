"""
MessageBox Helpers - утилиты для стандартных диалоговых окон.

Устраняет дублирование вызовов messagebox по всему проекту (142+ мест).
Автоматически использует tr() для i18n заголовков.

Пример использования:
    from gui.dialogs.messagebox_helpers import show_ok, show_error, ask_confirm

    show_ok("Настройки сохранены")
    show_error("Не удалось сохранить файл")
    if ask_confirm("Вы уверены?"):
        ...
"""

from tkinter import messagebox

try:
    from gui.gui_i18n import tr
except ImportError:
    # Fallback если i18n недоступен
    def tr(key: str, default: str = "") -> str:
        return default


def show_ok(message: str, title: str = None) -> None:
    """
    Показывает информационное сообщение.

    Args:
        message: Текст сообщения
        title: Заголовок окна (по умолчанию "OK")
    """
    messagebox.showinfo(
        title or tr("msg_ok", "OK"),
        message
    )


def show_error(message: str, title: str = None) -> None:
    """
    Показывает сообщение об ошибке.

    Args:
        message: Текст ошибки
        title: Заголовок окна (по умолчанию "Ошибка")
    """
    messagebox.showerror(
        title or tr("msg_error", "Ошибка"),
        message
    )


def show_warning(message: str, title: str = None) -> None:
    """
    Показывает предупреждение.

    Args:
        message: Текст предупреждения
        title: Заголовок окна (по умолчанию "Предупреждение")
    """
    messagebox.showwarning(
        title or tr("msg_warning", "Предупреждение"),
        message
    )


def show_info(message: str, title: str = None) -> None:
    """
    Показывает информационное сообщение (альтернатива show_ok).

    Args:
        message: Текст сообщения
        title: Заголовок окна (по умолчанию "Информация")
    """
    messagebox.showinfo(
        title or tr("msg_info", "Информация"),
        message
    )


def ask_confirm(
    message: str,
    title: str = None,
    default: bool = False
) -> bool:
    """
    Показывает диалог подтверждения.

    Args:
        message: Текст вопроса
        title: Заголовок окна (по умолчанию "Подтверждение")
        default: Ответ по умолчанию (False = Нет, True = Да)

    Returns:
        True если пользователь нажал "Да"
    """
    return messagebox.askyesno(
        title or tr("editor_confirm_title", "Подтверждение"),
        message,
        default=default
    )


def ask_yes_no(message: str, title: str = None) -> bool:
    """
    Показывает диалог Да/Нет (альтернатива ask_confirm).

    Args:
        message: Текст вопроса
        title: Заголовок окна

    Returns:
        True если выбрано "Да"
    """
    return ask_confirm(message, title)


def ask_retry(message: str, title: str = None) -> bool:
    """
    Показывает диалог с вариантами Повторить/Отмена.

    Args:
        message: Текст вопроса
        title: Заголовок окна

    Returns:
        True если выбрано "Повторить"
    """
    return messagebox.askretrycancel(
        title or tr("msg_retry", "Повторить"),
        message
    )
