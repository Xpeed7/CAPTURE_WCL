"""展示层中文翻译。

优先按 WCL/游戏 ID 翻译，找不到时保留英文，并记录到 output/missing_translations.json。
"""

from __future__ import annotations

import json
import os
from typing import Dict, Optional

from config import OUTPUT_DIR


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSLATION_DIR = os.path.join(BASE_DIR, "translations")


class TranslationStore:
    def __init__(self) -> None:
        self.abilities = self._load("abilities.json")
        self.actors = self._load("actors.json")
        self.buffs = self._load("buffs.json")
        self.items = self._load("items.json")
        self.enchants = self._load("enchants.json")
        self.missing: Dict[str, Dict[str, str]] = {
            "abilities": {},
            "actors": {},
            "buffs": {},
            "items": {},
            "enchants": {},
        }

    def translate_ability(self, ability_id: int = 0, name: str = "") -> str:
        return self._translate("abilities", self.abilities, ability_id, name)

    def translate_actor(self, name: str = "") -> str:
        if not name:
            return ""
        translated = self.actors.get(name)
        if translated:
            return translated
        return name

    def translate_buff(self, buff_id: int = 0, name: str = "") -> str:
        return self._translate("buffs", self.buffs, buff_id, name)

    def translate_item(self, item_id: int = 0, name: str = "") -> str:
        return self._translate("items", self.items, item_id, name)

    def translate_enchant(self, name: str = "") -> str:
        return self._translate("enchants", self.enchants, 0, name)

    def save_missing(self, filename: str = "missing_translations.json") -> str:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.missing, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
        return filepath

    def _translate(
        self,
        category: str,
        mapping: Dict[str, str],
        object_id: int = 0,
        name: str = "",
    ) -> str:
        key = str(object_id) if object_id else ""
        if key and mapping.get(key):
            return mapping[key]
        if name and mapping.get(name):
            return mapping[name]
        if name:
            self._remember_missing(category, key or name, name)
            return name
        return ""

    def _remember_missing(self, category: str, key: str, value: str) -> None:
        if not key or not value:
            return
        if value == "-":
            return
        self.missing.setdefault(category, {})[key] = value

    @staticmethod
    def _load(filename: str) -> Dict[str, str]:
        path = os.path.join(TRANSLATION_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in data.items()}


translator = TranslationStore()


def save_missing_translations() -> str:
    return translator.save_missing()
