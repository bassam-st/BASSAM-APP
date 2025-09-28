# main.py — Bassam الذكي v3.3
# بحث ذكي + تلخيص + RAG من ملفاتك + رياضيات + واجهة عربية
from fastapi import FastAPI, Request, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, re, html, time, json, math, requests
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from sympy import symbols, sympify, diff, integrate, simplify, sin, cos, tan, log, exp

# ✅ تصحيح استيراد sumy (الإصدار الجديد)
from sumy.parsers.text import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# قاعدة البيانات المحلية للـ RAG
DATA_DIR = "data"

app = FastAPI(title="Bassam الذكي 🤖", version="3.3")

# ربط المجلدات
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# كاش محلي مؤقت
cache = Cache(directory=".cache")


# 🧮 الذكاء الرياضي المحلي
def solve_math(expr: str):
    try:
        x = symbols('x')
        parsed = sympify(expr)
        deriv = diff(parsed, x)
        integ = integrate(parsed, x)
        simp = simplify(parsed)
        return {
            "input": str(parsed),
            "simplified": str(simp),
            "derivative": str(deriv),
            "integral": str(integ)
        }
    except Exception as e:
        return {"error": f"تعذر تحليل المعادلة: {e}"}


# 🧠 الذكاء النصي والتلخيص
def summarize_text(text: str):
    parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
    summarizer = TextRankSummarizer()
    sentences = summarizer(parser.document, 3)
    return " ".join(str(s) for s in sentences)


# 📚 البحث في ملفات المعرفة المحلية (RAG)
def rag_search(query: str):
    results = []
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".md") or file.endswith(".txt"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            results.append({
                                "file": file,
                                "snippet": content[:400] + "..."
                            })
                except:
                    pass
    return results


# 🌐 البحث على الإنترنت (DuckDuckGo)
def web_search(query: str):
    with DDGS() as ddgs:
        return [{"title": r["title"], "link": r["href"], "snippet": r["body"]}
                for r in ddgs.text(query, region="xa-ar", max_results=3)]


# ========================
# واجهات التطبيق
# ========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "version": "v3.3"})


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/ask")
def ask(q: str = Query(..., description="سؤالك هنا")):
    q = q.strip()
    if not q:
        return {"error": "يرجى كتابة السؤال"}

    # رياضيات
    if any(x in q for x in ["sin", "cos", "tan", "log", "exp", "x", "^"]):
        return {"type": "math", "result": solve_math(q)}

    # بحث في ملفات المعرفة (RAG)
    rag_results = rag_search(q)
    if rag_results:
        return {"type": "rag", "results": rag_results[:3]}

    # بحث من الإنترنت
    web_results = web_search(q)
    if web_results:
        summaries = [summarize_text(r["snippet"]) for r in web_results]
        return {"type": "web", "results": web_results, "summaries": summaries}

    return {"msg": "لم أجد نتائج حول سؤالك."}


# ========================
# نقطة تشغيل التطبيق
# ========================
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
