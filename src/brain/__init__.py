# src/brain/__init__.py — طبقة موحَّدة لنداء الذكاء

from .agent import run_free_agent

def safe_run(query: str) -> str:
    """
    نسخة مجانية 100%:
    - إذا كان السؤال حسابي: نحلّه بأمان.
    - إذا كان بحث: نبحث ونلخّص.
    - غير ذلك: رد افتراضي لطيف.
    """
    return run_free_agent(query)
