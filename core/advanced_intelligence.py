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
            حدد المكان بدقة مع وصف الموقع والمعلومات الجغرافية المهمة.""",
            
            'time': """أنت مؤرخ وخبير زمني متخصص في التواريخ والأحداث.
            حدد الوقت والتواريخ بدقة مع السياق التاريخي المناسب.""",
            
            'person': """أنت خبير في السير والتراجم متخصص في الشخصيات.
            قدم معلومات شاملة عن الأشخاص مع إنجازاتهم وسياقهم التاريخي.""",
            
            'quantity': """أنت محلل إحصائي دقيق متخصص في الأرقام والكميات.
            قدم الأرقام الدقيقة مع التحليل والمقارنات المناسبة.""",
            
            'yes_no': """أنت خبير تحليلي يقدم إجابات واضحة ومؤكدة.
            أجب بوضوح مع تقديم الأدلة والمبررات المناسبة.""",
            
            'comparison': """أنت محلل مقارن متخصص في دراسة الفروق والتشابهات.
            قارن بعمق مع إبراز نقاط القوة والضعف والاختلافات الجوهرية.""",
            
            'mathematical': """أنت أستاذ رياضيات خبير ومتخصص في تعليم الرياضيات.
            اشرح الحل خطوة بخطوة بطريقة واضحة ومفصلة.
            استخدم التبسيط والتوضيح في كل خطوة.""",
            
            'general': """أنت بسام الذكي، مساعد ذكي عربي متقدم مع قدرات عاطفية ولغوية عالية.
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
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """تحليل شامل للسؤال يشمل النوع والمشاعر والسياق"""
        if not question.strip():
            return {
                'question_type': 'general',
                'emotional_context': {'primary_emotion': 'neutral', 'confidence': 0.5},
                'complexity_level': 'simple',
                'requires_research': False
            }
        
        # كشف نوع السؤال
        question_type = self.detect_question_type(question)
        
        # كشف المشاعر
        emotion, confidence = self.detect_emotion(question)
        emotional_context = {
            'primary_emotion': emotion,
            'confidence': confidence,
            'emotional_indicators': self._extract_emotional_indicators(question)
        }
        
        # تحديد مستوى التعقيد
        complexity_level = self._assess_complexity(question, question_type)
        
        # تحديد ما إذا كان يحتاج بحث
        requires_research = self._needs_research(question, question_type)
        
        # تحليل متقدم إضافي
        linguistic_features = self._analyze_linguistic_features(question)
        
        return {
            'question_type': question_type,
            'emotional_context': emotional_context,
            'complexity_level': complexity_level,
            'requires_research': requires_research,
            'linguistic_features': linguistic_features,
            'recommended_approach': self._recommend_approach(question_type, emotion),
            'expected_response_length': self._estimate_response_length(complexity_level, question_type)
        }
    
    def _extract_emotional_indicators(self, text: str) -> List[str]:
        """استخراج المؤشرات العاطفية من النص"""
        indicators = []
        text_lower = text.lower()
        
        for emotion, patterns in self.emotion_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    indicators.append(f"{emotion}:{pattern}")
        
        return indicators
    
    def _assess_complexity(self, question: str, question_type: str) -> str:
        """تقييم مستوى تعقيد السؤال"""
        # عوامل التعقيد
        complexity_score = 0
        
        # طول السؤال
        if len(question) > 100:
            complexity_score += 2
        elif len(question) > 50:
            complexity_score += 1
        
        # نوع السؤال
        complex_types = ['mathematical', 'comparison', 'reason', 'explanation']
        if question_type in complex_types:
            complexity_score += 2
        
        # وجود مصطلحات تقنية أو علمية
        technical_indicators = ['معادلة', 'نظرية', 'قانون', 'مبدأ', 'تحليل', 'دراسة']
        for indicator in technical_indicators:
            if indicator in question:
                complexity_score += 1
        
        # أسئلة متعددة الأجزاء
        if '؟' in question and question.count('؟') > 1:
            complexity_score += 1
        
        if complexity_score >= 4:
            return 'complex'
        elif complexity_score >= 2:
            return 'moderate'
        else:
            return 'simple'
    
    def _needs_research(self, question: str, question_type: str) -> bool:
        """تحديد ما إذا كان السؤال يحتاج بحث خارجي"""
        research_indicators = [
            'آخر', 'أحدث', 'جديد', 'حالياً', 'الآن', 'اليوم', 
            'أسعار', 'سعر', 'إحصائيات', 'أرقام حديثة'
        ]
        
        for indicator in research_indicators:
            if indicator in question:
                return True
        
        # أنواع أسئلة تحتاج عادة لبحث
        research_types = ['location', 'time', 'person', 'quantity']
        return question_type in research_types
    
    def _analyze_linguistic_features(self, question: str) -> Dict[str, Any]:
        """تحليل الخصائص اللغوية للسؤال"""
        return {
            'is_arabic': is_arabic(question),
            'word_count': len(question.split()),
            'has_numbers': bool(re.search(r'\d', question)),
            'has_symbols': bool(re.search(r'[+\-*/=<>%]', question)),
            'question_marks': question.count('؟') + question.count('?'),
            'formality_level': self._assess_formality(question)
        }
    
    def _assess_formality(self, text: str) -> str:
        """تقييم مستوى الرسمية في النص"""
        formal_indicators = ['يرجى', 'من فضلك', 'لو سمحت', 'نرجو', 'نتمنى']
        informal_indicators = ['ازاي', 'ايه', 'عايز', 'ممكن']
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in text)
        informal_count = sum(1 for indicator in informal_indicators if indicator in text)
        
        if formal_count > informal_count:
            return 'formal'
        elif informal_count > formal_count:
            return 'informal'
        else:
            return 'neutral'
    
    def _recommend_approach(self, question_type: str, emotion: str) -> str:
        """اقتراح أفضل منهج للإجابة"""
        if emotion == 'confusion':
            return 'step_by_step_simple'
        elif emotion == 'help_request':
            return 'supportive_detailed'
        elif question_type == 'mathematical':
            return 'structured_solution'
        elif question_type in ['definition', 'explanation']:
            return 'comprehensive_educational'
        else:
            return 'balanced_informative'
    
    def _estimate_response_length(self, complexity: str, question_type: str) -> str:
        """تقدير طول الإجابة المناسب"""
        if complexity == 'complex' or question_type == 'mathematical':
            return 'detailed'  # 300+ كلمة
        elif complexity == 'moderate':
            return 'medium'    # 150-300 كلمة
        else:
            return 'concise'   # 50-150 كلمة
    
    def enhance_response(self, response: str, analysis: Dict[str, Any], original_question: str) -> str:
        """تحسين وتهذيب الرد النهائي"""
        if not response or not response.strip():
            return "عذراً، لم أتمكن من توليد إجابة مناسبة."
        
        enhanced = response.strip()
        
        # إضافة مقدمة عاطفية إذا لزم الأمر
        emotion = analysis.get('emotional_context', {}).get('primary_emotion', 'neutral')
        if emotion == 'confusion':
            enhanced = f"أفهم أن الموضوع قد يبدو معقداً، دعني أوضح الأمر:\n\n{enhanced}"
        elif emotion == 'help_request':
            enhanced = f"بكل سرور سأساعدك في هذا الأمر:\n\n{enhanced}"
        elif emotion == 'gratitude':
            enhanced = f"شكراً لثقتك بي، إليك المعلومات المطلوبة:\n\n{enhanced}"
        
        # إضافة سؤال متابعة مناسب
        question_type = analysis.get('question_type', 'general')
        follow_up = self._generate_follow_up_question(question_type, original_question)
        
        if follow_up:
            enhanced += f"\n\n💡 **سؤال للمتابعة:** {follow_up}"
        
        return enhanced
    
    def _generate_follow_up_question(self, question_type: str, original_question: str) -> str:
        """توليد سؤال متابعة مناسب"""
        follow_ups = {
            'definition': [
                "هل تريد أمثلة عملية أو تطبيقات لهذا المفهوم؟",
                "أم تفضل معرفة المزيد عن استخداماته العملية؟"
            ],
            'explanation': [
                "هل تريد شرحاً أكثر تفصيلاً لأي نقطة معينة؟",
                "أم تحتاج أمثلة إضافية للتوضيح؟"
            ],
            'mathematical': [
                "هل تريد رؤية طرق حل أخرى لهذه المسألة؟",
                "أم تحتاج شرحاً أكثر تفصيلاً لأي خطوة؟"
            ],
            'comparison': [
                "هل تريد مقارنة تفصيلية أكثر لجوانب معينة؟",
                "أم تفضل أمثلة عملية للفروق المذكورة؟"
            ],
            'reason': [
                "هل تريد معرفة عوامل أخرى قد تؤثر على هذا الأمر؟",
                "أم تحتاج أمثلة تاريخية أو حديثة؟"
            ]
        }
        
        if question_type in follow_ups:
            import random
            return random.choice(follow_ups[question_type])
        
        # أسئلة عامة للمتابعة
        general_follow_ups = [
            "هل تحتاج توضيحاً إضافياً لأي نقطة؟",
            "أم تريد معرفة المزيد حول موضوع ذي صلة؟",
            "هل هناك جانب آخر تود استكشافه؟"
        ]
        
        import random
        return random.choice(general_follow_ups)
    
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