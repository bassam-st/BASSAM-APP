# core/ocr.py
import os
import httpx
from typing import Optional

HF_API_KEY = os.getenv("HF_API_KEY")
HF_OCR_MODEL = os.getenv("HF_OCR_MODEL", "microsoft/trocr-base-printed")

async def ocr_image_with_hf(image_bytes: bytes) -> Optional[str]:
    """
    OCR عبر HuggingFace Inference (TrOCR).
    يعيد النص المستخرج أو None عند الفشل.
    """
    if not HF_API_KEY:
        return None

    url = f"https://api-inference.huggingface.co/models/{HF_OCR_MODEL}?wait_for_model=true"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(url, headers=headers, content=image_bytes)
            if r.status_code >= 400:
                return None
            data = r.json()
            # صيغ الإخراج تختلف، نحاول الأكثر شيوعًا:
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"].strip()
            if isinstance(data, dict) and "text" in data:
                return data["text"].strip()
            return None
    except Exception:
        return None
