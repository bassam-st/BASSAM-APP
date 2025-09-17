# main.py
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from duckduckgo_search import DDGS
from readability import Document
from bs4 import BeautifulSoup
import requests
import re
import html
from diskcache import Cache
from urllib.parse import urlparse

app = FastAPI()
cache = Cache(".cache")  # بسيط لتخفيف الطلبات المتكررة

# صفحة HTML بسيطة تتعامل بالعربية
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>بسام الذكي - بحث ومُلخَص</title>
  <style>
    body {{ font-family: Tahoma, Arial; padding: 18px; max-width:900px; margin:auto; }}
    input[type=text] {{ width:calc(100% - 24px); padding:12px; font-size:16px; }}
    button {{ padding:10px 18px; font-size:16px; margin-top:8px; }}
    .source {{ margin-top:12px; background:#f8f8f8; padding:10px; border-radius:8px; text-align:right; }}
    a {{ color: #0b63c6; text-decoration:none; }}
    .summary {{ background:#eef6ff; padding:12px; border-radius:8px; margin-top:8px; }}
    .footer {{ color:#666; margin-top:18px; font-size:14px; }}
  </style>
</head>
<body>
  <h1>بسام الذكي - بحث وملخّص مجاني</h1>
  <form method="post">
    <input type="text" name="question" placeholder="اكتب سؤالك هنا..." required />
    <div><button type="submit">بحث & تلخيص</button></div>
  </form>

  {result_panel}

  <div class="footer">
    ملاحظة: يستخدم هذا النظام تقنيات سحب صفحات الويب العامة؛ دقّة الإجابات تعتمد على محتوى المواقع ووضوحها. الرجاء استخدامه كأداة مساعدة وليس بديلاً عن مصادر رسمية.
  </div>
</body>
</html>
"""

def sentence_split(text: str):
    # تقسيم بسيط على علامات الترقيم العربية/الإنجليزية
    sentences = re.split(r'(?<=[\.\!\?\؟\!])\s+|\n+', text)
    # نظف الجمل الفارغة
    return [s.strip() for s in sentences if s and len(s.strip())>20][:6]  # نرجع أول 6 جمل طويلة

def fetch_and_extract(url: str, timeout=8):
    """يجلب صفحة ويب ويستخرج النص الرئيسي باستخدام readability"""
    # تجنب النهايات الغريبة
    try:
        headers = {"User-Agent":"Mozilla/5.0 (compatible; Bot/1.0)"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        doc = Document(r.text)
        content_html = doc.summary()
        # ازالة وسوم html إلى نص
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator="\n")
        text = html.unescape(text)
        return text
    except Exception:
        return ""

def summarize_from_text(text: str, max_sentences=3):
    sents = sentence_split(text)
    # خذ أول max_sentences جملة (ابسط وموثوق بدون نماذج خارجية)
    return " ".join(sents[:max_sentences])

def domain_of(url: str):
    try:
        return urlparse(url).netloc
    except:
        return url

@app.get("/", response_class=HTMLResponse)
async def form_get():
    return HTML_TEMPLATE.format(result_panel="")

@app.post("/", response_class=HTMLResponse)
async def form_post(question: str = Form(...)):
    q = question.strip()
    if not q:
        return HTML_TEMPLATE.format(result_panel="")

    cache_key = "q:" + q
    cached = cache.get(cache_key)
    if cached:
        return HTML_TEMPLATE.format(result_panel=cached)

    # 1) بحث DuckDuckGo (مجاني - بدون مفتاح)
    with DDGS() as ddgs:
        results = list(ddgs.text(q, region='wt-wt', safesearch='Off', max_results=6)) or []
    # DDGS returns list of dicts with keys 'title', 'href', 'body'

    panels = []
    combined_summary = []
    count = 0
    for r in results:
        href = r.get("href") or r.get("link") or r.get("url")
        title = r.get("title") or ""
        if not href:
            continue
        # اجلب النص الرئيسي مع caching بسيط لكل مصدر
        ckey = "url:" + href
        page_text = cache.get(ckey)
        if page_text is None:
            page_text = fetch_and_extract(href)
            # خزن إذا وجدنا نص طويل
            if page_text and len(page_text) > 200:
                cache.set(ckey, page_text, expire=60*60*24)  # يومي
        if not page_text:
            continue
        # ملخّص بسيط من الصفحة
        summ = summarize_from_text(page_text, max_sentences=2)
        if not summ:
            continue
        combined_summary.append(f"من {domain_of(href)}: {summ}")
        # بنعرض المصدر كلوحة قصيرة
        panels.append(f'<div class="source"><strong>{html.escape(title)}</strong><br/>' +
                      f'<div style="margin-top:8px;" class="summary">{html.escape(summ)}</div>' +
                      f'<div style="margin-top:8px;"><a target="_blank" href="{html.escape(href)}">عرض المصدر</a></div></div>')
        count += 1
        if count >= 3:
            break

    if not combined_summary:
        panel_html = "<div class='source'>لم أجد مصادر كافية للإجابة. حاول تغيير صيغة السؤال أو اجعل السؤال أكثر تحديدًا.</div>"
        cache.set(cache_key, panel_html, expire=60*5)
        return HTML_TEMPLATE.format(result_panel=panel_html)

    # جمع تلخيص نهائي بسيط (نجمع ملخصات المصادر)
    final_answer = "<br/><br/>".join(combined_summary)

    # لوحة النتائج
    panel_parts = f"""
    <div style="margin-top:18px;">
      <h3>سؤالك:</h3>
      <div class="source">{html.escape(q)}</div>

      <h3 style="margin-top:12px;">الملخّص (منَ المصادر):</h3>
      <div class="summary">{html.escape(final_answer)}</div>

      <h3 style="margin-top:12px;">المصادر:</h3>
      {"".join(panels)}
    </div>
    """
    cache.set(cache_key, panel_parts, expire=60*60)  # cache الإجابة لساعة
    return HTML_TEMPLATE.format(result_panel=panel_parts)


@app.get("/health")
def health():
    return {"ok": True}