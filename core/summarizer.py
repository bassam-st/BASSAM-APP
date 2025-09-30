# -*- coding: utf-8 -*-
# ملخّص ذكي مع Sumy + آلية احتياطية

from typing import List
import re

# نحاول استخدام sumy، وإن فشلت نستخدم تلخيصًا بسيطًا احتياطيًا
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer
    from sumy.nlp.stemmers import Stemmer
    from sumy.utils import get_stop_words
    _HAS_SUMY = True
except Exception:
    _HAS_SUMY = False


def _split_sentences(text: str) -> List[str]:
    # تقسيم بسيط للجُمل يدعم العربية والإنجليزية
    text = re.sub(r"\s+", " ", (text or "").strip())
    # نقاط، علامات استفهام، تعجب… الخ
    parts = re.split(r"(?<=[\.!\؟\!])\s+", text)
    # إزالة الفراغات الفارغة
    return [p.strip() for p in parts if p.strip()]


def _fallback_summarize(text: str, max_sentences: int = 5) -> str:
    # اختيار الجُمل الأطول/الأكثر معلومات كتلخيص بسيط
    sents = _split_sentences(text)
    if len(sents) <= max_sentences:
        return " ".join(sents)
    # ترتيب بحسب الطول (كتخمين للمعلوماتية) ثم الحفاظ على ترتيبها الأصلي
    top = sorted(range(len(sents)), key=lambda i: len(sents[i]), reverse=True)[:max_sentences]
    top = sorted(top)
    return " ".join(sents[i] for i in top)


def smart_summarize(text: str, max_sentences: int = 5) -> str:
    """
    يُلخّص نصًا طويلًا إلى عدد جُمل محدد.
    - يحاول استخدام Sumy (LSA) باللغة الإنجليزية.
    - عند الفشل أو النص القصير، يستخدم آلية احتياطية بسيطة.
    """
    if not text:
        return ""

    # نص قصير؟ لا نلخّصه
    if len(text) < 500:
        return text.strip()

    if _HAS_SUMY:
        try:
            # Sumy لا يدعم العربية بشكل كامل؛ نستخدم English tokenizer كافتراض
            lang = "english"
            parser = PlaintextParser.from_string(text, Tokenizer(lang))
            summarizer = LsaSummarizer(Stemmer(lang))
            summarizer.stop_words = get_stop_words(lang)
            sents = [str(s) for s in summarizer(parser.document, max_sentences)]
            if sents:
                return " ".join(sents)
        except Exception:
            pass

    # احتياطي
    return _fallback_summarize(text, max_sentences=max_sentences)
