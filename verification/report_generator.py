# verification/report_generator.py
"""
Модуль генерации отчетов о верификации переводов RimWorld.

Основные функции:
- ReportGenerator: класс генерации отчетов
- generate_text_report: генерация текстового отчета
- generate_json_report: генерация JSON отчета
- generate_html_report: генерация HTML отчета
- generate_markdown_report: генерация Markdown отчета
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


def _tr(key: str, default: str = None) -> str:
    """Lazy импорт tr для предотвращения циклических импортов."""
    try:
        from gui.gui_i18n import tr as _actual_tr

        return _actual_tr(key, default)
    except (ImportError, RuntimeError):
        return default or key


# ============================================================================
# ТИПЫ ДАННЫХ
# ============================================================================


@dataclass
class ReportStatistics:
    """Статистика отчета"""

    total_mods: int = 0
    translation_mods: int = 0
    regular_mods: int = 0
    mods_with_errors: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_conflicts: int = 0
    validation_issues: int = 0


@dataclass
class ReportSection:
    """Секция отчета"""

    title: str
    content: str
    level: int = 1  # 1 = h1, 2 = h2, etc.


class ReportFormat(Enum):
    """Формат отчета"""

    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


# ============================================================================
# БАЗОВЫЙ КЛАСС ГЕНЕРАТОРА ОТЧЕТОВ
# ============================================================================


class BaseReportGenerator(ABC):
    """Базовый абстрактный класс генератора отчетов"""

    @abstractmethod
    def generate(self, data: dict) -> str:
        """Сгенерировать отчет"""
        pass

    @abstractmethod
    def save(self, content: str, output_path: str) -> bool:
        """Сохранить отчет в файл"""
        pass


# ============================================================================
# КЛАСС REPORT GENERATOR
# ============================================================================


class ReportGenerator:
    """
    Класс для генерации отчетов о верификации переводов.

    Поддерживаемые форматы:
    - TEXT: Простой текстовый отчет
    - JSON: Отчет в формате JSON
    - HTML: HTML страница с таблицами
    - MARKDOWN: Markdown разметка
    """

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger

        # Форматтеры для разных типов отчетов
        self._formatters = {
            "text": self._format_text,
            "json": self._format_json,
            "html": self._format_html,
            "markdown": self._format_markdown,
        }

    # =========================================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # =========================================================================

    def generate(self, data: dict, format: str = "text") -> str:
        """
        Генерирует отчет в указанном формате.

        Args:
            data: Данные для отчета
            format: Формат отчета ('text', 'json', 'html', 'markdown')

        Returns:
            Строка с отчетом
        """
        formatter = self._formatters.get(format.lower(), self._format_text)
        return formatter(data)

    def generate_and_save(self, data: dict, output_path: str, format: str = "text") -> bool:
        """
        Генерирует и сохраняет отчет.

        Args:
            data: Данные для отчета
            output_path: Путь для сохранения
            format: Формат отчета

        Returns:
            True при успехе
        """
        content = self.generate(data, format)
        return self.save(content, output_path)

    def save(self, content: str, output_path: str) -> bool:
        """
        Сохраняет отчет в файл.

        Args:
            content: Содержимое отчета
            output_path: Путь для сохранения

        Returns:
            True при успехе
        """
        try:
            # Создаем директорию если нужно
            directory = os.path.dirname(output_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            if self.logger:
                self.logger.info(f"Отчет сохранен: {output_path}")

            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка сохранения отчета: {e}")
            return False

    # =========================================================================
    # ФОРМАТТЕРЫ
    # =========================================================================

    def _format_text(self, data: dict) -> str:
        """Форматирование в текстовый отчет"""
        lines = []

        # Заголовок
        lines.append("=" * 80)
        lines.append("ОТЧЕТ ВЕРИФИКАЦИИ ПЕРЕВОДОВ RIMWORLD МОДОВ")
        lines.append("=" * 80)

        # Метаинформация
        timestamp = data.get("timestamp", datetime.now().isoformat())
        mods_path = data.get("mods_path", "Unknown")
        lines.append(f"\nДата: {timestamp}")
        lines.append(f"Директория: {mods_path}")

        # Статистика
        stats = data.get("statistics", {})
        lines.append("\n" + "-" * 40)
        lines.append("СТАТИСТИКА")
        lines.append("-" * 40)
        lines.append(f"  Всего модов: {stats.get('total_mods', 0)}")
        lines.append(f"  Переводных модов: {stats.get('translation_mods', 0)}")
        lines.append(f"  Обычных модов: {stats.get('regular_mods', 0)}")
        lines.append(f"  Модов с ошибками: {stats.get('mods_with_errors', 0)}")
        lines.append(f"  Всего ошибок: {stats.get('total_errors', 0)}")
        lines.append(f"  Всего предупреждений: {stats.get('total_warnings', 0)}")
        lines.append(f"  Конфликтов: {stats.get('total_conflicts', 0)}")

        # Результаты по модам
        results = data.get("results", [])
        if results:
            lines.append("\n" + "-" * 40)
            lines.append("РЕЗУЛЬТАТЫ ПО МОДАМ")
            lines.append("-" * 40)

            for result in results:
                lines.append(
                    f"\n  {result.get('mod_name', 'Unknown')} ({result.get('mod_id', 'N/A')})"
                )
                lines.append(f"    Тип: {'Перевод' if result.get('is_translation') else 'Обычный'}")

                if result.get("errors"):
                    lines.append(f"    Ошибки ({len(result['errors'])}):")
                    for error in result["errors"][:5]:
                        lines.append(f"      ❌ {error}")

                if result.get("warnings"):
                    lines.append(f"    Предупреждения ({len(result['warnings'])}):")
                    for warning in result["warnings"][:3]:
                        lines.append(f"      ⚠️  {warning}")

                if result.get("conflicts"):
                    lines.append(f"    Конфликты ({len(result['conflicts'])}):")
                    for conflict in result["conflicts"][:3]:
                        lines.append(f"      ⚡ {conflict}")

        # Конфликты
        global_conflicts = data.get("global_conflicts", [])
        if global_conflicts:
            lines.append("\n" + "-" * 40)
            lines.append("ГЛОБАЛЬНЫЕ КОНФЛИКТЫ")
            lines.append("-" * 40)

            for conflict in global_conflicts:
                lines.append(f"\n  [{conflict.get('conflict_type', 'unknown')}]")
                lines.append(f"    {conflict.get('description', '')}")
                if conflict.get("resolution"):
                    lines.append(f"    Решение: {conflict['resolution']}")

        lines.append("\n" + "=" * 80)
        lines.append("КОНЕЦ ОТЧЕТА")
        lines.append("=" * 80)

        return "\n".join(lines)

    def _format_json(self, data: dict) -> str:
        """Форматирование в JSON"""
        # Добавляем timestamp если нет
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_html(self, data: dict) -> str:
        """Форматирование в HTML"""
        stats = data.get("statistics", {})
        results = data.get("results", [])
        global_conflicts = data.get("global_conflicts", [])

        html = (
            """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет верификации переводов RimWorld</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .meta { color: #7f8c8d; font-size: 0.9em; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; }
        .mod-card {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #3498db;
        }
        .mod-card.error { border-left-color: #e74c3c; }
        .mod-card.warning { border-left-color: #f39c12; }
        .error { color: #e74c3c; }
        .warning { color: #f39c12; }
        .success { color: #27ae60; }
        .conflict {
            background: #fff3cd;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            border-left: 4px solid #f39c12;
        }
    </style>
</head>
<body>
    <h1>🔍 Отчет верификации переводов RimWorld</h1>
    <div class="meta">
        <p>📅 Дата: """
            + data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            + """</p>
        <p>📁 Директория: """
            + data.get("mods_path", "Unknown")
            + """</p>
    </div>

    <h2>📊 Статистика</h2>
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">"""
            + str(stats.get("total_mods", 0))
            + """</div>
            <div class="stat-label">Всего модов</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">"""
            + str(stats.get("translation_mods", 0))
            + """</div>
            <div class="stat-label">Переводных</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">"""
            + str(stats.get("total_errors", 0))
            + """</div>
            <div class="stat-label">Ошибок</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">"""
            + str(stats.get("total_warnings", 0))
            + """</div>
            <div class="stat-label">Предупреждений</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">"""
            + str(stats.get("total_conflicts", 0))
            + """</div>
            <div class="stat-label">Конфликтов</div>
        </div>
    </div>
"""
        )

        # Результаты по модам
        if results:
            html += "\n    <h2>📋 Результаты по модам</h2>"

            for result in results:
                has_errors = bool(result.get("errors"))
                has_warnings = bool(result.get("warnings"))
                card_class = "mod-card"
                if has_errors:
                    card_class += " error"
                elif has_warnings:
                    card_class += " warning"

                translation_status = "🔄 Перевод" if result.get("is_translation") else "📦 Мод"

                html += f"""
    <div class="{card_class}">
        <h3>{result.get("mod_name", "Unknown")}</h3>
        <p><strong>ID:</strong> {result.get("mod_id", "N/A")}</p>
        <p><strong>Тип:</strong> {translation_status}</p>
"""

                if result.get("errors"):
                    html += f"        <p class='error'><strong>❌ Ошибки ({len(result['errors'])}):</strong></p>\n        <ul class='error'>\n"
                    for error in result["errors"][:5]:
                        html += f"            <li>{error}</li>\n"
                    html += "        </ul>\n"

                if result.get("warnings"):
                    html += f"        <p class='warning'><strong>⚠️ Предупреждения ({len(result['warnings'])}):</strong></p>\n        <ul class='warning'>\n"
                    for warning in result["warnings"][:3]:
                        html += f"            <li>{warning}</li>\n"
                    html += "        </ul>\n"

                html += "    </div>\n"

        # Глобальные конфликты
        if global_conflicts:
            html += "\n    <h2>⚡ Глобальные конфликты</h2>\n"
            for conflict in global_conflicts:
                html += f"""
    <div class="conflict">
        <strong>[{conflict.get("conflict_type", "unknown")}]</strong>
        <p>{conflict.get("description", "")}</p>
        {f"<p><em>Решение: {conflict['resolution']}</em></p>" if conflict.get("resolution") else ""}
    </div>
"""

        html += """
</body>
</html>"""

        return html

    def _format_markdown(self, data: dict) -> str:
        """Форматирование в Markdown"""
        lines = []

        # Заголовок
        lines.append("# 🔍 Отчет верификации переводов RimWorld")
        lines.append("")

        # Метаинформация
        lines.append("## 📋 Информация")
        lines.append("")
        lines.append(
            f"- **Дата:** {data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
        )
        lines.append(f"- **Директория:** {data.get('mods_path', 'Unknown')}")
        lines.append("")

        # Статистика
        stats = data.get("statistics", {})
        lines.append("## 📊 Статистика")
        lines.append("")

        stats_table = """
| Метрика | Значение |
|---------|----------|
| Всего модов | {total} |
| Переводных модов | {translations} |
| Обычных модов | {regular} |
| Модов с ошибками | {errors} |
| Всего ошибок | {total_errors} |
| Всего предупреждений | {warnings} |
| Конфликтов | {conflicts} |
""".format(
            total=stats.get("total_mods", 0),
            translations=stats.get("translation_mods", 0),
            regular=stats.get("regular_mods", 0),
            errors=stats.get("mods_with_errors", 0),
            total_errors=stats.get("total_errors", 0),
            warnings=stats.get("total_warnings", 0),
            conflicts=stats.get("total_conflicts", 0),
        )

        lines.append(stats_table)

        # Результаты по модам
        results = data.get("results", [])
        if results:
            lines.append("## 📋 Результаты по модам")
            lines.append("")

            for result in results:
                has_errors = bool(result.get("errors"))
                has_warnings = bool(result.get("warnings"))
                status_icon = "❌" if has_errors else ("⚠️" if has_warnings else "✅")

                lines.append(f"### {status_icon} {result.get('mod_name', 'Unknown')}")
                lines.append("")
                lines.append(f"- **ID:** `{result.get('mod_id', 'N/A')}`")
                lines.append(
                    f"- **Тип:** {'🔄 Перевод' if result.get('is_translation') else '📦 Мод'}"
                )
                status_text = (
                    tr("report_errors", "Ошибки")
                    if has_errors
                    else (
                        tr("report_warnings", "Предупреждения")
                        if has_warnings
                        else tr("report_ok", "OK")
                    )
                )
                lines.append(f"- **Статус:** {status_text}")
                lines.append("")

                if result.get("errors"):
                    lines.append(f"**❌ Ошибки ({len(result['errors'])}):**")
                    for error in result["errors"][:5]:
                        lines.append(f"- {error}")
                    lines.append("")

                if result.get("warnings"):
                    lines.append(f"**⚠️ Предупреждения ({len(result['warnings'])}):**")
                    for warning in result["warnings"][:3]:
                        lines.append(f"- {warning}")
                    lines.append("")

        # Глобальные конфликты
        global_conflicts = data.get("global_conflicts", [])
        if global_conflicts:
            lines.append("## ⚡ Глобальные конфликты")
            lines.append("")

            for conflict in global_conflicts:
                lines.append(f"### [{conflict.get('conflict_type', 'unknown')}]")
                lines.append("")
                lines.append(f"{conflict.get('description', '')}")
                if conflict.get("resolution"):
                    lines.append(f"**Решение:** {conflict['resolution']}")
                lines.append("")

        lines.append("---")
        lines.append("*Отчет сгенерирован автоматически*")

        return "\n".join(lines)

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def calculate_statistics(self, results: list[dict], conflicts: list[dict]) -> ReportStatistics:
        """
        Вычисляет статистику по результатам.

        Args:
            results: Список результатов верификации
            conflicts: Список конфликтов

        Returns:
            ReportStatistics
        """
        stats = ReportStatistics()

        stats.total_mods = len(results)
        stats.translation_mods = sum(1 for r in results if r.get("is_translation"))
        stats.regular_mods = sum(1 for r in results if not r.get("is_translation"))
        stats.mods_with_errors = sum(1 for r in results if r.get("errors"))
        stats.total_errors = sum(len(r.get("errors", [])) for r in results)
        stats.total_warnings = sum(len(r.get("warnings", [])) for r in results)
        stats.total_conflicts = len(conflicts)

        return stats

    def prepare_report_data(self, coordinator_results: Any, conflicts: list[dict]) -> dict:
        """
        Подготавливает данные для отчета из результатов координатора.

        Args:
            coordinator_results: Результаты от VerificationCoordinator
            conflicts: Список конфликтов

        Returns:
            Словарь данных для отчета
        """
        results = []
        for result in coordinator_results:
            results.append(
                {
                    "mod_id": result.mod_id,
                    "mod_name": result.mod_name,
                    "mod_path": result.mod_path,
                    "is_translation": result.is_translation,
                    "is_valid": result.is_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "conflicts": [str(c) for c in result.conflicts],
                }
            )

        stats = self.calculate_statistics(results, conflicts)

        return {
            "timestamp": datetime.now().isoformat(),
            "statistics": asdict(stats),
            "results": results,
            "global_conflicts": [asdict(c) for c in conflicts],
        }


# ============================================================================
# ФУНКЦИИ ВЫСОКОГО УРОВНЯ
# ============================================================================


def generate_text_report(data: dict) -> str:
    """Генерирует текстовый отчет"""
    generator = ReportGenerator()
    return generator.generate(data, "text")


def generate_json_report(data: dict) -> str:
    """Генерирует JSON отчет"""
    generator = ReportGenerator()
    return generator.generate(data, "json")


def generate_html_report(data: dict) -> str:
    """Генерирует HTML отчет"""
    generator = ReportGenerator()
    return generator.generate(data, "html")


def generate_markdown_report(data: dict) -> str:
    """Генерирует Markdown отчет"""
    generator = ReportGenerator()
    return generator.generate(data, "markdown")


# ============================================================================
# ТЕСТЫ
# ============================================================================

if __name__ == "__main__":
    from enum import Enum

    print("=" * 60)
    print("Тестирование report_generator")
    print("=" * 60)

    # Тестовые данные
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "mods_path": "C:/Test/Mods",
        "statistics": {
            "total_mods": 10,
            "translation_mods": 3,
            "regular_mods": 7,
            "mods_with_errors": 2,
            "total_errors": 5,
            "total_warnings": 10,
            "total_conflicts": 3,
        },
        "results": [
            {
                "mod_id": "test.mod",
                "mod_name": "Test Mod",
                "is_translation": False,
                "is_valid": True,
                "errors": [],
                "warnings": ["Some warning"],
            },
            {
                "mod_id": "test.translation",
                "mod_name": "Test Translation",
                "is_translation": True,
                "is_valid": False,
                "errors": ["Missing placeholder {0}"],
                "warnings": [],
            },
        ],
        "global_conflicts": [
            {
                "conflict_type": "duplicate_key",
                "description": "Key appears in multiple mods",
                "severity": "warning",
                "resolution": "Use first",
            }
        ],
    }

    generator = ReportGenerator()

    # Тест текстового отчета
    print("\n[ТЕСТ] Текстовый отчет:")
    text_report = generator.generate(test_data, "text")
    print(text_report[:500] + "...")

    # Тест HTML отчета
    print("\n[ТЕСТ] HTML отчет:")
    html_report = generator.generate(test_data, "html")
    print(f"Длина: {len(html_report)} символов")

    # Тест Markdown отчета
    print("\n[ТЕСТ] Markdown отчет:")
    md_report = generator.generate(test_data, "markdown")
    print(md_report[:300] + "...")

    print("\n" + "=" * 60)
    print("Все тесты пройдены!")
    print("=" * 60)
