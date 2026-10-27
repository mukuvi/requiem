"""Graveyard: JSONL store of obituaries."""

from __future__ import annotations

import json
import os
from typing import Iterable

class Graveyard:
    def __init__(self, path: str = "data/obituaries.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def bury(self, record: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def list(self, limit: int = 20) -> list[dict]:
        items = []
        if not os.path.exists(self.path):
            return items
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        return list(reversed(items[-limit:]))

    def get(self, death_id: str) -> dict | None:
        if not os.path.exists(self.path):
            return None
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("death", {}).get("id") == death_id or obj.get("id") == death_id:
                        return obj
                except Exception:
                    continue
        return None

    def count(self) -> int:
        if not os.path.exists(self.path):
            return 0
        n = 0
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n += 1
        return n
