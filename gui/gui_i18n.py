# gui_i18n.py - Система интернационализации
import json
import locale
from pathlib import Path

# Поддержка обоих форматов:
# 1. Папка locales/ (новый формат, рекомендуется)
# 2. translations.json (старый формат, обратная совместимость)
LOCALES_DIR = Path(__file__).parent.parent / "locales"
TRANSLATIONS_FILE = Path(__file__).parent.parent / "translations.json"


def _detect_system_language():
    """
    Определяет язык системы пользователя.

    Returns:
        Код языка ('ru', 'en', 'de', 'ja', 'ua') или 'en' по умолчанию
    """
    try:
        # Получаем локаль системы
        system_locale = locale.getdefaultlocale()[0]
        if not system_locale:
            return "en"

        # Извлекаем код языка (например, 'ru_RU' -> 'ru')
        lang_code = system_locale.split("_")[0].lower()

        # Маппинг поддерживаемых языков
        supported_languages = {
            "ru": "ru",
            "en": "en",
            "de": "de",
            "ja": "ja",
            "uk": "ua",  # Украина использует 'uk' в системе, но 'ua' в приложении
            "ua": "ua",
            "pl": "pl",
        }

        return supported_languages.get(lang_code, "en")
    except Exception:
        return "en"


class I18N:
    def __init__(self):
        self.translations = {}
        # ✅ Автоопределение языка системы вместо хардкода
        self.current_language = _detect_system_language()
        self._load_translations()

    def _load_translations(self):
        """Загружает переводы из locales/*.json или translations.json"""
        try:
            # Приоритет: папка locales/ (новый формат)
            if LOCALES_DIR.exists() and LOCALES_DIR.is_dir():
                self._load_from_locales_dir()
            # Fallback: translations.json (старый формат)
            elif TRANSLATIONS_FILE.exists():
                self._load_from_single_file()
            else:
                print("⚠️ Файлы переводов не найдены")
                self.translations = {"ru": {}, "en": {}}
        except Exception as e:
            print(f"❌ Ошибка загрузки переводов: {e}")
            self.translations = {"ru": {}, "en": {}}

    def _load_from_locales_dir(self):
        """Загрузка из отдельных файлов locales/{lang}.json"""
        self.translations = {}
        for lang_file in LOCALES_DIR.glob("*.json"):
            if lang_file.name == "README.md":
                continue
            try:
                with open(lang_file, encoding="utf-8") as f:
                    data = json.load(f)

                    # Пропускаем _meta при обработке
                    lang_code = None
                    translations = None

                    if len(data) == 1:
                        # {"ru": {...}} - старый формат без _meta
                        lang_code = list(data.keys())[0]
                        translations = data[lang_code]
                    else:
                        # {"_meta": {...}, "ru": {...}} - новый формат с _meta
                        # Находим ключ который НЕ _meta
                        for key in data.keys():
                            if key != "_meta":
                                lang_code = key
                                translations = data[key]
                                break

                        # Если не нашли - используем имя файла
                        if lang_code is None:
                            lang_code = lang_file.stem
                            translations = data

                    if translations and isinstance(translations, dict):
                        self.translations[lang_code] = translations
            except Exception as e:
                print(f"⚠️ Ошибка загрузки {lang_file.name}: {e}")

    def _load_from_single_file(self):
        """Загрузка из единого файла translations.json"""
        with open(TRANSLATIONS_FILE, encoding="utf-8") as f:
            self.translations = json.load(f)

    def set_language(self, lang_code):
        """
        Устанавливает текущий язык.

        Args:
            lang_code: Код языка ('ru', 'en', 'de', и т.д.)

        Returns:
            True если язык установлен успешно
        """
        if lang_code in self.translations:
            self.current_language = lang_code
            print(f"✅ Язык изменён на: {self.get_language_name(lang_code)}")
            return True
        print(f"⚠️ Язык '{lang_code}' не найден")
        return False

    def get_language_name(self, lang_code):
        names = {
            "ru": "🇷🇺 Русский",
            "en": "🇬🇧 English",
            "de": "🇩🇪 Deutsch",
            "pl": "🇵🇱 Polski",
            "ja": "🇯🇵 日本語",
            "ua": "🇺🇦 Українська",
            "zh": "🇨🇳 中文",
            "fr": "🇫🇷 Français",
            "es": "🇪🇸 Español",
        }
        return names.get(lang_code, lang_code)

    def get_available_languages(self):
        return list(self.translations.keys())

    def tr(self, key, default=None):
        lang_data = self.translations.get(self.current_language, {})
        return lang_data.get(key, default or key)

    def get_current_language_with_name(self):
        """Возвращает текущий язык с названием для отображения."""
        return self.get_language_name(self.current_language)


i18n = I18N()


def tr(key, default=None):
    return i18n.tr(key, default)
