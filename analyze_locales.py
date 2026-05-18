import json
import sys

with open(r'locales\en.json', 'r', encoding='utf-8') as f:
    en_data = json.load(f)
with open(r'locales\ru.json', 'r', encoding='utf-8') as f:
    ru_data = json.load(f)
with open(r'locales\ua.json', 'r', encoding='utf-8') as f:
    ua_data = json.load(f)
with open(r'locales\ja.json', 'r', encoding='utf-8') as f:
    ja_data = json.load(f)

en_keys = set(en_data.get('en', {}).keys())
ru_keys = set(ru_data.get('ru', {}).keys())
ua_keys = set(ua_data.get('ua', {}).keys())
ja_keys = set(ja_data.get('ja', {}).keys())

out = sys.stdout

out.write("=" * 60 + "\n")
out.write("STATISTICS\n")
out.write("=" * 60 + "\n")
out.write(f"en.json: {len(en_keys)} keys\n")
out.write(f"ru.json: {len(ru_keys)} keys\n")
out.write(f"ua.json: {len(ua_keys)} keys\n")
out.write(f"ja.json: {len(ja_keys)} keys\n")
out.write("\n")

missing_in_ru = sorted(en_keys - ru_keys)
out.write(f"MISSING in ru.json (in en but not ru): {len(missing_in_ru)}\n")
for k in missing_in_ru:
    out.write(f"  {k}\n")
out.write("\n")

extra_in_ru = sorted(ru_keys - en_keys)
out.write(f"EXTRA in ru.json (not in en): {len(extra_in_ru)}\n")
for k in extra_in_ru:
    out.write(f"  {k}\n")
out.write("\n")

missing_in_ua = sorted(en_keys - ua_keys)
out.write(f"MISSING in ua.json: {len(missing_in_ua)}\n")
for k in missing_in_ua:
    out.write(f"  {k}\n")
out.write("\n")

missing_in_ja = sorted(en_keys - ja_keys)
out.write(f"MISSING in ja.json: {len(missing_in_ja)}\n")
for k in missing_in_ja:
    out.write(f"  {k}\n")
out.write("\n")

# Check TODO/empty
for lang_name, lang_section in [('ru', ru_data.get('ru', {})), ('ua', ua_data.get('ua', {})), ('ja', ja_data.get('ja', {}))]:
    todo_empty = []
    for k, v in lang_section.items():
        val_stripped = str(v).strip()
        if val_stripped.upper() == 'TODO' or val_stripped == '':
            todo_empty.append((k, v))
    out.write(f"TODO/EMPTY in {lang_name}.json: {len(todo_empty)}\n")
    for k, v in todo_empty:
        out.write(f"  {k}: '{v}'\n")
    out.write("\n")

target = ['translation_fuzzy', 'translation_clear_cache', 'translation_cache_cleared', 'translation_cache_empty']
out.write("SPECIFIC KEYS CHECK:\n")
for tk in target:
    en_v = en_data['en'].get(tk, 'MISSING')
    ru_v = ru_data['ru'].get(tk, 'MISSING')
    ua_v = ua_data.get('ua', {}).get(tk, 'MISSING')
    ja_v = ja_data.get('ja', {}).get(tk, 'MISSING')
    out.write(f"  {tk}:\n")
    out.write(f"    en: {en_v}\n")
    out.write(f"    ru: {ru_v}\n")
    out.write(f"    ua: {ua_v}\n")
    out.write(f"    ja: {ja_v}\n")
out.write("\n")

# Completion stats
out.write("COMPLETENESS vs en.json:\n")
for lang_name, lang_section, lang_key_set in [
    ('ru', ru_data.get('ru', {}), ru_keys),
    ('ua', ua_data.get('ua', {}), ua_keys),
    ('ja', ja_data.get('ja', {}), ja_keys)
]:
    translated = 0
    missing = 0
    todo = 0
    for k in en_keys:
        if k not in lang_key_set:
            missing += 1
        else:
            v = str(lang_section.get(k, '')).strip()
            if v.upper() == 'TODO' or v == '':
                todo += 1
            else:
                translated += 1
    out.write(f"  {lang_name}: {translated} translated, {todo} TODO/empty, {missing} missing (out of {len(en_keys)})\n")
