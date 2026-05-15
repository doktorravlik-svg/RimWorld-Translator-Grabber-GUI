# gui/styling/theme_manager.py
"""
Управление темами ttkbootstrap для RimWorld Translator Grabber.
"""

# Маппинг тем ttkbootstrap (обновлено для v1.20.2)
TTKBOOTSTRAP_THEMES = {
    # Существующие темы
    "light": "cosmo",
    "dark": "darkly",
    "ocean": "minty",
    "forest": "united",
    # Новые темы (добавлены в 2026)
    "solar": "solar",
    "vapor": "vapor",
    "cyborg": "cyborg",
    "superhero": "superhero",
}

# Описания тем для отображения в меню
THEME_DESCRIPTIONS = {
    "light": "☀️ Светлая (Cosmo)",
    "dark": "🌙 Тёмная (Darkly)",
    "ocean": "🌊 Океан (Minty)",
    "forest": "🌲 Лес (United)",
    "solar": "🔆 Солнечная (Solar)",
    "vapor": "💨 Пар (Vapor)",
    "cyborg": "🤖 Киборг (Cyborg)",
    "superhero": "🦸 Супергерой (Superhero)",
}


def get_theme_names() -> list[str]:
    """
    Возвращает список всех доступных имён тем.

    Returns:
        Список имён тем
    """
    return list(THEME_DESCRIPTIONS.keys())


def get_theme_name_display(theme_key: str) -> str:
    """
    Возвращает отображаемое имя темы.

    Args:
        theme_key: Ключ темы

    Returns:
        Отображаемое имя или ключ если не найдено
    """
    return THEME_DESCRIPTIONS.get(theme_key, theme_key)


def apply_theme(style, theme_name: str):
    """
    Применить тему ttkbootstrap.

    Args:
        style: ttkbootstrap Style
        theme_name: Имя темы из конфига (light, dark, ocean, forest)
    """
    bs_theme = TTKBOOTSTRAP_THEMES.get(theme_name, "cosmo")
    style.theme_use(bs_theme)


def change_theme(config, style, theme_name: str, log_callback=None):
    """
    Сменить тему оформления.

    Args:
        config: Словарь конфигурации
        style: ttkbootstrap Style
        theme_name: Новое имя темы
        log_callback: Функция для логирования
    """
    config["theme"] = theme_name
    apply_theme(style, theme_name)
    if log_callback:
        log_callback(f"Тема изменена на: {theme_name}")
