# core/summarizer.py
# تلخيص بسيط بدون اعتماد على sumy — يعمل عربي/إنجليزي

import re
from collections import Counter

_AR_STOP = {
    "في","من","على","إلى","الى","عن","أن","إن","او","أو","و","ثم","لكن","بل",
    "كان","كانت","يكون","لقد","قد","تم","هذه","هذا","ذلك","تلك","هو","هي",
    "هناك","كما","ما","لا","لم","لن","إنه","أنها","أي","أية","مع","بين","حتى",
}

_EN_STOP = {
    "the","a","an","and","or","but","to","of","in","on","for","with","as",
    "is","it","this","that","these","those","by","from","at","be","are","was","were",
    "have","has","had","not","no","yes","you","we","they","he","she",
}

def _sentences(text: str):
    # يقسم الجمل مع دعم علامات الوقف العربية
    sents = re.split(r"(?<=[\.!\?…؟])\s+", text.strip())
    return [s.strip() for s in sents if s.strip()]

def smart_summarize(text: str, max_sentences: int = 5) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    sents = _sentences(text)
    if len(sents) <= max_sentences:
        return " ".join(sents)

    # تكرارية الكلمات (بدون الوقف)
    tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    stop = _AR_STOP | _EN_STOP
    freq = Counter(t for t in tokens if t not in stop and len(t) > 2)

    def score(sent: str) -> float:
        toks = re.findall(r"\w+", sent.lower(), flags=re.UNICODE)
        if not toks:
            return 0.0
        return sum(freq.get(t, 0) for t in toks) / (len(toks) + 1)

    ranked = sorted(((score(s), i, s) for i, s in enumerate(sents)), reverse=True)
    top = sorted(ranked[:max_sentences], key=lambda x: x[1])  # حافظ على ترتيب الظهور
    return " ".join(s for _, _, s in top)
