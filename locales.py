import json
import os
from typing import Dict, Any

class Locales:
    def __init__(self):
        self.current_language = "en"
        self.translations: Dict[str, Dict[str, Any]] = {}
        self._load_all_languages()

    def _load_all_languages(self):
        """Load all language files from locales/ folder"""
        locales_dir = os.path.join(os.path.dirname(__file__), "locales")
        if not os.path.exists(locales_dir):
            return
        for lang_file in os.listdir(locales_dir):
            if lang_file.endswith(".json"):
                lang_code = lang_file.replace(".json", "")
                with open(os.path.join(locales_dir, lang_file), "r", encoding="utf-8") as f:
                    self.translations[lang_code] = json.load(f)

    def set_language(self, lang_code: str):
        """Set current language"""
        if lang_code in self.translations:
            self.current_language = lang_code

    def get(self, key: str, default: str = "", **kwargs) -> str:
        """
        Get translated string by dot-notation key
        Example: i18n.get("commands.start")
        Supports variable interpolation: i18n.get("messages.mode_switched", mode="as a friend")
        """
        keys = key.split(".")
        value = self.translations.get(self.current_language, {})

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        if not value:
            return default

        # Handle string interpolation
        if isinstance(value, str) and kwargs:
            for k, v in kwargs.items():
                value = value.replace(f"{{{{{k}}}}}", str(v))

        return value or default

# Global instance
i18n = Locales()
