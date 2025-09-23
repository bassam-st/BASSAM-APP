"""
محرك الذكاء الاصطناعي المحدث - بسام الذكي
يدمج النماذج المتعددة مع الخريطة المعمارية المجانية
"""

import os
import time
import asyncio
from typing import Optional, Dict, Any, List

try:
    from core.multi_llm_engine import multi_llm_engine
    from core.free_architecture import free_architecture
    from core.advanced_intelligence import AdvancedIntelligence
    from core.utils import is_arabic, normalize_text
    print("✅ تم تحميل جميع وحدات الذكاء الاصطناعي المحدثة")
except ImportError as e:
    print(f"❌ خطأ في استيراد وحدات الذكاء الاصطناعي: {e}")

class EnhancedAIEngine:
    """محرك الذكاء الاصطناعي المحدث مع النماذج المتعددة"""
    
    def __init__(self):
        self.intelligence = AdvancedIntelligence()
        self.multi_llm = multi_llm_engine
        self.architecture = free_architecture
        print("🤖 تم تهيئة محرك الذكاء الاصطناعي المحدث")
        
        # إحصائيات الاستخدام
        self.session_stats = {
            'questions_answered': 0,
            'models_used': set(),
            'total_tokens': 0,
            'cache_hits': 0
        }
    
    def is_available(self) -> bool:
        """التحقق من توفر أي نموذج"""
        available_models = self.multi_llm.get_available_models()
        return len(available_models) > 0
    
    async def answer_question(self, question: str, context: str = "") -> Optional[Dict[str, Any]]:
        """الإجابة الذكية على الأسئلة باستخدام أفضل نموذج متاح"""
        if not question.strip():
            return None
        
        try:
            # فحص الذاكرة المؤقتة أولاً
            cached_response = self.architecture.get_cached_response(question)
            if cached_response:
                self.session_stats['cache_hits'] += 1
                cached_response['from_cache'] = True
                return cached_response
            
            # تحليل السؤال بالذكاء المتقدم
            analysis = self.intelligence.analyze_question(question)
            
            # بناء سياق محسن
            enhanced_context = self._build_enhanced_context(question, analysis, context)
            
            start_time = time.time()
            
            # توليد الرد باستخدام النماذج المتعددة
            response = await self.multi_llm.generate_response(
                enhanced_context,
                context=f"تحليل: {analysis.get('question_type', 'عام')}",
                max_tokens=1000
            )
            
            response_time = time.time() - start_time
            
            if response['success']:
                # تحسين الرد بالذكاء المتقدم
                enhanced_response = self.intelligence.enhance_response(
                    response['response'], analysis, question
                )
                
                result = {
                    'success': True,
                    'answer': enhanced_response,
                    'question_type': analysis.get('question_type', 'general'),
                    'emotional_tone': analysis.get('emotional_context', {}),
                    'enhanced': True,
                    'from_cache': False,
                    'model_used': response['model'],
                    'provider': response['provider'],
                    'tokens_used': response.get('tokens_used', 0),
                    'response_time': response_time
                }
                
                # تحديث الإحصائيات
                self.session_stats['questions_answered'] += 1
                self.session_stats['models_used'].add(response['model'])
                self.session_stats['total_tokens'] += response.get('tokens_used', 0)
                
                # تسجيل الاستخدام
                self.architecture.record_usage(
                    service=response['provider'],
                    operation='question_answer',
                    tokens_used=response.get('tokens_used', 0),
                    response_time=response_time,
                    success=True
                )
                
                # تخزين في الذاكرة المؤقتة
                self.architecture.cache_response(question, result, response['model'])
                
                return result
            else:
                # فشل في الحصول على رد
                return {
                    'success': False,
                    'answer': "عذراً، لا أستطيع الإجابة على هذا السؤال حالياً. يرجى المحاولة لاحقاً.",
                    'error': 'no_models_available'
                }
            
        except Exception as e:
            print(f"❌ خطأ في الإجابة على السؤال: {e}")
            
            # تسجيل الخطأ
            self.architecture.record_usage(
                service='enhanced_ai',
                operation='question_answer_error',
                response_time=time.time() - start_time if 'start_time' in locals() else 0,
                success=False
            )
            
            return {
                'success': False,
                'answer': "حدث خطأ أثناء معالجة السؤال. يرجى المحاولة مرة أخرى.",
                'error': str(e)
            }
    
    def _build_enhanced_context(self, question: str, analysis: Dict[str, Any], context: str = "") -> str:
        """بناء سياق محسن للسؤال"""
        
        # السياق الأساسي
        enhanced_context = f"""أنت بسام الذكي، مساعد ذكي متخصص في اللغة العربية.

تحليل السؤال:
- النوع: {analysis.get('question_type', 'عام')}
- المشاعر: {analysis.get('emotional_context', {}).get('primary_emotion', 'محايد')}
- اللغة: {'عربي' if is_arabic(question) else 'إنجليزي'}

تعليمات الإجابة:
1. اجب باللغة العربية الفصحى الجميلة
2. كن مفيداً ومفصلاً ودقيقاً
3. استخدم أمثلة عملية عند الحاجة
4. اختتم بسؤال متابعة مناسب

"""
        
        # إضافة السياق الإضافي إن وجد
        if context:
            enhanced_context += f"السياق الإضافي: {context}\n\n"
        
        # إضافة السؤال
        enhanced_context += f"السؤال: {question}\n\nالإجابة:"
        
        return enhanced_context
    
    async def smart_search_enhancement(self, query: str, search_results: List[Dict]) -> Optional[str]:
        """تحسين نتائج البحث بالذكاء الاصطناعي"""
        if not search_results:
            return None
        
        try:
            # تجميع المحتوى من النتائج
            content_summary = []
            for result in search_results[:3]:  # أخذ أول 3 نتائج فقط
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                content_summary.append(f"• {title}: {snippet}")
            
            combined_content = "\n".join(content_summary)
            
            # بناء prompt للتلخيص
            enhancement_prompt = f"""بناءً على نتائج البحث التالية، قدم ملخصاً شاملاً ومفيداً عن "{query}":

{combined_content}

اكتب ملخصاً مفصلاً ومنظماً باللغة العربية، مع التركيز على أهم المعلومات والنقاط الرئيسية."""
            
            # استخدام النماذج المتعددة للتحسين
            response = await self.multi_llm.generate_response(
                enhancement_prompt,
                max_tokens=800
            )
            
            if response['success']:
                # تسجيل الاستخدام
                self.architecture.record_usage(
                    service=response['provider'],
                    operation='search_enhancement',
                    tokens_used=response.get('tokens_used', 0),
                    success=True
                )
                
                return response['response']
            
            return None
            
        except Exception as e:
            print(f"❌ خطأ في تحسين البحث: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """الحصول على حالة النظام الشاملة"""
        
        # إحصائيات النماذج
        model_stats = self.multi_llm.get_model_stats()
        
        # صحة النظام
        system_health = self.architecture.get_system_health()
        
        # إحصائيات الجلسة
        session_models = list(self.session_stats['models_used'])
        
        return {
            'models': {
                'available': model_stats['total_models'],
                'free_models': model_stats['free_models'],
                'local_models': model_stats['local_models'],
                'best_model': model_stats['best_model'],
                'session_models_used': session_models
            },
            'session': self.session_stats,
            'architecture': {
                'cache_size_mb': system_health['cache']['size_mb'],
                'cache_items': system_health['cache']['items'],
                'db_size_mb': system_health['database']['size_mb']
            },
            'usage_limits': system_health['usage'],
            'system_healthy': model_stats['total_models'] > 0
        }
    
    def optimize_system(self) -> Dict[str, Any]:
        """تحسين النظام والذاكرة"""
        return self.architecture.optimize_for_free_hosting()

# إنشاء المثيل العام المحدث
enhanced_ai_engine = EnhancedAIEngine()