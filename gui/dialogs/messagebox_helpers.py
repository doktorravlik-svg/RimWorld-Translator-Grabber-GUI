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

import tkinter as tk
from tkinter import messagebox

try:
    from gui.gui_i18n import tr
except ImportError:
    # Fallback если i18n недоступен
    def tr(key: str, default: str = "") -> str:
        return default


def _show_messagebox_safe(parent, title, message, messagebox_func=messagebox.showinfo):
    """Показывает messagebox в главном потоке (thread-safe)."""
    if parent and isinstance(parent, tk.Tk | tk.Toplevel):
        parent.after(0, lambda: messagebox_func(title, message))
    else:
        messagebox_func(title, message)


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
    default_value = "yes" if default else "no"
    return messagebox.askyesno(
        title or tr("editor_confirm_title", "Подтверждение"),
        message,
        default=default_value
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


# =============================================================================
# Thread-safe версии функций (для вызова из фоновых потоков)
# =============================================================================

def show_ok_safe(parent, message: str, title: str = None) -> None:
    """Показывает информационное сообщение в главном потоке."""
    _show_messagebox_safe(parent, title or tr("msg_ok", "OK"), message, messagebox.showinfo)


def show_error_safe(parent, message: str, title: str = None) -> None:
    """Показывает сообщение об ошибке в главном потоке."""
    _show_messagebox_safe(parent, title or tr("msg_error", "Ошибка"), message, messagebox.showerror)


def show_warning_safe(parent, message: str, title: str = None) -> None:
    """Показывает предупреждение в главном потоке."""
    _show_messagebox_safe(parent, title or tr("msg_warning", "Предупреждение"), message, messagebox.showwarning)


def show_info_safe(parent, message: str, title: str = None) -> None:
    """Показывает информационное сообщение в главном потоке."""
    _show_messagebox_safe(parent, title or tr("msg_info", "Информация"), message, messagebox.showinfo)


def ask_confirm_safe(parent, message: str, title: str = None, default: bool = False) -> bool:
    """
    Показывает диалог подтверждения в главном потоке.
    ВНИМАНИЕ: Возвращает False, если диалог ещё не был закрыт (асинхронный вызов).
    Для использования из фоновых потоков сопоставьтесь с результатом через callback.
    """
    result = [False]
    default_value = "yes" if default else "no"

    def _show():
        result[0] = messagebox.askyesno(
            title or tr("editor_confirm_title", "Подтверждение"),
            message,
            default=default_value
        )

    _show_messagebox_safe(parent, title or tr("editor_confirm_title", "Подтверждение"), message,
                          lambda t, m: result.__setitem__(0, messagebox.askyesno(t, m, default=default_value)))
    return result[0]
