# core/summarizer.py — summary + auto-translate to Arabic
from typing import List, Dict
from sumy.parsers.plaintext import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from .arabic_text import to_arabic

def _sumy(text: str, sentences: int = 5) -> str:
    parser = PlainTextParser.from_string(text, Tokenizer("english"))
    summ = TextRankSummarizer()
    sents = summ(parser.document, sentences)
    return " ".join(str(s) for s in sents)

def smart_summarize(passages: List[Dict], query: str, max_chars: int = 3500) -> Dict:
    if not passages:
        return {"ar_answer": to_arabic("لم أجد محتوى كافياً."), "raw": ""}

    # نجمع أهم المقاطع (الأولى عادةً أفضل)
    txt = ""
    for p in passages:
        if len(txt) > max_chars: break
        piece = p.get("text","")
        if piece:
            txt += piece.strip() + "\n"

    # ملخص إنجليزي/عام ثم ترجمة للعربية
    try:
        raw = _sumy(txt, sentences=6)
        if len(raw) < 150: raw = txt[:1200]
    except Exception:
        raw = txt[:1200]

    ar = to_arabic(raw)
    return {"ar_answer": ar, "raw": raw}
