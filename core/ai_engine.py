"""
وحدة محرك الذكاء الاصطناعي
التكامل مع Gemini API لتوفير إجابات ذكية
"""

import os
import re
from typing import Optional, Dict, Any, List

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

from core.utils import is_arabic, normalize_text
from core.advanced_intelligence import AdvancedIntelligence

class AIEngine:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.is_available = False
        self.intelligence = AdvancedIntelligence()  # إضافة الذكاء المتقدم
        
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
        """الإجابة على الأسئلة العامة مع الذكاء المتقدم"""
        if not self.is_available:
            return None
        
        try:
            # كشف نوع السؤال والمشاعر
            question_type = self.intelligence.detect_question_type(question)
            emotion, confidence = self.intelligence.detect_emotion(question)
            
            # إنشاء سياق محسن
            enhanced_context = self.intelligence.create_enhanced_context(question, question_type, emotion)
            
            # إنشاء رد عاطفي
            emotional_intro = self.intelligence.generate_emotional_response(emotion, confidence)
            
            # تحضير السؤال مع المقدمة العاطفية
            if emotional_intro:
                full_question = f"{emotional_intro}\n\n{question}"
            else:
                full_question = question
            
            # تحضير النص النهائي
            prompt = f"""
نوع السؤال: {question_type}
السؤال: {full_question}

أجب بشكل مفصل وذكي ومفيد. اجعل إجابتك شاملة وغنية بالمعلومات مع أمثلة وتوضيحات.
"""
            
            # توليد الرد
            response = self.generate_response(prompt, enhanced_context)
            
            if response:
                # تحسين النص العربي
                enhanced_response = self.intelligence.enhance_arabic_text(response)
                
                # إضافة أسئلة متابعة
                follow_up_questions = self.intelligence.generate_follow_up_questions(
                    question, question_type
                )
                
                return {
                    'success': True,
                    'question': question,
                    'answer': enhanced_response,
                    'question_type': question_type,
                    'emotion_detected': emotion,
                    'confidence': confidence,
                    'follow_up_questions': follow_up_questions,
                    'source': 'بسام الذكي - Gemini AI المتقدم'
                }
            
            return None
            
        except Exception as e:
            print(f"خطأ في الإجابة على السؤال: {e}")
            return None
    
    def explain_math_solution(self, problem: str, solution: str, detailed_steps: Optional[List[str]] = None) -> Optional[str]:
        """شرح الحلول الرياضية مع تفاصيل متقدمة"""
        if not self.is_available:
            return None
        
        try:
            # إنشاء سياق متقدم للرياضيات
            advanced_context = self.intelligence.create_enhanced_context(problem, 'mathematical', 'help_request')
            
            # تحضير النص مع الخطوات المفصلة
            if detailed_steps:
                steps_text = "\n".join([f"- {step}" for step in detailed_steps])
                prompt = f"""
🧮 **شرح مسألة رياضية متقدم**

📋 **المسألة:** {problem}
✅ **الحل:** {solution}

🔧 **الخطوات المفصلة:**
{steps_text}

📚 **مطلوب منك:**
1. اشرح كل خطوة بطريقة تعليمية واضحة
2. اذكر القواعد الرياضية المستخدمة 
3. قدم نصائح وتحذيرات مهمة
4. اقترح طرق للتحقق من الحل
5. أعط أمثلة مشابهة للتدريب

استخدم اللغة العربية الواضحة مع الرموز الرياضية المناسبة.
                """
            else:
                prompt = f"""
اشرح بطريقة تعليمية متقدمة كيفية حل هذه المسألة الرياضية:

المسألة: {problem}
الحل: {solution}

قدم شرحاً شاملاً يتضمن:
- الخطوات مرقمة وواضحة
- القواعد الرياضية المستخدمة
- نصائح للتذكر والتطبيق
- طرق التحقق من صحة الحل
                """
            
            explanation = self.generate_response(prompt, advanced_context)
            
            if explanation:
                return self.intelligence.enhance_arabic_text(explanation)
            
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