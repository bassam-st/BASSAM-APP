# src/brain/omni_brain.py — عقل بسام الذكي (تلخيص + بحث + فهم)
import re, requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from readability import Document
from diskcache import Cache

# ===== استيراد آمن لمكتبة sumy =====
try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.text_rank import TextRankSummarizer
except Exception as e:
    PlaintextParser = None
    Tokenizer = None
    TextRankSummarizer = None

cache = Cache("cache")

# ===== دالة تلخيص النص =====
def summarize_text(text: str, sentences_count: int = 3):
    if PlaintextParser and Tokenizer and TextRankSummarizer:
        try:
            parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
            summarizer = TextRankSummarizer()
            summary = summarizer(parser.document, sentences_count)
            return " ".join([str(s) for s in summary])
        except Exception as e:
            return simple_summary(text)
    else:
        return simple_summary(text)

def simple_summary(text: str):
    sents = re.split(r'[.!؟\n]', text)
    sents = [s.strip() for s in sents if s.strip()]
    return " ".join(sents[:3])

# ===== دالة الإجابة العامة =====
def omni_answer(query: str) -> str:
    query = (query or "").strip()
    if not query:
        return "يرجى كتابة سؤالك أولاً ✍️"

    key = f"ans::{query}"
    if key in cache:
        return cache[key]

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="xa-ar", max_results=5))
        if not results:
            return "لم أجد نتائج حول سؤالك."
        top = results[0]
        url = top.get("href", "")
        title = top.get("title", "")
        body = top.get("body", "")
        try:
            page = requests.get(url, timeout=10)
            doc = Document(page.text)
            text = BeautifulSoup(doc.summary(), "html.parser").get_text()
            summary = summarize_text(text)
        except Exception:
            summary = body
        answer = f"🔹 {title}\n\n{summary}\n\n🌐 المصدر: {url}"
    except Exception as e:
        answer = f"⚠️ خطأ أثناء المعالجة: {e}"

    cache[key] = answer
    return answer
