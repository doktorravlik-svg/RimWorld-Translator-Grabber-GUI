import os
import re

# ✅ ИСПРАВЛЕНО: Динамическое определение корня проекта
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE_PATH = os.path.join(BASE, "gui", "styling", "icon_manager.py")

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Определяем старый метод get()
old_get = '''    def get(
        self,
        name: str,
        size: int = 16,
        color: str = None,
        color_key: str = None,
        style: str = None,
    ):
        """
        Получить иконку (создается отложенно при первом вызове в GUI контексте).

        Args:
            name: Имя иконки (Bootstrap Icons)
            size: Размер в пикселях
            color: Явный цвет (hex) — переопределяет color_key
            color_key: Ключ цвета из схемы темы
            style: Стиль (пока не используется)

        Returns:
            BootstrapIcon объект или None
        """
        if not HAS_ICONS:
            return None

        # Определяем цвет
        if color is None and color_key:
            color = self.colors.get(color_key, self.colors["menu_icon"])

        cache_key = (name, size, color, style)
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = BootstrapIcon(name=name, size=size, color=color)
            except RuntimeError:
                # tkinter root не инициализирован — вернем None
                # Иконка будет создана при следующем вызове
                return None
            except Exception:
                return None
        return self._cache[cache_key]'''

# Определяем новые методы
new_methods = '''    def get(
        self,
        name: str,
        size: int = 16,
        color: str = None,
        color_key: str = None,
        style: str = None,
        fallback_text: str = None,
    ):
        """
        Получить иконку (создается отложенно при первом вызове в GUI контексте).

        Args:
            name: Имя иконки (Bootstrap Icons)
            size: Размер в пикселях
            color: Явный цвет (hex) — переопределяет color_key
            color_key: Ключ цвета из схемы темы
            style: Стиль (пока не используется)
            fallback_text: Текст для отображения если иконка не найдена (например, эмодзи)

        Returns:
            BootstrapIcon объект или fallback_text
        """
        if not HAS_ICONS:
            return fallback_text

        # Определяем цвет
        if color is None and color_key:
            color = self.colors.get(color_key, self.colors["menu_icon"])

        cache_key = (name, size, color, style)
        if cache_key not in self._cache:
            try:
                self._cache[cache_key] = BootstrapIcon(name=name, size=size, color=color)
            except RuntimeError:
                # tkinter root не инициализирован — вернем fallback_text
                return fallback_text
            except Exception:
                print(f"⚠️ Ошибка загрузки иконки '{name}': используем fallback '{fallback_text}'")
                return fallback_text
        return self._cache[cache_key]

    def get_with_states(
        self,
        name: str,
        size: int = 16,
        color: str = None,
        hover_color: str = None,
        pressed_color: str = None,
        disabled_color: str = None,
        fallback_text: str = None,
    ):
        """
        Получить иконку с состояниями (Stateful Icons v3.1+).
        Автоматически меняет цвет при hover/pressed/disabled.

        Args:
            name: Имя иконки
            size: Размер
            color: Базовый цвет
            hover_color: Цвет при наведении
            pressed_color: Цвет при нажатии
            disabled_color: Цвет при отключении
            fallback_text: Fallback текст

        Returns:
            BootstrapIcon объект или fallback_text
        """
        icon = self.get(name, size, color, fallback_text=fallback_text)
        if icon is None or isinstance(icon, str):
            return icon
            
        # Сохраняем конфигурацию состояний для применения к виджету
        states = {}
        if hover_color:
            states["hover"] = {"color": hover_color}
        if pressed_color:
            states["pressed"] = {"color": pressed_color}
        if disabled_color:
            states["disabled"] = {"color": disabled_color}
            
        if states:
            icon._state_config = states
                
        return icon'''

if old_get in content:
    content = content.replace(old_get, new_methods)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ icon_manager.py обновлён (Fallback + Stateful Icons)")
else:
    print("❌ Не удалось найти старый метод get(). Проверьте файл.")
