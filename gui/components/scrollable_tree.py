# gui/components/scrollable_tree.py
"""
Переиспользуемый компонент: Treeview с горизонтальным и вертикальным скроллбаром.

Устраняет дублирование паттерна Treeview + 2 Scrollbar,
который повторяется 8+ раз по всему проекту.

Пример использования:
    st = ScrollableTree(
        parent_frame,
        columns=("key", "value", "status"),
        headings={"key": "🔑 Ключ", "value": "📝 Значение", "status": "📊 Статус"},
        column_widths={"key": 250, "value": 400, "status": 100},
        height=15,
        selectmode="extended"
    )
    st.pack(fill="both", expand=True)

    # Доступ к tree и скроллбарам
    st.tree.insert("", "end", values=("key1", "value1", "complete"))
    st.tree.tag_configure("complete", background="#22c55e")
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class ScrollableTree(ttk.Frame):
    """
    Frame содержащий Treeview + вертикальный + горизонтальный скроллбар.

    Args:
        master: Родительский виджет
        columns: Список имён колонок
        headings: Словарь {column: heading_text}
        column_widths: Словарь {column: width}
        column_mins: Словарь {column: minwidth} (опционально)
        show: Что показывать ("headings", "tree", etc.)
        selectmode: Режим выделения ("extended", "browse", "none")
        height: Высота дерева (количество строк)
        **tree_kwargs: Дополнительные аргументы для ttk.Treeview
    """

    def __init__(
        self,
        master,
        columns: tuple[str, ...] | list[str],
        headings: dict[str, str] | None = None,
        column_widths: dict[str, int] | None = None,
        column_mins: dict[str, int] | None = None,
        show: str = "headings",
        selectmode: str = "browse",
        height: int = 10,
        **tree_kwargs,
    ):
        super().__init__(master)

        # Создаём Treeview
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show=show,
            selectmode=selectmode,
            height=height,
            **tree_kwargs,
        )

        # Настраиваем колонки
        headings = headings or {}
        column_widths = column_widths or {}
        column_mins = column_mins or {}

        for col in columns:
            heading_text = headings.get(col, col)
            width = column_widths.get(col, 100)
            minwidth = column_mins.get(col, 50)

            self.tree.heading(col, text=heading_text)
            self.tree.column(col, width=width, minwidth=minwidth)

        # Создаём скроллбары
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)

        # Связываем Treeview со скроллбарами
        self.tree.configure(
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
        )

        # Упаковываем виджеты через grid для корректного пересечения скроллбаров
        # grid предотвращает перекрытие vsb/hsb в правом нижнем углу
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # Настраиваем растягивание
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def bind(self, sequence: str, func, add: bool = None):
        """Прокси для привязки событий к tree"""
        return self.tree.bind(sequence, func, add)

    def delete(self, *items):
        """Прокси для удаления элементов"""
        return self.tree.delete(*items)

    def insert(self, parent, index, iid=None, **kwargs):
        """Прокси для вставки элементов"""
        return self.tree.insert(parent, index, iid, **kwargs)

    def item(self, item, option=None, **kw):
        """Прокси для работы с элементами"""
        return self.tree.item(item, option, **kw)

    def selection(self, selop=None, *items):
        """Прокси для выделения"""
        return self.tree.selection(selop, *items)

    def selection_set(self, *items):
        """Прокси для установки выделения"""
        return self.tree.selection_set(*items)

    def selection_get(self):
        """Прокси для получения выделения"""
        return self.tree.selection_get()

    def get_children(self, item=None):
        """Прокси для получения дочерних элементов"""
        return self.tree.get_children(item)

    def tag_configure(self, tagname, option=None, **kwargs):
        """Прокси для настройки тегов"""
        return self.tree.tag_configure(tagname, option, **kwargs)

    def focus(self, item=None):
        """Прокси для фокуса"""
        return self.tree.focus(item)

    def set(self, item, column=None, value=None):
        """Прокси для получения/установки значения ячейки"""
        return self.tree.set(item, column, value)

    def see(self, item):
        """Прокси для прокрутки к элементу"""
        return self.tree.see(item)

    def heading(self, column, option=None, **kwargs):
        """Прокси для настройки заголовков"""
        return self.tree.heading(column, option, **kwargs)

    def column(self, column, option=None, **kwargs):
        """Прокси для настройки колонок"""
        return self.tree.column(column, option, **kwargs)

    def identify_row(self, y: int):
        """Определяет строку по координате Y"""
        return self.tree.identify_row(y)

    def identify_column(self, x: int):
        """Определяет колонку по координате X"""
        return self.tree.identify_column(x)

    def bbox(self, item, column=None):
        """Возвращает bounding box элемента"""
        return self.tree.bbox(item, column)
