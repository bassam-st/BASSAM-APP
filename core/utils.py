"""
وحدة الدوال المساعدة
دوال تحويل أرقام عربية، كشف نص عربي، تنظيف HTML
"""

import re
import html
from typing import Optional

# خريطة تحويل الأرقام العربية إلى إنجليزية
AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def convert_arabic_numbers(text: str) -> str:
    """تحويل الأرقام العربية إلى إنجليزية"""
    return text.translate(AR_NUM)

def is_arabic(text: str, min_arabic_chars: int = 3) -> bool:
    """كشف النص العربي"""
    if not text:
        return False
    arabic_chars = re.findall(r'[\u0600-\u06FF]', text)
    return len(arabic_chars) >= min_arabic_chars

def clean_html(text: str) -> str:
    """تنظيف النص من علامات HTML"""
    if not text:
        return ""
    # إزالة علامات HTML
    text = re.sub(r'<[^>]+>', '', text)
    # فك تشفير HTML entities
    text = html.unescape(text)
    # تنظيف المسافات الزائدة
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_text(text: str) -> str:
    """تطبيع النص العربي"""
    if not text:
        return ""
    # تحويل الأرقام العربية
    text = convert_arabic_numbers(text)
    # إزالة التشكيل
    text = re.sub(r'[\u064B-\u0652\u0670\u0640]', '', text)
    # تطبيع الهمزة
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'[ؤ]', 'و', text)
    text = re.sub(r'[ئ]', 'ي', text)
    # تنظيف المسافات
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def truncate_text(text: str, max_length: int = 200) -> str:
    """اقتطاع النص مع الحفاظ على الكلمات"""
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length]
    # البحث عن آخر مسافة لتجنب قطع الكلمات
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # إذا كانت المسافة قريبة
        truncated = truncated[:last_space]
    
    return truncated + "..."

def format_number(num: float, decimals: int = 2) -> str:
    """تنسيق الأرقام للعرض"""
    if num == int(num):
        return str(int(num))
    return f"{num:.{decimals}f}".rstrip('0').rstrip('.')

def extract_keywords(text: str, max_keywords: int = 5) -> list:
    """استخراج الكلمات المفتاحية من النص"""
    if not text:
        return []
    
    # إزالة علامات الترقيم والكلمات القصيرة
    words = re.findall(r'\w+', text.lower())
    words = [word for word in words if len(word) > 2]
    
    # إزالة الكلمات الشائعة
    stop_words = {'في', 'من', 'إلى', 'على', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي'}
    words = [word for word in words if word not in stop_words]
    
    # إرجاع أهم الكلمات
    return list(set(words))[:max_keywords]