# IMPORTANT: KEEP THIS COMMENT
# Follow these instructions when using this blueprint:
# - Note that the newest Gemini model series is "gemini-2.5-flash" or gemini-2.5-pro"
#   - do not change this unless explicitly requested by the user
# Blueprint for using Gemini (a multimodal LLM service offered by Google) with Python.

import json
import logging
import os
from typing import Optional

# استخدام os.environ للتحقق من توفر المكتبة
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("تحذير: مكتبة Gemini غير متوفرة - سيتم تعطيل ميزة الذكاء الاصطناعي")

# -------- نظام الذكاء الاصطناعي الهجين --------
class HybridAI:
    def __init__(self):
        self.gemini_client = None
        if GEMINI_AVAILABLE and os.environ.get("GEMINI_API_KEY"):
            try:
                self.gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
                print("✅ تم تفعيل Gemini AI")
            except Exception as e:
                print(f"⚠️ فشل في تهيئة Gemini: {e}")

    def is_available(self) -> bool:
        """التحقق من توفر الذكاء الاصطناعي"""
        return self.gemini_client is not None

    def answer_question(self, question: str, context: str = None) -> Optional[str]:
        """الإجابة على سؤال باستخدام Gemini AI"""
        if not self.is_available():
            return None
            
        try:
            # إعداد الرسالة مع السياق
            prompt = f"""أجب على السؤال التالي باللغة العربية بإجابة مفيدة ومختصرة:

السؤال: {question}

{f"السياق: {context}" if context else ""}

يرجى الإجابة بشكل واضح ومفيد في 2-3 جمل فقط."""

            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text if response.text else None
            
        except Exception as e:
            print(f"خطأ في الذكاء الاصطناعي: {e}")
            return None

    def summarize_arabic_text(self, text: str) -> Optional[str]:
        """تلخيص النص العربي"""
        if not self.is_available():
            return None
            
        try:
            prompt = f"""لخص النص التالي باللغة العربية في نقاط رئيسية مختصرة:

{text[:2000]}  

اكتب الملخص في 3-4 نقاط رئيسية فقط."""

            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            return response.text if response.text else None
            
        except Exception as e:
            print(f"خطأ في التلخيص: {e}")
            return None

    def is_programming_question(self, question: str) -> bool:
        """التحقق من كون السؤال متعلق بالبرمجة"""
        programming_keywords = [
            'بايثون', 'python', 'javascript', 'js', 'html', 'css', 'php', 'java',
            'c++', 'c#', 'كود', 'برمجة', 'تطوير', 'algorithm', 'function', 'class',
            'variable', 'framework', 'library', 'api', 'database', 'sql',
            'react', 'vue', 'angular', 'django', 'flask', 'node', 'npm'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in programming_keywords)

    def is_networking_question(self, question: str) -> bool:
        """التحقق من كون السؤال متعلق بالشبكات"""
        networking_keywords = [
            'شبكة', 'network', 'internet', 'tcp', 'ip', 'http', 'https', 'dns',
            'router', 'wifi', 'lan', 'wan', 'vpn', 'firewall', 'protocol',
            'port', 'server', 'client', 'bandwidth', 'latency', 'cisco',
            'juniper', 'mikrotik', 'switch', 'hub'
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in networking_keywords)

# إنشاء مثيل من الذكاء الاصطناعي الهجين
hybrid_ai = HybridAI()