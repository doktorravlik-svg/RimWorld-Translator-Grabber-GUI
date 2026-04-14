# gui/tabs/editor/editor_toolbar.py
"""
Панель инструментов редактора с автоматическим переносом при сужении окна.

Вынесено из gui_translation_editor.py для разделения ответственности.
"""

import ttkbootstrap as ttk


class WrappingToolbar(ttk.Frame):
    """Панель инструментов с автоматическим переносом при сужении окна"""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._groups = []
        self._built = False

    def add_group(self, label, widgets_callback):
        """
        Добавить группу виджетов на панель.

        Args:
            label: Текст заголовка группы
            widgets_callback: Функция, принимающая LabelFrame для размещения виджетов
        """
        lf = ttk.LabelFrame(self, text=label)
        widgets_callback(lf)
        self._groups.append((label, lf))
        return lf

    def build(self):
        """Построить панель (вызывать после размещения всех групп)"""
        if self._built:
            return
        self._built = True
        self.bind("<Configure>", self._on_resize)
        self._on_resize()

    def _on_resize(self, event=None):
        """Автоматический перенос групп при изменении ширины"""
        if not self._built:
            return
        width = self.winfo_width()
        if width < 10:
            return

        for _, lf in self._groups:
            lf.pack_forget()

        used_width = 0
        current_row = ttk.Frame(self)
        current_row.pack(fill="x", pady=1)

        for label, lf in self._groups:
            lf.update_idletasks()
            group_w = lf.winfo_reqwidth()
            if group_w < 10:
                group_w = 130

            if used_width + group_w > width - 10 and used_width > 0:
                current_row = ttk.Frame(self)
                current_row.pack(fill="x", pady=1)
                used_width = 0

            lf.pack(in_=current_row, side="left", padx=2)
            used_width += group_w + 4
