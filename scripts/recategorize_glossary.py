#!/usr/bin/env python
"""
Скрипт для перекатегоризации seed-терминов в глоссарии.
Запускает перекатегоризацию для всех языков.
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from translation_db import get_translation_db, clear_db_instances
from translation.glossary_utils import determine_category


def recategorize_language(target_language: str):
    """Перекатегоризует seed-термины для указанного языка."""
    print(f"\n=== Обработка языка: {target_language} ===")
    
    try:
        db = get_translation_db(target_language)
        
        # Get all seed entries
        c = db.conn.cursor()
        c.execute("SELECT id, term, translation FROM glossary WHERE target_language = ? AND category = 'seed'", (target_language,))
        seed_entries = c.fetchall()
        
        print(f"Найдено seed-терминов: {len(seed_entries)}")
        
        # Categorize and update
        updated_count = 0
        categorized_count = 0
        uncategorized_count = 0
        category_stats = {}
        
        for entry in seed_entries:
            entry_id = entry[0] if hasattr(entry, '__getitem__') else getattr(entry, 'id', None)
            term = entry[1] if hasattr(entry, '__getitem__') else getattr(entry, 'term', None)
            
            if entry_id is None or term is None:
                continue
                
            new_category = determine_category(term)
            if new_category:
                c.execute("UPDATE glossary SET category = ? WHERE id = ?", (new_category, entry_id))
                updated_count += 1
                categorized_count += 1
                category_stats[new_category] = category_stats.get(new_category, 0) + 1
            else:
                uncategorized_count += 1
        
        db.conn.commit()
        print(f"Перекатегоризовано: {updated_count}")
        print(f"Категоризировано: {categorized_count}")
        print(f"Оставлено в seed: {uncategorized_count}")
        
        # Print category breakdown
        if category_stats:
            print("\nРаспределение по категориям:")
            for cat, count in sorted(category_stats.items(), key=lambda x: -x[1]):
                print(f"  {cat}: {count}")
        
        # Sync to JSON files
        print("\nСинхронизация с JSON файлами...")
        db._sync_glossary_to_json(target_language)
        
        return updated_count
        
    except Exception as e:
        print(f"Ошибка при обработке {target_language}: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Главная функция."""
    # Supported languages
    languages = ["Russian", "English", "German", "French", "Spanish", "Ukrainian"]
    
    total_updated = 0
    for lang in languages:
        total_updated += recategorize_language(lang)
    
    print(f"\n=== ИТОГО ===")
    print(f"Всего перекатегоризовано терминов: {total_updated}")
    
    # Clear singleton instances
    clear_db_instances()


if __name__ == "__main__":
    main()