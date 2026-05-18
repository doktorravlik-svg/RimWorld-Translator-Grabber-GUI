#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт автоматического обновления метаданных (_meta) в файлах переводов.
Добавляет информацию о переводчике, дате, версии и количестве ключей.
"""

import json
from pathlib import Path
from datetime import datetime

LOCALES_DIR = Path(__file__).parent.parent / "locales"

# Информация о проекте
PROJECT_INFO = {
    "project_name": "RimWorld Translator Grabber",
    "version": "2.1.0",
    "translator": "RimWorld Translator Team",
    "source_language": "en",
    "review_status": "approved"
}

# Информация по языкам
LANG_INFO = {
    "ru": {"language_name": "Русский", "native_name": "Русский"},
    "en": {"language_name": "English", "native_name": "English"},
    "ua": {"language_name": "Українська", "native_name": "Українська"},
    "ja": {"language_name": "日本語", "native_name": "日本語"},
}

def update_metadata():
    """Обновить _meta во всех файлах locales"""
    print("🔧 Обновление метаданных переводов...\n")
    
    for lang_file in sorted(LOCALES_DIR.glob("*.json")):
        lang_code = lang_file.stem
        if lang_code not in LANG_INFO:
            continue
            
        with open(lang_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Находим переводы (пропускаем _meta если есть)
        translations = {}
        for k, v in data.items():
            if k != "_meta":
                translations[k] = v
        
        # Если структура {"ru": {...}}
        actual_lang = lang_code
        if len(translations) == 1:
            actual_lang = list(translations.keys())[0]
            translations = translations[actual_lang]
            
        total_keys = len(translations)
        
        # Создаём _meta
        meta = {
            "language": actual_lang,
            "language_name": LANG_INFO.get(lang_code, {}).get("language_name", lang_code),
            "native_name": LANG_INFO.get(lang_code, {}).get("native_name", lang_code),
            "translator": PROJECT_INFO["translator"],
            "project_version": PROJECT_INFO["version"],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "total_keys": total_keys,
            "translated_keys": total_keys,
            "completion_percentage": 100.0,
            "review_status": PROJECT_INFO["review_status"]
        }
        
        # Формируем новый файл
        new_data = {"_meta": meta}
        new_data[actual_lang] = translations
        
        with open(lang_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ {lang_file.name}: {total_keys} ключей, статус: {meta['review_status']}")
        
    print("\n✨ Готово!")

if __name__ == "__main__":
    update_metadata()
