🌍 Interface Localization
This folder contains translation files for RimWorld Translator Grabber.

📁 File Structure
Each language is stored in a separate file with a simple name:
locales/
├── ru.json      # Русский
├── en.json      # English
├── ua.json      # Українська
├── ja.json      # 日本語
└── README.md    # This file

🚀 How to Add a New Language (5 minutes)
**Step 1: Create a Translation File**
Copy an existing file (e.g., `en.json`) and rename it to `{language_code}.json`:
# Example for German:
copy locales\en.json locales\de.json

Popular language codes:
- `de` — Deutsch (German)
- `fr` — Français (French)
- `es` — Español (Spanish)
- `it` — Italiano (Italian)
- `pl` — Polski (Polish)
- `zh` — 中文 (Chinese)
- `ko` — 한국어 (Korean)

**Step 2: Translate Values**
Open the file and translate only the values (right side). Do NOT change the keys!
{
  "de": {
    "app_title": "RimWorld Translator Grabber",  ← translated
    "menu_file": "Datei",                        ← translated
    "menu_exit": "Beenden",                      ← translated
    ...
  }
}
❌ DO NOT:
{
  "menu_file": "Datei",  ← key changed — BAD!
}
✅ DO:
{
  "menu_file": "Datei"  ← key preserved, value translated — GOOD!
}

**Step 3: Validate the File**
python -c "import json; json.load(open('locales/de.json',encoding='utf-8')); print('✅ File is valid!')"
Or run extended validation:
python scripts/validate_locales.py locales/de.json

**Step 4: Test**
- Launch the application
- Open the 🌐 Interface Language menu
- Select the new language
- Verify that all texts are translated

**Step 5: Submit a PR**
Create a Pull Request with your translation file.

🔧 Automatic Installation
A new language appears automatically when a `locales/{code}.json` file exists.
No additional registration required!

📝 Translation Rules
**Formatting**
✅ Use UTF-8 encoding
✅ Preserve emojis (📦, ✅, 🌐, etc.)
✅ Preserve trailing spaces in lines (if present in the original)

**Special Characters**
- `\n` — new line
- `\"` — quote inside a string
- `\\` — backslash

**Translation Status**
You can add a comment at the beginning of the file:
{
  "_meta": {
    "language": "de",
    "translator": "YourName",
    "last_updated": "2026-04-05",
    "completion": "100%"
  },
  "de": {
    ...
  }
}

🐛 Troubleshooting
**Translation not loading**
- Cause: Invalid JSON file
- Solution: Validate the file using `python -m json.tool locales/de.json`

**Some strings not translated**
- Cause: Missing keys
- Solution: Compare with `en.json` and add missing keys

**Text gets cut off**
- Cause: Translation too long
- Solution: Shorten the text or use abbreviations

💡 Tips
- Use the original file as a template — don't start from scratch
- Context matters — keys indicate where the string is used:
  - `menu.*` — menu items
  - `tab.*` — tab names
  - `editor.*` — translation editor
  - `dialog.*` — dialog windows
  - `status.*` — status bar
- Test frequently — run the app after every 50-100 lines
- Preserve emojis — they are part of the UI

📞 Help
If you have questions — create an Issue on GitHub or contact the developers.

✨ Thank you for contributing to localization!