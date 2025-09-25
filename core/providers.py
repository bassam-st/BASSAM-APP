# core/providers.py
import os
import asyncio
from typing import Optional

import httpx

# ---------- Gemini (Google Generative AI) ----------
# نستخدم مكتبة google-generativeai إذا كانت متاحة، وإلا REST عبر httpx
_GEMINI_KEY = os.getenv("GEMINI_API_KEY")
try:
    import google.generativeai as genai
    _HAS_GEMINI_SDK = True
except Exception:
    _HAS_GEMINI_SDK = False


async def ask_gemini(prompt: str, model: str = "gemini-1.5-flash") -> Optional[str]:
    if not _GEMINI_KEY:
        return None
    if _HAS_GEMINI_SDK:
        genai.configure(api_key=_GEMINI_KEY)
        loop = asyncio.get_event_loop()

        def _sync_call():
            m = genai.GenerativeModel(model)
            r = m.generate_content(prompt)
            return r.text if hasattr(r, "text") else None

        return await loop.run_in_executor(None, _sync_call)
    # REST fallback (نادراً تحتاجه)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={_GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None


# ---------- Groq (Llama/Mixtral سريع) ----------
_GROQ_KEY = os.getenv("GROQ_API_KEY")

async def ask_groq(prompt: str, model: str = "llama-3.1-8b-instant") -> Optional[str]:
    if not _GROQ_KEY:
        return None
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {_GROQ_KEY}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 400:
            return None
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None


# ---------- Hugging Face Inference ----------
_HF_KEY = os.getenv("HF_API_KEY")
# اخترنا نموذج حواري خفيف يدعم العربية بشكل مقبول:
_HF_MODEL = os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct")

async def ask_hf(prompt: str, model: Optional[str] = None) -> Optional[str]:
    if not _HF_KEY:
        return None
    model_id = model or _HF_MODEL
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {"Authorization": f"Bearer {_HF_KEY}"}
    # نستخدم واجهة text-generation البسيطة
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 256, "temperature": 0.3}}
    async with httpx.AsyncClient(timeout=90, headers=headers) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 400:
            return None
        data = r.json()
        # الاستجابة قد تكون قائمة أو dict حسب النموذج
        if isinstance(data, list) and data and "generated_text" in data[0]:
            # بعض النماذج ترجع prompt+الإكمال سويًا
            out = data[0]["generated_text"]
            return out[len(prompt):].strip() if out.startswith(prompt) else out
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        # بعض واجهات HF ترجع {"choices":[{"text":...}]}
        try:
            return data["choices"][0]["text"]
        except Exception:
            return None


# ---------- OpenAI (اختياري مدفوع قليلًا) ----------
_OPENAI_KEY = os.getenv("OPENAI_API_KEY")

async def ask_openai(prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    if not _OPENAI_KEY:
        return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {_OPENAI_KEY}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=60, headers=headers) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 400:
            return None
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return None
