# omni_brain.py — المحرك الذكي للإجابات (Brain) في مشروع Bassam App
# يعتمد على التلخيص والفهم السياقي من بيانات RAG أو الويب

import re
from sumy.parsers.plaintext import PlainTextParser   # ✅ الاستيراد الصحيح
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer


def clean_text(text: str) -> str:
    """تنظيف النص من الرموز الزائدة والأسطر الفارغة."""
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def summarize_text(text: str, sentences_count: int = 5, lang: str = "arabic") -> str:
    """تلخيص النص بطريقة TextRank."""
    try:
        parser = PlainTextParser.from_string(text, Tokenizer(lang))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, sentences_count)
        summarized = "\n".join([str(s) for s in summary]).strip()
        return summarized if summarized else text
    except Exception as e:
        print(f"[Brain summarize_text] ❌ Error: {e}")
        return text


def merge_contexts(contexts):
    """دمج النصوص المستخرجة من RAG في نص واحد طويل قبل التحليل."""
    combined = ""
    for c in contexts:
        text = c.get("text", "")
        if text:
            combined += "\n" + clean_text(text)
    return combined.strip()


def answer(query: str, context: list[dict]) -> str:
    """
    دالة رئيسية تُستخدم من main.py
    - تأخذ السؤال (query)
    - وسياقات النصوص المستخرجة من RAG (context)
    - تُرجع إجابة ذكية مختصرة بناءً على المحتوى
    """
    try:
        # دمج السياقات في نص واحد
        combined_context = merge_contexts(context)
        if not combined_context:
            return "لم يتم العثور على معلومات كافية للإجابة."

        # تلخيص النصوص أولًا لتقليل الضوضاء
        summary = summarize_text(combined_context, sentences_count=8)

        # محاولة استخراج فقرة مرتبطة بالسؤال
        pattern = re.compile(rf".{{0,100}}{re.escape(query)}.{{0,300}}", re.IGNORECASE)
        matches = pattern.findall(summary)
        if matches:
            extracted = " ".join(matches)
            extracted = clean_text(extracted)
            final_answer = summarize_text(extracted, sentences_count=3)
        else:
            final_answer = summarize_text(summary, sentences_count=5)

        # فلترة الرد الأخير
        if len(final_answer) < 40:
            final_answer += "\n\n📘 تم توليد الإجابة بناءً على المحتوى المتاح."

        return final_answer.strip()

    except Exception as e:
        print(f"[Brain answer] ❌ Error: {e}")
        return "حدث خطأ أثناء توليد الإجابة، حاول مرة أخرى لاحقًا."
