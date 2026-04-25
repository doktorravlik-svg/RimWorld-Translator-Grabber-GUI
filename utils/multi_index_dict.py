"""
MultiIndexDict - словарь с множественными индексами для поиска модов.

Поддерживает:
- Поиск по name, packageId, пути (case-insensitive)
- Fuzzy search (расстояние Левенштейна)
- Частичное совпадение
- Синонимы (например "CE" -> "Combat Extended")
"""

from typing import Optional


class MultiIndexDict:
    """
    Словарь с множественными индексами для быстрого поиска модов.
    
    Индексы:
    - По имени (case-insensitive)
    - По packageId (case-insensitive)
    - По пути
    - По синонимам
    """

    def __init__(self):
        self._data: dict[str, dict] = {}  # packageId -> {name, path, ...}
        self._name_index: dict[str, str] = {}  # name_lower -> packageId
        self._package_index: dict[str, str] = {}  # packageId_lower -> packageId
        self._path_index: dict[str, str] = {}  # path_lower -> packageId
        self._synonym_index: dict[str, str] = {}  # synonym -> packageId
        
        # Инициализация синонимов
        self._load_default_synonyms()

    def _load_default_synonyms(self) -> None:
        """Загружает синонимы по умолчанию."""
        self._synonyms: dict[str, str] = {
            "ce": "Combat Extended",
            "combat extended": "Combat Extended",
            "vanilla expanded": "Vanilla Expanded Framework",
            "vef": "Vanilla Expanded Framework",
            "har": "Harmony",
            "harmony": "Harmony",
            "rjw": "RimJobWorld",
            "rimjobworld": "RimJobWorld",
            "hugslib": "HugsLib",
            "hl": "HugsLib",
            "epoe": "Expanded Prosthetics and Organ Engineering",
            "epoef": "Expanded Prosthetics and Organ Engineering - Forked",
            "rbse": "RBSE",
            "realistic body size": "RBSE",
        }

    def add(
        self,
        package_id: str,
        name: str = "",
        path: str = "",
        **kwargs
    ) -> None:
        """
        Добавляет мод в индекс.

        Args:
            package_id: Уникальный ID мода
            name: Отображаемое имя
            path: Путь к моду
            **kwargs: Дополнительные метаданные
        """
        self._data[package_id] = {
            "package_id": package_id,
            "name": name,
            "path": path,
            **kwargs
        }

        # Обновляем индексы
        if name:
            self._name_index[name.lower()] = package_id
        
        self._package_index[package_id.lower()] = package_id
        
        if path:
            self._path_index[path.lower()] = package_id

    def get(self, key: str) -> Optional[dict]:
        """
        Ищет мод по ключу (name, packageId или path).

        Args:
            key: Ключ для поиска

        Returns:
            Данные мода или None
        """
        if not key:
            return None

        key_lower = key.lower()

        # 1. Точное совпадение по packageId
        if key_lower in self._package_index:
            return self._data[self._package_index[key_lower]]

        # 2. Точное совпадение по имени
        if key_lower in self._name_index:
            return self._data[self._name_index[key_lower]]

        # 3. Точное совпадение по пути
        if key_lower in self._path_index:
            return self._data[self._path_index[key_lower]]

        # 4. Поиск по синонимам
        if key_lower in self._synonym_index:
            return self._data[self._synonym_index[key_lower]]

        # Проверяем синонимы
        if key_lower in self._synonyms:
            resolved = self._synonyms[key_lower]
            return self.get(resolved)

        return None

    def fuzzy_search(
        self,
        query: str,
        max_distance: int = 3,
        max_results: int = 5
    ) -> list[dict]:
        """
        Нечёткий поиск по расстоянию Левенштейна.

        Args:
            query: Строка поиска
            max_distance: Максимальное расстояние
            max_results: Максимальное количество результатов

        Returns:
            Список найденных модов
        """
        if not query:
            return []

        query_lower = query.lower()
        results: list[tuple[int, dict]] = []

        # Собираем все возможные ключи для поиска
        all_keys = set()
        all_keys.update(self._name_index.keys())
        all_keys.update(self._package_index.keys())
        all_keys.update(self._path_index.keys())

        for key in all_keys:
            distance = self._levenshtein_distance(query_lower, key)
            
            if distance <= max_distance:
                package_id = (
                    self._name_index.get(key) or
                    self._package_index.get(key) or
                    self._path_index.get(key)
                )
                if package_id and package_id in self._data:
                    results.append((distance, self._data[package_id]))

        # Сортируем по расстоянию и возвращаем топ-N
        results.sort(key=lambda x: x[0])
        return [item[1] for item in results[:max_results]]

    def partial_match(
        self,
        query: str,
        max_results: int = 10
    ) -> list[dict]:
        """
        Поиск по частичному совпадению.

        Args:
            query: Строка поиска
            max_results: Максимальное количество результатов

        Returns:
            Список найденных модов
        """
        if not query:
            return []

        query_lower = query.lower()
        results: list[tuple[int, dict]] = []

        all_keys = set()
        all_keys.update(self._name_index.keys())
        all_keys.update(self._package_index.keys())

        for key in all_keys:
            if query_lower in key:
                package_id = (
                    self._name_index.get(key) or
                    self._package_index.get(key)
                )
                if package_id and package_id in self._data:
                    # Позиция совпадения - чем раньше, тем лучше
                    position = key.index(query_lower)
                    results.append((position, self._data[package_id]))

        # Сортируем по позиции совпадения
        results.sort(key=lambda x: x[0])
        return [item[1] for item in results[:max_results]]

    def get_by_path(self, path: str) -> Optional[dict]:
        """
        Ищет мод по пути.

        Args:
            path: Путь к моду

        Returns:
            Данные мода или None
        """
        if not path:
            return None

        path_lower = path.lower()
        
        # Точное совпадение
        if path_lower in self._path_index:
            return self._data[self._path_index[path_lower]]
        
        # Частичное совпадение
        for stored_path, package_id in self._path_index.items():
            if stored_path in path_lower or path_lower in stored_path:
                return self._data[package_id]

        return None

    def add_synonym(self, synonym: str, package_id: str) -> None:
        """
        Добавляет синоним для мода.

        Args:
            synonym: Синоним
            package_id: ID мода
        """
        self._synonyms[synonym.lower()] = package_id
        self._synonym_index[synonym.lower()] = package_id

    def get_all(self) -> dict[str, dict]:
        """Возвращает все данные."""
        return self._data.copy()

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """
        Вычисляет расстояние Левенштейна между двумя строками.

        Args:
            s1: Первая строка
            s2: Вторая строка

        Returns:
            Расстояние Левенштейна
        """
        if len(s1) < len(s2):
            return MultiIndexDict._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # insertions, deletions, substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


def build_mods_database(
    mods_folders: list[str],
    logger=None
) -> MultiIndexDict:
    """
    Строит базу данных всех модов из указанных папок.

    Args:
        mods_folders: Список папок с модами
        logger: Логгер (опционально)

    Returns:
        MultiIndexDict со всеми модами
    """
    import os
    from scanner.mod_scanner import find_about_xml, parse_about_xml

    db = MultiIndexDict()

    for folder in mods_folders:
        if not os.path.exists(folder):
            continue

        for item in os.listdir(folder):
            mod_path = os.path.join(folder, item)
            if not os.path.isdir(mod_path):
                continue

            about_path = find_about_xml(mod_path)
            if not about_path:
                continue

            about_data = parse_about_xml(about_path)
            
            package_id = about_data.get("mod_id", "")
            name = about_data.get("name", "")
            
            if package_id:
                db.add(
                    package_id=package_id,
                    name=name,
                    path=mod_path,
                    **{k: v for k, v in about_data.items() 
                       if k not in ("mod_id", "name", "mod_path")}
                )

    if logger:
        logger.info(f"База данных модов: {len(db)} модов")

    return db
