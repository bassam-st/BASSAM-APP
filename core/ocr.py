# core/ocr.py
import base64, httpx, os

HF_TOKEN = os.getenv("HF_TOKEN")  # ضع توكن هاجينغ فيس في متغير بيئة

async def ocr_image_with_hf(image_bytes: bytes) -> str:
    # مثال مبسط لاستخدام نموذج OCR على HF Inference API
    # بدّل الـ endpoint بنموذج OCR مناسب يدعم العربية/الإنجليزية
    endpoint = "https://api-inference.huggingface.co/models/microsoft/trocr-base-printed"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(endpoint, headers=headers, content=image_bytes)
        r.raise_for_status()
        data = r.json()
        # بعض النماذج ترجع [{"generated_text": "..."}]
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        # fallback نصّي
        return str(data)
