# main.py — Bassam App (Render-ready, free search)

import os, time, traceback
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# وحداتنا
from core.search import deep_search, people_search
from core.utils import ensure_dirs

# مجلدات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
ensure_dirs(TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, CACHE_DIR)

# FastAPI
app = FastAPI(title="Bassam — Deep Search")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ===== Helpers =====
def _parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on", "t"}

def _simple_summarize(text: str, max_sentences: int = 5) -> str:
    import re
    if not text:
        return ""
    sents = [s.strip() for s in re.split(r"(?<=[.!؟\?])\s+", text) if s.strip()]
    if len(sents) <= max_sentences:
        return " ".join(sents)
    def score(s: str) -> float:
        words = re.findall(r"\w+", s.lower())
        return 0.7 * len(s) + 0.3 * len(set(words))
    ranked = sorted(sents, key=score, reverse=True)[:max_sentences]
    ranked.sort(key=lambda s: sents.index(s))
    return " ".join(ranked)

def _sources_to_text(sources: List[Dict], limit: int = 12) -> str:
    parts = []
    for s in (sources or [])[:limit]:
        snip = s.get("snippet") or s.get("body") or ""
        if snip:
            parts.append(snip)
    return " ".join(parts)


# ===== Routes =====
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"ok": True}


# ===== API: Search =====
@app.post("/search")
async def search_endpoint(
    request: Request,
    q: Optional[str] = Form(None),
    want_prices: Optional[bool] = Form(False),
):
    t0 = time.time()
    try:
        if not q:
            try:
                body = await request.json()
            except Exception:
                body = {}
            q = (body.get("q") or "").strip()
            want_prices = _parse_bool(body.get("want_prices"))

        q = (q or "").strip()
        if not q:
            return JSONResponse({"ok": False, "error": "query_is_empty"}, status_code=400)

        sources = deep_search(q, include_prices=_parse_bool(want_prices)) or []
        blob = _sources_to_text(sources, limit=12)
        answer = _simple_summarize(blob, max_sentences=5) or "تم العثور على نتائج — راجع الروابط."

        return JSONResponse({
            "ok": True,
            "latency_ms": int((time.time() - t0) * 1000),
            "answer": answer,
            "sources": [{"title": s.get("title") or s.get("url"), "url": s.get("url")} for s in sources[:12]],
        })
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"search_failed:{type(e).__name__}"}, status_code=500)


# ===== API: People =====
@app.post("/people")
async def people_endpoint(
    request: Request,
    name: Optional[str] = Form(None),
):
    try:
        if not name:
            try:
                body = await request.json()
            except Exception:
                body = {}
            name = (body.get("name") or "").strip()

        name = (name or "").strip()
        if not name:
            return JSONResponse({"ok": False, "error": "name_is_empty"}, status_code=400)

        results = people_search(name) or []
        return {"ok": True, "sources": [{"title": r.get("title") or r.get("url"), "url": r.get("url")} for r in results[:20]]}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"people_failed:{type(e).__name__}"}, status_code=500)
