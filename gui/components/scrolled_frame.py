# gui/components/scrolled_frame.py
"""
Переиспользуемый компонент: Прокручиваемый фрейм с Canvas.

Устраняет дублирование паттерна Canvas + Scrollbar + Frame,
который повторяется 5+ раз по всему проекту.

Пример использования:
    sf = ScrolledFrame(parent, width=400, height=300)
    sf.pack(fill="both", expand=True)

    # Добавление виджетов в content_frame
    ttk.Label(sf.content_frame, text="Привет").pack()
    ttk.Button(sf.content_frame, text="Кнопка").pack()
"""

import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class ScrolledFrame(ttk.Frame):
    """
    Frame с вертикальной прокруткой на основе Canvas.

    Args:
        master: Родительский виджет
        width: Ширина (опционально)
        height: Высота (опционально)
        autohidescroll: Автоматически скрывать скроллбар (True/False)
        **kwargs: Дополнительные аргументы для ttk.Frame
    """

    def __init__(
        self,
        master,
        width: int | None = None,
        height: int | None = None,
        autohidescroll: bool = False,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        # Создаём Canvas
        self.canvas = tk.Canvas(self, highlightthickness=0)

        if width:
            self.canvas.config(width=width)
        if height:
            self.canvas.config(height=height)

        # Создаём скроллбар
        if autohidescroll:
            # Используем встроенный авто-скролл если доступен
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        else:
            self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        # Создаём контент-фрейм
        self.content_frame = ttk.Frame(self.canvas)

        # Настраиваем Canvas
        self.content_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.content_frame, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Упаковываем виджеты
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Привязка колёсика мыши — локальная, без bind_all
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.content_frame.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """Обработка колёсика мыши"""
        # Windows/Mac: event.delta, Linux: event.num
        if event.delta != 0:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

    def update_scrollregion(self):
        """Обновить область прокрутки (вызывать после изменений контента)"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
