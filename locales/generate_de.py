#!/usr/bin/env python3
"""
Генерация de.json из en.json через deep_translator.GoogleTranslator.
"""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOCALES_DIR = os.path.dirname(os.path.abspath(__file__))
EN_FILE = os.path.join(LOCALES_DIR, "en.json")
DE_FILE = os.path.join(LOCALES_DIR, "de.json")

def main():
    from deep_translator import GoogleTranslator

    with open(EN_FILE, encoding="utf-8") as f:
        en_data = json.load(f)

    en_translations = en_data.get("en", {})
    meta = en_data.get("_meta", {})

    total = len(en_translations)
    print(f"Translating {total} keys EN->DE via GoogleTranslator...")

    translator = GoogleTranslator(source="en", target="de")

    de_translations = {}
    count = 0

    for key, value in en_translations.items():
        count += 1
        if not value or not value.strip():
            de_translations[key] = value
            continue

        stripped = value.strip()
        # Skip URLs, JSON, codes
        if stripped.startswith("http") or stripped.startswith("{") or stripped.startswith("["):
            de_translations[key] = value
            continue

        try:
            result = translator.translate(stripped)
            de_translations[key] = result if result and result.strip() else value
        except Exception as e:
            print(f"  Error at {count} '{key}': {e}")
            de_translations[key] = value
            time.sleep(2)  # Pause on error

        if count % 50 == 0:
            print(f"  {count}/{total}...")
            time.sleep(0.5)

    print(f"Done: {count} keys")

    de_data = {
        "_meta": {
            "language": "de",
            "language_name": "Deutsch",
            "native_name": "Deutsch",
            "translator": "Auto-generated from en.json via Google Translate",
            "project_version": meta.get("project_version", "2.4"),
            "last_updated": "2026-05-26",
            "total_keys": len(de_translations),
            "translated_keys": len(de_translations),
            "completion_percentage": 100.0,
            "review_status": "auto-generated",
        },
        "de": de_translations
    }

    with open(DE_FILE, "w", encoding="utf-8") as f:
        json.dump(de_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] {DE_FILE} created: {len(de_translations)} keys")

if __name__ == "__main__":
    main()
