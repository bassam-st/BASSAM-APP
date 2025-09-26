# bassam_brain.py — نواة بسام الذكي (نسخة أولية مجانية)
# تعمل محلياً باستخدام TinyLlama أو Mistral (مفتوح المصدر)

import os
from pathlib import Path
from llama_cpp import Llama

# --- تحميل النموذج (مرن) ---
def load_model():
    # المجلد الذي فيه النموذج
    model_path = os.getenv("BASSAM_MODEL", "models/tinyllama-1.1b-chat.gguf")

    if not Path(model_path).exists():
        raise FileNotFoundError(
            f"⚠️ لم أجد النموذج في: {model_path}\n"
            "↪ نزّل TinyLlama من HuggingFace وضعه داخل مجلد models/"
        )

    llm = Llama(
        model_path=model_path,
        n_ctx=2048,   # طول السياق
        n_threads=4,  # عدّل حسب جهازك
        n_batch=256
    )
    return llm

# --- كائن عالمي للنموذج ---
_model = None

def init_brain():
    global _model
    if _model is None:
        _model = load_model()

# --- واجهة بسيطة: سؤال ↔ جواب ---
def ask_brain(prompt: str, system: str = "أنت بسام الذكي. جاوب بالعربية المبسطة."):
    init_brain()
    response = _model(
        prompt=f"{system}\n\nسؤال المستخدم:\n{prompt}",
        max_tokens=400,
        temperature=0.4,
        stop=["</s>"]
    )
    text = response["choices"][0]["text"].strip()
    return text
