"""
وحدة بسام الذكي الأساسية
تحتوي على جميع محركات التطبيق الرئيسية
"""

from .utils import (
    convert_arabic_numbers,
    is_arabic,
    clean_html,
    normalize_text,
    truncate_text,
    format_number,
    extract_keywords
)

from .search import search_engine
from .math_engine import math_engine
from .ai_engine import ai_engine

__version__ = "1.0.0"
__author__ = "Bassam Smart App"
__all__ = [
    "search_engine",
    "math_engine", 
    "ai_engine",
    "convert_arabic_numbers",
    "is_arabic",
    "clean_html",
    "normalize_text",
    "truncate_text",
    "format_number",
    "extract_keywords"
]