# gui/components/report_exporter.py
"""
Переиспользуемый компонент: Экспорт отчётов в TXT, JSON и HTML.

Устраняет дублирование логики экспорта, которая повторяется в:
- gui_tab_verification.py
- gui_dependencies.py

Пример использования:
    exporter = ReportExporter(
        data=self.results,
        title="Отчёт верификации",
        columns=("Тип", "Мод", "Сообщение"),
        date=datetime.now()
    )

    exporter.export_txt("report.txt")
    exporter.export_json("report.json")
    exporter.export_html("report.html")
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Sequence


class ReportExporter:
    """
    Экспорт данных отчёта в различные форматы (TXT, JSON, HTML).

    Args:
        data: Список словарей с данными отчёта
        title: Заголовок отчёта
        columns: Названия колонок
        date: Дата создания отчёта (по умолчанию текущая)
        keys: Ключи словарей data, соответствующие колонкам (опционально;
            если не заданы — выводятся из имени колонки)
    """

    def __init__(
        self,
        data: Sequence[dict[str, Any]],
        title: str,
        columns: Sequence[str],
        date: datetime | None = None,
        keys: Sequence[str] | None = None,
    ):
        self.data = data
        self.title = title
        self.columns = columns
        self.date = date or datetime.now()
        self.keys = keys

    def _cell_value(self, row: dict[str, Any], index: int) -> Any:
        """Значение ячейки: по явному ключу или по нормализованному имени колонки."""
        if self.keys is not None and index < len(self.keys):
            return row.get(self.keys[index], "")
        # Fallback: normalize column name to match data keys
        col_name = self.columns[index]
        normalized = col_name.lower().replace(" ", "_")
        return row.get(normalized, "")

    def export_txt(self, file_path: str) -> bool:
        """
        Экспорт в TXT.

        Args:
            file_path: Путь к файлу

        Returns:
            True если экспорт успешен, False в случае ошибки
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"{self.title}\n")
                f.write(f"Дата: {self.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                for row in self.data:
                    values = [str(self._cell_value(row, i)) for i in range(len(self.columns))]
                    f.write(" | ".join(values) + "\n")
            return True
        except (OSError, PermissionError) as e:
            print(f"Ошибка экспорта в TXT: {e}")
            return False

    def export_json(self, file_path: str) -> bool:
        """
        Экспорт в JSON.

        Args:
            file_path: Путь к файлу

        Returns:
            True если экспорт успешен, False в случае ошибки
        """
        try:
            data = {
                "title": self.title,
                "timestamp": self.date.isoformat(),
                "columns": self.columns,
                "rows": self.data,
                "statistics": {
                    "total": len(self.data),
                },
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, PermissionError) as e:
            print(f"Ошибка экспорта в JSON: {e}")
            return False

    def export_html(self, file_path: str, style_classes: dict[str, str] | None = None) -> bool:
        """
        Экспорт в HTML.

        Args:
            file_path: Путь к файлу
            style_classes: Словарь {class_name: css_style} для стилизации строк

        Returns:
            True если экспорт успешен, False в случае ошибки
        """
        try:
            style_classes = style_classes or {
                "error": "background-color: #ffcccc;",
                "warning": "background-color: #fff3cd;",
                "success": "background-color: #d4edda;",
                "info": "background-color: #d1ecf1;",
            }
            
            html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .header {{ background: #f5f5f5; padding: 15px; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .error {{ background-color: #ffcccc; }}
        .warning {{ background-color: #fff3cd; }}
        .success {{ background-color: #d4edda; }}
        .info {{ background-color: #d1ecf1; }}
    </style>
</head>
<body>
    <h1>{self.title}</h1>
    <div class="header">
        <p>Дата: {self.date.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Всего записей: {len(self.data)}</p>
    </div>
    <table>
        <tr>
"""
            for col in self.columns:
                html += f"            <th>{col}</th>\n"
            
            html += "        </tr>\n"
            
            for row in self.data:
                row_class = row.get("class", row.get("type", ""))
                html += f'        <tr class="{row_class}">\n'
                for i in range(len(self.columns)):
                    val = self._cell_value(row, i)
                    # Экранирование HTML-специальных символов
                    val = (
                        str(val)
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                    )
                    html += f"            <td>{val}</td>\n"
                html += "        </tr>\n"
            
            html += """    </table>
</body>
</html>"""
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            return True
        except (OSError, PermissionError) as e:
            print(f"Ошибка экспорта в HTML: {e}")
            return False
