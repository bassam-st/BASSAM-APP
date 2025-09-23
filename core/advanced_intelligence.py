"""
وحدة الذكاء المتقدم لبسام
تحتوي على الذكاء اللغوي والعاطفي والتلخيص المتقدم
"""

import re
import random
from typing import Dict, List, Optional, Any, Tuple
from core.utils import is_arabic, normalize_text

class AdvancedIntelligence:
    """محرك الذكاء المتقدم للبحث والتلخيص والذكاء العاطفي"""
    
    def __init__(self):
        self.emotion_patterns = self._load_emotion_patterns()
        self.question_patterns = self._load_question_patterns()
        self.context_templates = self._load_context_templates()
        
    def _load_emotion_patterns(self) -> Dict[str, List[str]]:
        """تحميل أنماط المشاعر"""
        return {
            'positive': [
                'شكرا', 'ممتاز', 'رائع', 'جميل', 'أحبك', 'سعيد', 'فرح', 'حلو', 'عظيم', 
                'رائع', 'ممتع', 'مفيد', 'نجح', 'نجاح', 'فاز', 'فوز', 'أفضل'
            ],
            'negative': [
                'زعلان', 'حزين', 'صعب', 'مشكلة', 'خطأ', 'غلط', 'فشل', 'سيء', 
                'صعوبة', 'تعب', 'متعب', 'مشاكل', 'خايف', 'قلقان', 'مقلق'
            ],
            'help_request': [
                'ساعدني', 'مساعدة', 'أريد', 'أحتاج', 'من فضلك', 'رجاءً', 
                'لو سمحت', 'ممكن', 'عايز', 'أقدر', 'كيف'
            ],
            'confusion': [
                'ما فهمت', 'مش فاهم', 'غير واضح', 'معقد', 'صعب الفهم', 
                'ما أعرف', 'محتار', 'مش عارف'
            ],
            'gratitude': [
                'شكرا', 'شكرًا', 'مشكور', 'شاكر', 'ممنون', 'أشكرك', 
                'جزاك الله خير', 'بارك الله فيك'
            ]
        }
    
    def _load_question_patterns(self) -> Dict[str, List[str]]:
        """تحميل أنماط الأسئلة"""
        return {
            'definition': ['ما هو', 'ما هي', 'ماهو', 'ماهي', 'عرف', 'تعريف', 'معنى'],
            'explanation': ['كيف', 'اشرح', 'وضح', 'فسر', 'بين', 'أعطني', 'علمني'],
            'reason': ['لماذا', 'ليش', 'السبب', 'لأن', 'علل', 'ما السبب'],
            'location': ['أين', 'وين', 'مكان', 'موقع', 'مكانها', 'موقعها'],
            'time': ['متى', 'وقت', 'تاريخ', 'زمن', 'سنة', 'يوم', 'ساعة'],
            'person': ['من', 'مين', 'شخص', 'إنسان', 'رجل', 'امرأة'],
            'quantity': ['كم', 'عدد', 'مقدار', 'حجم', 'كمية', 'مساحة'],
            'yes_no': ['هل', 'أ', 'يا ترى', 'ممكن', 'صحيح', 'خطأ'],
            'comparison': ['أيهما', 'أفضل', 'الفرق', 'مقارنة', 'اختلاف', 'أحسن'],
            'mathematical': ['احسب', 'حل', 'مشتق', 'تكامل', 'معادلة', 'رياضية', '+', '-', '*', '/', '=', '^']
        }
    
    def _load_context_templates(self) -> Dict[str, str]:
        """تحميل قوالب السياق"""
        return {
            'definition': """أنت خبير تعليمي متخصص في التعريفات. 
            قدم تعريفاً شاملاً ومفصلاً مع أمثلة وتوضيحات عملية.
            استخدم لغة بسيطة وواضحة مع التدرج من البسيط إلى المعقد.""",
            
            'explanation': """أنت معلم ماهر متخصص في الشرح والتوضيح.
            اشرح بالتفصيل والخطوات مع استخدام أمثلة وتشبيهات مفهومة.
            قسم الإجابة إلى نقاط واضحة ومرتبة منطقياً.""",
            
            'reason': """أنت محلل عميق متخصص في تفسير الأسباب والعوامل.
            وضح الأسباب والعوامل المؤثرة بشكل منطقي ومفصل.
            اربط الأسباب بالنتائج وقدم السياق الكامل.""",
            
            'location': """أنت جغرافي خبير متخصص في المعلومات المكانية.
            حدد المكان بدقة مع وصف الموقع والمعلومات الجغرافية المهمة.
            اذكر المناطق المحيطة والخصائص الجغرافية.""",
            
            'mathematical': """أنت أستاذ رياضيات خبير ومتخصص في تعليم الرياضيات.
            اشرح الحل خطوة بخطوة بطريقة واضحة ومفصلة.
            استخدم التبسيط والتوضيح في كل خطوة.""",
            
            'general': """أنت بسام الذكي 🤖، مساعد ذكي عربي متقدم مع قدرات عاطفية ولغوية عالية.
            قدم إجابة متكاملة ومفصلة وشاملة تغطي جوانب الموضوع المختلفة."""
        }
    
    def detect_question_type(self, question: str) -> str:
        """كشف نوع السؤال بدقة عالية"""
        question_lower = question.lower().strip()
        
        # إزالة علامات الترقيم للتحليل الأفضل
        clean_question = re.sub(r'[^\w\s]', ' ', question_lower)
        
        # فحص كل نوع من الأسئلة
        for q_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if pattern in clean_question:
                    return q_type
        
        return 'general'
    
    def detect_emotion(self, text: str) -> Tuple[str, float]:
        """كشف المشاعر مع درجة الثقة"""
        text_lower = text.lower().strip()
        clean_text = re.sub(r'[^\w\s]', ' ', text_lower)
        
        emotion_scores = {}
        
        # حساب درجات المشاعر
        for emotion, patterns in self.emotion_patterns.items():
            score = 0
            for pattern in patterns:
                # عدد مرات الظهور مع وزن
                occurrences = len(re.findall(r'\b' + pattern + r'\b', clean_text))
                score += occurrences
            
            if score > 0:
                # تطبيع النتيجة
                emotion_scores[emotion] = score / len(patterns)
        
        if emotion_scores:
            # أقوى مشاعر
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            confidence = emotion_scores[dominant_emotion]
            return dominant_emotion, confidence
        
        return 'neutral', 0.0
    
    def generate_emotional_response(self, emotion: str, confidence: float) -> str:
        """توليد رد عاطفي مناسب"""
        if confidence < 0.3:  # ثقة منخفضة
            return ""
        
        responses = {
            'positive': [
                '😊 أسعدني أنك راضٍ! كيف يمكنني مساعدتك أكثر؟',
                '🌟 رائع! أنا سعيد لأنني أستطيع مساعدتك.',
                '❤️ شكراً لك! أشعر بالفخر عندما أساعدك.',
                '🎉 ممتاز! دعني أقدم لك المزيد من المساعدة.'
            ],
            'negative': [
                '😟 أعتذر إذا كان هناك أي إزعاج. دعني أساعدك بشكل أفضل.',
                '💙 أتفهم شعورك. سأبذل قصارى جهدي لمساعدتك.',
                '🤗 لا تقلق، سنحل المشكلة معاً خطوة بخطوة.',
                '💪 أفهم الصعوبة. دعني أقدم لك حلولاً مبسطة وواضحة.'
            ],
            'help_request': [
                '🙋‍♂️ بالطبع! أنا هنا لمساعدتك. ما الذي تحتاج إليه؟',
                '✋ أكيد! أخبرني بالتفصيل كيف يمكنني مساعدتك.',
                '💪 معاً سنجد الحل! اطرح سؤالك بوضوح.',
                '🎯 تمام! أنا جاهز لتقديم أفضل مساعدة ممكنة.'
            ],
            'confusion': [
                '🤔 دعني أوضح الأمر بطريقة أبسط وأوضح.',
                '💡 سأشرح لك بتفصيل أكبر ووضوح أكثر.',
                '📚 لا مشكلة! سأعيد الشرح بطريقة مختلفة ومبسطة.',
                '🔍 دعني أعطيك شرحاً مفصلاً وأمثلة واضحة.'
            ],
            'gratitude': [
                '🥰 العفو! أنا سعيد جداً لأنني ساعدتك.',
                '😊 لا شكر على واجب! هذا عملي وأحبه.',
                '🌟 تسلم! أي وقت تحتاج مساعدة أنا هنا.',
                '❤️ الله يعطيك العافية! دائماً في خدمتك.'
            ]
        }
        
        if emotion in responses:
            return random.choice(responses[emotion])
        
        return ""
    
    def analyze_text_complexity(self, text: str) -> str:
        """تحليل تعقيد النص لتحديد مستوى الإجابة المطلوب"""
        word_count = len(text.split())
        technical_terms = len(re.findall(r'\b(?:تقني|علمي|تكنولوجيا|برمجة|هندسة|طب|فيزياء|كيمياء|رياضيات)\b', text.lower()))
        
        if word_count < 5:
            return 'simple'
        elif word_count < 15 and technical_terms == 0:
            return 'medium'
        else:
            return 'advanced'
    
    def create_enhanced_context(self, question: str, question_type: str, emotion: str) -> str:
        """إنشاء سياق محسن للسؤال"""
        base_context = self.context_templates.get(question_type, self.context_templates['general'])
        complexity = self.analyze_text_complexity(question)
        
        # تخصيص السياق حسب التعقيد
        complexity_additions = {
            'simple': "استخدم لغة بسيطة جداً ومفردات سهلة. قدم أمثلة من الحياة اليومية.",
            'medium': "استخدم لغة متوسطة التعقيد مع شرح المصطلحات الصعبة.",
            'advanced': "يمكنك استخدام المصطلحات التقنية مع توضيحها بالتفصيل."
        }
        
        # إضافة التوجيهات العاطفية
        emotional_guidance = {
            'help_request': "كن إيجابياً ومشجعاً في ردك.",
            'confusion': "كن صبوراً ووضح الأمور بطرق متعددة.",
            'negative': "كن مريحاً ومطمئناً في أسلوبك.",
            'positive': "شارك الإيجابية واستمر في تقديم الأفضل."
        }
        
        enhanced_context = f"""
{base_context}

مستوى التعقيد المطلوب: {complexity_additions[complexity]}

{emotional_guidance.get(emotion, "")}

مبادئ الإجابة المتقدمة:
- ابدأ بإجابة مختصرة ثم فصل
- استخدم التنسيق والترقيم لتنظيم المعلومات  
- أضف أمثلة عملية من الواقع العربي
- اختتم بسؤال للمتابعة أو اقتراح للتوسع
- استخدم الرموز التعبيرية بحكمة لإضافة الحيوية
- قدم مراجع أو مصادر إضافية عند الإمكان
"""
        
        return enhanced_context
    
    def create_detailed_summary(self, content: str, max_sentences: int = 5) -> str:
        """إنشاء تلخيص مفصل ومنظم"""
        if not content or len(content.strip()) < 100:
            return content
        
        # تقسيم المحتوى إلى جمل
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if len(sentences) <= max_sentences:
            return content
        
        # اختيار الجمل المهمة (أول جملة، جمل تحتوي على كلمات مفتاحية، آخر جملة)
        important_sentences = []
        
        # الجملة الأولى دائماً
        if sentences:
            important_sentences.append(sentences[0])
        
        # البحث عن جمل تحتوي على كلمات مفتاحية
        keywords = ['مهم', 'أساسي', 'رئيسي', 'يجب', 'ضروري', 'أولاً', 'ثانياً', 'أخيراً', 'خلاصة', 'نتيجة']
        for sentence in sentences[1:-1]:
            if any(keyword in sentence for keyword in keywords) and len(important_sentences) < max_sentences - 1:
                important_sentences.append(sentence)
        
        # الجملة الأخيرة إذا كان هناك مساحة
        if len(sentences) > 1 and len(important_sentences) < max_sentences:
            important_sentences.append(sentences[-1])
        
        return '. '.join(important_sentences) + '.'
    
    def generate_follow_up_questions(self, topic: str, question_type: str) -> List[str]:
        """توليد أسئلة متابعة ذكية"""
        follow_ups = {
            'definition': [
                f'هل تريد أمثلة أكثر عن {topic}؟',
                f'ما رأيك في معرفة تطبيقات {topic} العملية؟',
                f'هل تحب أن نتحدث عن تاريخ {topic}؟'
            ],
            'explanation': [
                f'هل الشرح واضح أم تحتاج تفصيل أكثر في نقطة معينة؟',
                f'تحب نشوف أمثلة إضافية على {topic}؟',
                f'فيه جزء معين من الشرح تحتاج توضيح أكتر فيه؟'
            ],
            'mathematical': [
                'هل تريد حل مسائل مشابهة؟',
                'تحب أشرح لك طريقة أخرى لحل نفس النوع؟',
                'عندك أسئلة على خطوات الحل؟'
            ],
            'general': [
                f'هل هناك جانب معين من {topic} تريد التوسع فيه؟',
                'أي معلومة إضافية تحتاجها؟',
                'هل الإجابة أجابت على سؤالك بالكامل؟'
            ]
        }
        
        return follow_ups.get(question_type, follow_ups['general'])
    
    def enhance_arabic_text(self, text: str) -> str:
        """تحسين النص العربي للقراءة والفهم"""
        if not text:
            return text
        
        # إضافة التشكيل للكلمات المهمة
        important_words = {
            'الله': 'اللهُ',
            'محمد': 'محمدٌ',
            'القران': 'القرآن',
            'الاسلام': 'الإسلام'
        }
        
        enhanced_text = text
        for word, enhanced in important_words.items():
            enhanced_text = re.sub(rf'\b{word}\b', enhanced, enhanced_text, flags=re.IGNORECASE)
        
        # تحسين علامات الترقيم
        enhanced_text = re.sub(r'([.!?])\s*', r'\1 ', enhanced_text)  # مسافة بعد علامات الترقيم
        enhanced_text = re.sub(r'\s+', ' ', enhanced_text)  # إزالة المسافات الزائدة
        enhanced_text = enhanced_text.strip()
        
        return enhanced_text