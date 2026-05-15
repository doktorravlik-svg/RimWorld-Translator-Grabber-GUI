# translation/engines/argos_engine.py
"""
Движок Argos Translate.

Полностью оффлайн-переводчик на базе OpenNMT.
Не требует интернета, работает на вашем процессоре.
"""

try:
    import argostranslate
    import argostranslate.package
    import argostranslate.translate

    _ARGOS_AVAILABLE = True
except ImportError:
    _ARGOS_AVAILABLE = False
except Exception:
    _ARGOS_AVAILABLE = False

from translation.engines.base import TranslationEngine


class ArgosEngine(TranslationEngine):
    """
    Оффлайн-движок Argos Translate.

    При первом использовании скачивает языковые пакеты.
    """

    def __init__(
        self,
        source_lang: str = "en",
        target_lang: str = "ru",
        proxy: dict | None = None,
        auto_install_packages: bool = True,
    ):
        # Argos не поддерживает auto, нужен конкретный язык
        super().__init__(source_lang, target_lang, proxy)
        self._installed_translation = None
        self.auto_install = auto_install_packages

        if _ARGOS_AVAILABLE:
            try:
                self._ensure_package_installed()
                self._initialized = self._installed_translation is not None
            except Exception:
                self._initialized = False

    def _ensure_package_installed(self):
        """Убеждается, что нужный пакет установлен."""
        if not _ARGOS_AVAILABLE:
            return

        try:
            import argostranslate.package
            import argostranslate.translate
            
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            for pkg in available_packages:
                if pkg.from_code == self.source_lang and pkg.to_code == self.target_lang:
                    installed_codes = [
                        p.from_code for p in argostranslate.package.get_installed_packages()
                    ]
                    if self.source_lang not in installed_codes:
                        if self.auto_install:
                            argostranslate.package.install_from_path(pkg.download())
                        else:
                            return

                    self._installed_translation = argostranslate.translate.get_translation_from_codes(
                        self.source_lang, self.target_lang
                    )
                    break
        except Exception:
            pass

    def translate(self, text: str) -> str | None:
        if not self._initialized or not self._installed_translation:
            self.increment_error_count()
            return None

        try:
            result = self._installed_translation.translate(text)
            self.reset_error_count()
            return result
        except Exception:
            self.increment_error_count()
            return None
