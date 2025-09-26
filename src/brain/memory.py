# brain/memory.py
from typing import List, Tuple

class Memory:
    """ذاكرة خفيفة داخل الذاكرة (بدون ملفات)."""
    def __init__(self) -> None:
        self._items: List[Tuple[str, str]] = []  # (role, text)

    def add(self, role: str, text: str) -> None:
        self._items.append((role, text))
        if len(self._items) > 200:
            self._items.pop(0)

    def last(self, n: int = 5) -> List[Tuple[str, str]]:
        return self._items[-n:]

memory = Memory()
