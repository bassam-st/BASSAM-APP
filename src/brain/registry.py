# brain/registry.py
from typing import Callable, Dict

class SkillRegistry:
    """تجميع الأدوات/المهارات باسم -> دالة."""
    def __init__(self) -> None:
        self._skills: Dict[str, Callable[..., str]] = {}

    def register(self, name: str, func: Callable[..., str]) -> None:
        self._skills[name.lower()] = func

    def has(self, name: str) -> bool:
        return name.lower() in self._skills

    def run(self, name: str, **kwargs) -> str:
        name = name.lower()
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' غير مسجل.")
        return self._skills[name](**kwargs)

registry = SkillRegistry()

# --- مهارات افتراضية خفيفة ---
def skill_echo(text: str) -> str:
    return f"Echo: {text}"

def skill_sum(a: float, b: float) -> str:
    return f"{a} + {b} = {a + b}"

registry.register("echo", skill_echo)
registry.register("sum", skill_sum)
