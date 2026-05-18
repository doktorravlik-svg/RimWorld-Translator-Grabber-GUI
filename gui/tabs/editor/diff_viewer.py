"""
Diff Viewer - просмотр различий между оригиналом и переводом.

Отвечает за:
- Побайтовое сравнение оригинала с переводом
- Цветовое выделение добавленных/удалённых символов
- Отображение в диалоговом окне
"""

import difflib
from typing import Optional

import tkinter as tk
from tkinter import ttk

from gui.gui_i18n import tr


class DiffViewer:
    """Просмотр различий между двумя текстами."""

    def __init__(self, parent):
        """
        Args:
            parent: Родительский виджет
        """
        self.parent = parent

    def show_diff(
        self,
        original: str,
        translation: str,
        title: str = "Сравнение с оригиналом"
    ) -> None:
        """
        Показывает диалог сравнения.

        Args:
            original: Оригинальный текст
            translation: Переведённый текст
            title: Заголовок окна
        """
        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.geometry("800x500")
        dialog.transient(self.parent)
        dialog.grab_set()

        # Заголовки
        header_frame = ttk.Frame(dialog)
        header_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(header_frame, text=tr("diff_original", "Оригинал (EN)"), font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=20
        )
        ttk.Label(header_frame, text=tr("diff_translation", "Перевод"), font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=20
        )

        # Создаём PanedWindow для двух панелей
        paned = ttk.PanedWindow(dialog, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=5)

        # Левая панель - оригинал
        orig_frame = ttk.Frame(paned)
        orig_text = self._create_diff_text(orig_frame, original, is_original=True)
        paned.add(orig_frame, weight=1)

        # Правая панель - перевод
        trans_frame = ttk.Frame(paned)
        trans_text = self._create_diff_text(trans_frame, translation, is_original=False)
        paned.add(trans_frame, weight=1)

        # Кнопка закрытия
        ttk.Button(
            dialog,
            text=tr("editor_close", "Закрыть"),
            command=dialog.destroy
        ).pack(pady=5)

    def _create_diff_text(
        self,
        parent,
        text: str,
        is_original: bool
    ) -> tk.Text:
        """
        Создаёт виджет текста с подсветкой различий.

        Args:
            parent: Родительский виджет
            text: Текст
            is_original: Это оригинал или перевод

        Returns:
            Созданный Text виджет
        """
        # Создаём Text с вертикальной прокруткой
        text_widget = tk.Text(
            parent,
            wrap="word",
            font=("Consolas", 10),
            state="normal"
        )
        scrollbar = ttk.Scrollbar(parent, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        text_widget.pack(side="left", fill="both", expand=True)

        # Вставляем текст
        text_widget.insert("1.0", text)

        # Настраиваем теги для подсветки
        text_widget.tag_configure("added", background="#d4edda", foreground="#155724")
        text_widget.tag_configure("removed", background="#f8d7da", foreground="#721c24")
        text_widget.tag_configure("changed", background="#fff3cd", foreground="#856404")

        return text_widget

    def generate_diff_html(
        self,
        original: str,
        translation: str
    ) -> str:
        """
        Генерирует HTML представление различий.

        Args:
            original: Оригинальный текст
            translation: Переведённый текст

        Returns:
            HTML строка с подсветкой различий
        """
        # Используем CharacterMatcher для побайтового сравнения
        matcher = difflib.SequenceMatcher(None, original, translation)

        html_parts = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                html_parts.append(self._escape(original[i1:i2]))
            elif tag == "replace":
                html_parts.append(
                    f'<span style="background:#f8d7da; color:#721c24; text-decoration:line-through">'
                    f'{self._escape(original[i1:i2])}</span>'
                )
                html_parts.append(
                    f'<span style="background:#d4edda; color:#155724">'
                    f'{self._escape(translation[j1:j2])}</span>'
                )
            elif tag == "delete":
                html_parts.append(
                    f'<span style="background:#f8d7da; color:#721c24; text-decoration:line-through">'
                    f'{self._escape(original[i1:i2])}</span>'
                )
            elif tag == "insert":
                html_parts.append(
                    f'<span style="background:#d4edda; color:#155724">'
                    f'{self._escape(translation[j1:j2])}</span>'
                )

        return "".join(html_parts)

    def generate_unified_diff(
        self,
        original: str,
        translation: str,
        from_name: str = "original",
        to_name: str = "translation",
        context_lines: int = 3
    ) -> str:
        """
        Генерирует unified diff.

        Args:
            original: Оригинальный текст
            translation: Переведённый текст
            from_name: Имя оригинала
            to_name: Имя перевода
            context_lines: Количество строк контекста

        Returns:
            Unified diff строка
        """
        orig_lines = original.splitlines(keepends=True)
        trans_lines = translation.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            trans_lines,
            fromfile=from_name,
            tofile=to_name,
            n=context_lines
        )

        return "".join(diff)

    @staticmethod
    def _escape(text: str) -> str:
        """Экранирует HTML символы."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )
