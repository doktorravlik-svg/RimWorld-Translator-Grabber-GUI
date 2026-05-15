#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт генерации отчёта о статусах переводов.
Читает _meta из всех файлов locales и выводит красивую таблицу.
"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent.parent / "locales"

def generate_report():
    """Сгенерировать отчёт о статусах переводов"""
    print("=" * 65)
    print("              СТАТУС ПЕРЕВОДОВ ПРОЕКТА")
    print("=" * 65)
    
    headers = ["Язык", "Ключи", "%", "Обновлён", "Статус"]
    rows = []
    
    for lang_file in sorted(LOCALES_DIR.glob("*.json")):
        with open(lang_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        meta = data.get("_meta", {})
        if not meta:
            continue
            
        lang_name = meta.get("language_name", lang_file.stem)
        native_name = meta.get("native_name", "")
        total = meta.get("total_keys", 0)
        translated = meta.get("translated_keys", 0)
        pct = meta.get("completion_percentage", 0.0)
        updated = meta.get("last_updated", "—")
        review = meta.get("review_status", "unknown")
        
        review_icon = "✅" if review == "approved" else "⚠️"
        rows.append([
            f"{lang_name} ({native_name})",
            f"{translated}/{total}",
            f"{pct:.1f}%",
            updated,
            f"{review_icon} {review}"
        ])
        
    # Печатаем таблицу
    # Вычисляем ширину колонок
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
            
    def print_row(cells):
        row_str = " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cells))
        print(f"| {row_str} |")
        
    # Заголовок
    print_row(headers)
    print("-" * (sum(col_widths) + 3 * len(headers) + 2))
    
    # Строки
    for row in rows:
        print_row(row)
        
    print("=" * 65)
    print(f"\n✨ Всего языков: {len(rows)}")
    print(f"📁 Папка переводов: {LOCALES_DIR.absolute()}")

if __name__ == "__main__":
    generate_report()
