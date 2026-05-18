import os
import sys
import tempfile
from collections import defaultdict

import pymorphy3

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from loguru import logger


class RimWorldUniversalParser:
    """Універсальний парсер для генерації RulePackDef XML з текстових файлів Strings.

    Підтримує:
    - RU, UA: склонення через pymorphy3 (4 роди)
    - PL, DE, FR: через spacy (якщо встановлено)
    - EN, JP, KO, ZH: просте копіювання
    """

    # Словник для збереження слів за категоріями
    WORD_CATEGORIES = ['AdjM', 'AdjF', 'AdjN', 'NounM', 'NounF', 'NounN']

    def __init__(self, lang='ru'):
        self.lang = lang.lower()
        logger.debug(f"RimWorldUniversalParser.__init__(lang='{lang}')")
        self.mode = 'simple'
        self.morph = None
        self.nlp = None

        # Словянські мови (флективні, 4 роди)
        if self.lang in ['ru', 'uk']:
            try:
                self.morph = pymorphy3.MorphAnalyzer(lang=self.lang)
                self.mode = 'slavic'
                logger.debug(f"pymorphy3 ініціалізовано для {self.lang}")
            except Exception as e:
                logger.warning(f"Не вдалося ініціалізувати pymorphy3 для {self.lang}: {e}")
                logger.info("Буде використано простий режим (без склонення)")

        # Європейські мови (через Spacy або простий режим з правильною структурою XML)
        elif self.lang in ['pl', 'de', 'fr']:
            self.mode = 'european'
            if SPACY_AVAILABLE:
                try:
                    models = {
                        'pl': 'pl_core_news_sm',
                        'de': 'de_core_news_sm',
                        'fr': 'fr_core_news_sm'
                    }
                    self.nlp = spacy.load(models[self.lang])
                    logger.debug(f"spacy модель завантажено для {self.lang}")
                except Exception as e:
                    logger.warning(f"Не вдалося завантажити модель spacy для {self.lang}: {e}")
                    logger.info("Буде використано базове склонення (без spacy)")

    def get_word_forms(self, word):
        """Повертає форми слова залежно від мови."""
        logger.debug(f"get_word_forms(word='{word}')")
        if self.mode == 'slavic' and self.morph:
            parsed = self.morph.parse(word)[0]
            try:
                return {
                    'masc': parsed.inflect({'sing', 'nomn', 'masc'}).word,
                    'femn': parsed.inflect({'sing', 'nomn', 'femn'}).word,
                    'neut': parsed.inflect({'sing', 'nomn', 'neut'}).word,
                    'plur': parsed.inflect({'plural', 'nomn'}).word
                }
            except Exception:
                base = word
                return {'masc': base, 'femn': base, 'neut': base, 'plur': base}

        elif self.mode == 'european' and self.nlp:
            doc = self.nlp(word)
            base = doc[0].lemma_.capitalize() if doc else word.capitalize()
            return {'base': base}

        return {'base': word.capitalize()}

    def _init_word_data(self):
        """Ініціалізує структуру даних для слів."""
        return {cat: set() for cat in self.WORD_CATEGORIES}

    def _process_adjective(self, parsed, word):
        """Обробляє прикметник та повертає слово для кожного роду."""
        result = {}
        try:
            result['AdjM'] = parsed.inflect({'masc', 'sing', 'nomn'}).word.capitalize()
        except Exception:
            result['AdjM'] = word.capitalize()

        try:
            result['AdjF'] = parsed.inflect({'femn', 'sing', 'nomn'}).word.capitalize()
        except Exception:
            result['AdjF'] = word.capitalize()

        try:
            result['AdjN'] = parsed.inflect({'neut', 'sing', 'nomn'}).word.capitalize()
        except Exception:
            result['AdjN'] = word.capitalize()

        return result

    def _process_noun(self, parsed, word):
        """Обробляє іменник та повертає слово з урахуванням роду."""
        result = {}
        if 'masc' in parsed.tag:
            result['NounM'] = word.capitalize()
        elif 'femn' in parsed.tag:
            result['NounF'] = word.capitalize()
        elif 'neut' in parsed.tag:
            result['NounN'] = word.capitalize()
        else:
            logger.warning(f"Не вдалося визначити рід іменника: '{word}'")
        return result

    def _process_word(self, word, data):
        """Обробляє одне слово та розподіляє його по категоріях.

        Args:
            word: Слово для обробки
            data: Словник для збереження результатів
        """
        if self.mode != 'slavic' or not self.morph:
            return

        parsed = self.morph.parse(word)[0]

        # Розподіляємо прикметники
        if 'ADJF' in parsed.tag:
            result = self._process_adjective(parsed, word)
            for key, val in result.items():
                data[key].add(val)

        # Розподіляємо іменники
        elif 'NOUN' in parsed.tag:
            result = self._process_noun(parsed, word)
            for key, val in result.items():
                data[key].add(val)

        else:
            logger.warning(f"Слово '{word}' не є прикметником або іменником, пропущено")

    def _read_words_from_file(self, input_txt):
        """Зчитує слова з файлу.

        Args:
            input_txt: Шлях до текстового файлу

        Returns:
            list: Список слів або None у разі помилки
        """
        if not os.path.exists(input_txt):
            logger.error(f"Файл не знайдено: {input_txt}")
            return None

        with open(input_txt, encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]

        if not words:
            logger.error(f"Файл порожній: {input_txt}")
            return None

        return words

    def _log_word_stats(self, data, output_path):
        """Логує статистику слів."""
        total = sum(len(v) for v in data.values())
        logger.info(f"Збалансований XML створено: {output_path}")
        logger.info(f"   Всього слів: {total}")
        for key, val in data.items():
            if val:
                logger.info(f"   - {key}: {len(val)}")

    def generate_xml(self, input_txt, def_name, output_path=None):
        """
        Генерує XML-файл RulePackDef з текстового файлу.

        Автоматично розподіляє слова на прикметники та іменники,
        правильно відмінює прикметники за родами.

        Args:
            input_txt: шлях до текстового файлу зі словами
            def_name: назва дефу (наприклад, 'Namer_Ratkin')
            output_path: шлях для збереження (за замовчуванням - в поточну папку)
        """
        logger.debug(f"generate_xml(input_txt='{input_txt}', def_name='{def_name}')")
        words = self._read_words_from_file(input_txt)
        if words is None:
            return None

        # Контейнери для розподілу слів по родах
        data = self._init_word_data()

        # Обробляємо слова
        for w in words:
            self._process_word(w, data)

        # Визначаємо шлях збереження
        output_path = output_path or f"RulePack_{def_name}_{self.lang}.xml"

        # Записуємо XML
        self._write_final_xml(data, def_name, output_path)
        self._log_word_stats(data, output_path)

        return output_path

    def _get_european_rules(self, def_name):
        """Повертає правила для європейських мов."""
        if self.lang == 'pl':
            rules = "    <li>r_name->[AdjM] [NounM]</li>\n"
            rules += "    <li>r_name->[AdjF] [NounF]</li>\n"
            rules += "    <li>r_name->[AdjN] [NounN]</li>\n"
        elif self.lang == 'de':
            rules = "    <li>r_name->[Adj][Noun]</li>\n"
        elif self.lang == 'fr':
            rules = "    <li>r_name->[AdjM] [NounM]</li>\n"
            rules += "    <li>r_name->[AdjF] [NounF]</li>\n"
        else:
            rules = "    <li>r_name->[Adj] [Noun]</li>\n"

        return f"  <{def_name}.rulePack.rulesStrings>\n{rules}  </{def_name}.rulePack.rulesStrings>\n"

    def batch_generate(self, input_files, def_name, output_dir=None):
        """
        Генерує XML для кількох файлів одразу.

        Args:
            input_files: список шляхів до текстових файлів
            def_name: базова назва дефу
            output_dir: папка для збереження
        """
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        results = []
        for i, input_file in enumerate(input_files):
            if output_dir:
                name = os.path.splitext(os.path.basename(input_file))[0]
                output_path = os.path.join(output_dir, f"RulePack_{def_name}_{name}_{self.lang}.xml")
            else:
                output_path = None

            # ✅ ИСПРАВЛЕНО: Використовуємо generate_balanced_xml для всіх мов
            result = self.generate_balanced_xml(input_file, def_name, output_path)
            if result:
                results.append(result)

        logger.info(f"Загалом створено {len(results)} файлів з {len(input_files)}")
        return results

    def generate_balanced_xml(self, input_txt, def_name, output_path=None, keyword=None):
        """
        Генерує XML з розподілом слів на прикметники та іменники.

        Автоматично визначає частину мови (прикметник/іменник) та
        правильно відмінює прикметники за родами.

        Args:
            input_txt: шлях до текстового файлу зі словами
            def_name: назва дефу (наприклад, 'Namer_Ratkin')
            output_path: шлях для збереження
            keyword: ключове слово для тега (наприклад, 'msyl', 'political_union_outlander')
        """
        words = self._read_words_from_file(input_txt)
        if words is None:
            return None

        # Визначаємо шлях збереження
        if output_path is None:
            output_path = f"RulePack_{def_name}.xml"

        # Визначаємо ключове слово
        if keyword is None:
            # Якщо ключове слово не передано, використовуємо def_name
            keyword = def_name.lower().replace('_', '')

        # Перевіряємо, чи є pymorphy3 для слов'янських мов
        if self.lang in ['ru', 'uk']:
            # Для російської та української обов'язково використовуємо pymorphy3
            if not self.morph:
                logger.error(f"Помилка: pymorphy3 не ініціалізовано для {self.lang}")
                return None
            # НЕ використовуємо generate_xml() - обробляємо безпосередньо
        elif self.mode != 'slavic' or not self.morph:
            logger.warning(f"Для коректної роботи потрібен pymorphy3 (мова: {self.lang}, режим: {self.mode})")
            logger.info("Використовую базовий метод generate_xml")
            return self.generate_xml(input_txt, def_name, output_path)

        # Хранилище для розподілених слів
        db = self._init_word_data()

        for w in words:
            self._process_word(w, db)

        # Записуємо XML
        self._write_final_xml(db, def_name, output_path, keyword)
        self._log_word_stats(db, output_path)

        return output_path

    def _write_final_xml(self, db, def_name, output_path, keyword=None):
        """
        Записує збалансований XML у файл.

        Args:
            db: словник з наборами слів для кожної категорії
            def_name: назва дефу
            output_path: шлях для збереження
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<LanguageData>\n')

            # Визначаємо ключеве слово для тега
            if keyword is None:
                keyword = def_name.lower().replace('_', '')

            # Правила комбінування
            def_name_camel = ''.join(word.capitalize() if i > 0 else word for i, word in enumerate(def_name.split('_')))
            f.write(f'  <{def_name_camel}.rulePack.rulesStrings>\n')
            f.write(f'    <li>r_name->[{keyword}]</li>\n')
            f.write(f'  </{def_name_camel}.rulePack.rulesStrings>\n')

            # Записуємо всі слова під одним ключовим словом
            all_words = set()
            for tag in self.WORD_CATEGORIES:
                all_words.update(db.get(tag, set()))

            if all_words:
                f.write(f'\n  <{keyword} Class="Rule_StringList">\n')
                f.write(f'    <symbol>{keyword}</symbol>\n')
                f.write('    <options>\n')
                for w in sorted(all_words):
                    f.write(f'      <li>{w}</li>\n')
                f.write(f'    </options>\n  </{keyword}>\n')

            f.write('</LanguageData>\n')


# --- Приклади використання ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Morphy.py - генератор RulePackDef XML")
    parser.add_argument("--strings", help="Путь до папки Strings (наприклад, Languages/Russian/Strings)")
    parser.add_argument("--def-name", default="Namer_Test", help="Назва Def для генерації")
    parser.add_argument("--lang", default="ru", help="Код языка (ru, uk, en)")
    parser.add_argument("--batch", action="store_true", help="Обробити всі .txt файли в Strings/")
    parser.add_argument("input_files", nargs="*", help="Вхідні .txt файли (якщо не використовується --strings)")

    args = parser.parse_args()

    if args.strings:
        strings_folder = args.strings
        if not os.path.exists(strings_folder):
            logger.error(f"Папка не знайдена: {strings_folder}")
            sys.exit(1)

        logger.info("=" * 60)
        logger.info(f"Morphy.py: Post-processing Strings/ folder")
        logger.info("=" * 60)

        parser = RimWorldUniversalParser(lang=args.lang)

        if args.batch:
            # Збираємо всі .txt файли
            input_files = []
            for root, dirs, files in os.walk(strings_folder):
                for filename in files:
                    if filename.endswith(".txt"):
                        input_files.append(os.path.join(root, filename))

            if input_files:
                logger.info(f"\nЗнайдено {len(input_files)} .txt файлів:")
                for f in input_files[:5]:
                    logger.info(f"  - {os.path.basename(f)}")
                if len(input_files) > 5:
                    logger.info(f"  ... і ще {len(input_files) - 5}")

                results = parser.batch_generate(input_files, args.def_name)
                logger.info(f"\n✅ Згенеровано {len(results)} XML файлів")
            else:
                logger.info("❌ .txt файли не знайдені")
        else:
            logger.info("Використовуйте --batch для обробки всіх файлів")
    elif args.input_files:
        logger.info("=" * 60)
        logger.info("Приклад: Генерація для одного файлу")
        logger.info("=" * 60)

        parser = RimWorldUniversalParser(lang=args.lang)
        for input_file in args.input_files:
            if os.path.exists(input_file):
                result = parser.generate_xml(input_file, args.def_name)
                if result and os.path.exists(result):
                    logger.info(f"\n[FILE] Згенерований XML: {result}")
                    with open(result, encoding="utf-8") as f:
                        logger.info(f.read())
                    os.remove(result)
            else:
                logger.info(f"Файл не знайдено: {input_file}")
    else:
        # Тестові приклади (оригінальне поведінка)
        logger.info("=" * 60)
        logger.info("Приклад: Генерація для російської мови")
        logger.info("=" * 60)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("червоний\nсиній\nзелений\nжовтий\n")
            test_file = f.name

        try:
            parser = RimWorldUniversalParser(lang="ru")
            result = parser.generate_xml(test_file, "Namer_Test")

            if result and os.path.exists(result):
                logger.info("\n[FILE] Згенерований XML:")
                with open(result, encoding="utf-8") as f:
                    logger.info(f.read())
                os.remove(result)
        finally:
            os.remove(test_file)

        logger.info("\n" + "=" * 60)
        logger.info("Приклад: Генерація для англійської мови")
        logger.info("=" * 60)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("red\nblue\ngreen\nyellow\n")
            test_file = f.name

        try:
            parser = RimWorldUniversalParser(lang="en")
            result = parser.generate_xml(test_file, "Namer_Test")

            if result and os.path.exists(result):
                logger.info("\n[FILE] Згенерований XML:")
                with open(result, encoding="utf-8") as f:
                    logger.info(f.read())
                os.remove(result)
        finally:
            os.remove(test_file)

        logger.info("\n[OK] Всі приклади завершено!")
