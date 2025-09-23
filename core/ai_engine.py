"""
وحدة محرك الذكاء الاصطناعي
التكامل مع Gemini API لتوفير إجابات ذكية
"""

import os
import re
from typing import Optional, Dict, Any

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

from core.utils import is_arabic, normalize_text

class AIEngine:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.is_available = False
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # تجربة النماذج الحديثة المتاحة
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                except:
                    try:
                        self.model = genai.GenerativeModel('gemini-1.5-pro')
                    except:
                        try:
                            self.model = genai.GenerativeModel('gemini-pro-latest')
                        except:
                            self.model = genai.GenerativeModel('gemini-pro')
                self.is_available = True
            except Exception as e:
                print(f"خطأ في تهيئة Gemini: {e}")
                self.is_available = False
    
    def is_gemini_available(self) -> bool:
        """التحقق من توفر خدمة Gemini"""
        return self.is_available
    
    def generate_response(self, prompt: str, context: str = "") -> Optional[str]:
        """توليد رد باستخدام Gemini"""
        if not self.is_available:
            return None
        
        try:
            # تحضير النص مع السياق
            full_prompt = f"{context}\n\n{prompt}" if context else prompt
            
            # إرسال الطلب
            response = self.model.generate_content(full_prompt)
            
            if response and response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            print(f"خطأ في توليد الرد: {e}")
            return None
    
    def answer_question(self, question: str) -> Optional[Dict[str, Any]]:
        """الإجابة على الأسئلة العامة"""
        if not self.is_available:
            return None
        
        try:
            # تحضير السياق للأسئلة العربية
            if is_arabic(question):
                context = """أنت مساعد ذكي يتحدث العربية ويساعد المستخدمين العرب.
                قدم إجابات دقيقة ومفيدة ومناسبة ثقافياً.
                استخدم اللغة العربية في الرد واجعله واضحاً ومفهوماً."""
            else:
                context = """You are a helpful AI assistant.
                Provide accurate, useful, and culturally appropriate answers.
                Be clear and concise in your responses."""
            
            # توليد الرد
            response = self.generate_response(question, context)
            
            if response:
                return {
                    'success': True,
                    'question': question,
                    'answer': response,
                    'source': 'Gemini AI'
                }
            
            return None
            
        except Exception as e:
            print(f"خطأ في الإجابة على السؤال: {e}")
            return None
    
    def explain_math_solution(self, problem: str, solution: str) -> Optional[str]:
        """شرح الحلول الرياضية"""
        if not self.is_available:
            return None
        
        try:
            prompt = f"""
            اشرح بطريقة بسيطة ومفهومة كيفية حل هذه المسألة الرياضية:
            
            المسألة: {problem}
            الحل: {solution}
            
            قدم الشرح بخطوات واضحة ومرقمة باللغة العربية.
            """
            
            explanation = self.generate_response(prompt)
            return explanation
            
        except Exception as e:
            print(f"خطأ في شرح الحل الرياضي: {e}")
            return None
    
    def suggest_related_topics(self, topic: str) -> Optional[list]:
        """اقتراح مواضيع ذات صلة"""
        if not self.is_available:
            return None
        
        try:
            prompt = f"""
            اقترح 5 مواضيع مرتبطة بـ: {topic}
            
            قدم الاقتراحات في شكل قائمة مرقمة باللغة العربية.
            ركز على المواضيع المفيدة والتعليمية.
            """
            
            response = self.generate_response(prompt)
            
            if response:
                # استخراج القائمة من الرد
                lines = response.split('\n')
                suggestions = []
                
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # إزالة الرقم والرموز
                        clean_line = re.sub(r'^[\d\-\.\)\s]+', '', line).strip()
                        if clean_line:
                            suggestions.append(clean_line)
                
                return suggestions[:5]  # أقصى 5 اقتراحات
            
            return None
            
        except Exception as e:
            print(f"خطأ في اقتراح المواضيع: {e}")
            return None
    
    def translate_to_arabic(self, text: str) -> Optional[str]:
        """ترجمة النص إلى العربية"""
        if not self.is_available or is_arabic(text):
            return None
        
        try:
            prompt = f"""
            ترجم النص التالي إلى اللغة العربية بطريقة دقيقة ومفهومة:
            
            {text}
            
            قدم الترجمة فقط بدون تفسيرات إضافية.
            """
            
            translation = self.generate_response(prompt)
            return translation
            
        except Exception as e:
            print(f"خطأ في الترجمة: {e}")
            return None
    
    def smart_search_enhancement(self, query: str, search_results: list) -> Optional[str]:
        """تحسين نتائج البحث بالذكاء الاصطناعي"""
        if not self.is_available or not search_results:
            return None
        
        try:
            # تحضير ملخص النتائج
            results_summary = "\n".join([
                f"- {result.get('title', '')}: {result.get('snippet', '')[:100]}..."
                for result in search_results[:3]
            ])
            
            prompt = f"""
            بناءً على نتائج البحث التالية عن "{query}":
            
            {results_summary}
            
            قدم ملخصاً شاملاً ومفيداً باللغة العربية يجيب على استفسار المستخدم.
            اجعل الملخص منظماً ومفهوماً ويتضمن أهم المعلومات.
            """
            
            enhanced_summary = self.generate_response(prompt)
            return enhanced_summary
            
        except Exception as e:
            print(f"خطأ في تحسين البحث: {e}")
            return None

# إنشاء مثيل عام
ai_engine = AIEngine()