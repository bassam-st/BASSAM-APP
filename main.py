# main.py — Bassam الذكي v4.1 (Web-first • Math • RAG • PDF/Image • Download • Deep Search)

from fastapi import FastAPI, Request, Query, Body, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re, shutil
from typing import List, Dict, Any
from urllib.parse import urlparse

# -------- Web / Text --------
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from readability import Document

# -------- Summarization (sumy) --------
try:
    from sumy.parsers.text import PlaintextParser
except Exception:
    from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# -------- Math --------
from sympy import symbols, sympify, diff, integrate, simplify

# -------- RAG BM25 --------
from rank_bm25 import BM25Okapi

# -------- Files / PDF / Images --------
from pypdf import PdfReader
from PIL import Image

# -------- HTTP client (download/proxy) --------
import httpx


# =========================
# 0) إعداد التطبيق والمجلدات
# =========================
app = FastAPI(title="Bassam الذكي 🤖", version="4.1")

DATA_DIR     = "data"
NOTES_DIR    = os.path.join(DATA_DIR, "notes")
FILES_DIR    = "files"
UPLOADS_DIR  = os.path.join(FILES_DIR, "uploads")
LEARN_PATH   = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH   = os.path.join(DATA_DIR,  "usage_stats.json")

for d in (DATA_DIR, NOTES_DIR, FILES_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# =========================
# 1) أدوات مساعدة
# =========================
def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text or "", Tokenizer("arabic"))
        sents = TextRankSummarizer()(parser.document, max_sentences)
        return " ".join(map(str, sents)) if sents else (text or "")[:400]
    except Exception:
        return (text or "")[:400]

def _tokenize_ar(s: str) -> List[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", (s or "").lower())

def ensure_safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name or "")
    return name[:120] or f"file_{int(time.time())}"

def log_usage():
    try:
        if not os.path.exists(USAGE_PATH):
            with open(USAGE_PATH, "w", encoding="utf-8") as f:
                json.dump({"requests": 0, "last_time": int(time.time())}, f)
        with open(USAGE_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["requests"] = int(data.get("requests", 0)) + 1
            data["last_time"] = int(time.time())
            f.seek(0); json.dump(data, f); f.truncate()
    except Exception:
        pass

def answer_bubble(text: str, sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = {"type": "chat", "answer": text.strip()}
    if sources:
        out = []
        for s in sources:
            s = dict(s)
            s["summary"] = summarize_text(s
