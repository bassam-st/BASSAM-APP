# src/brain/agent.py — وكيل مجاني خفيف

import re
import ast
import math
from typing import List

# بحث ويب مجاني
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import httpx

# --- أدوات مساعدة ---

MATH_ALLOWED_NAMES = {
    k: getattr(math, k) for k in dir(math) if not k.startswith("_")
}
MATH_ALLOWED_NAMES.update({"pi": math.pi, "e": math.e})

def _safe_eval(expr: str) -> float:
    """
    تقييم تعبير رياضي بأمان باستخدام AST (بدون eval المباشر).
    يدعم + - * / ** () وأغلب دوال math مثل sqrt, sin ...
    """
    node = ast.parse(expr, mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Num):      # 3.8-
            return n.n
        if isinstance(n, ast.Constant): # 3.8+
            if isinstance(n.value, (int, float)):
                return n.value
            raise ValueError("نوع ثابت غير مسموح")
        if isinstance(n, ast.BinOp):
            left, right = _eval(n.left), _eval(n.right)
            if isinstance(n.op, ast.Add):  return left + right
            if isinstance(n.op, ast.Sub):  return left - right
            if isinstance(n.op, ast.Mult): return left * right
            if isinstance(n.op, ast.Div):  return left / right
            if isinstance(n.op, ast.Pow):  return left ** right
            raise ValueError("عملية غير مدعومة")
        if isinstance(n, ast.UnaryOp):
            val = _eval(n.operand)
            if isinstance(n.op, ast.UAdd): return +val
            if isinstance(n.op, ast.USub): return -val
            raise ValueError("عملية وحيدة غير مدعومة")
        if isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name):
                raise ValueError("استدعاء غير مسموح")
            name = n.func.id
            if name not in MATH_ALLOWED_NAMES:
                raise ValueError(f"دالة غير مسموح بها: {name}")
            args = [_eval(a) for a in n.args]
            return MATH_ALLOWED_NAMES[name](*args)
        if isinstance(n, ast.Name):
            if n.id in MATH_ALLOWED_NAMES:
                return MATH_ALLOWED_NAMES[n.id]
            raise ValueError(f"اسم غير مسموح: {n.id}")
        if isinstance(n, ast.Tuple):
            return tuple(_eval(elt) for elt in n.elts)
        raise ValueError("صيغة غير مدعومة")
    return _eval(node)

def _looks_math(q: str) -> bool:
    # بسيط: أرقام + رموز حسابية أو دوال رياضية معروفة
    return bool(re.search(r"[0-9πpie\+\-\*/\^\(\)]", q)) or any(
        kw in q.lower() for kw in ["sqrt", "sin", "cos", "tan", "log", "ln", "جذر", "أس", "تربيع"]
    )

def _is_search(q: str) -> bool:
    kws = ["ابحث", "بحث", "ما هو", "من هو", "أين", "متى", "how", "what", "who", "where", "when"]
    return any(kw in q.lower() for kw in kws)

def _fetch_text(url: str, timeout=8) -> str:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            # نأخذ نصًا نظيفًا ومختصرًا
            for s in soup(["script", "style", "noscript"]):
                s.extract()
            text = " ".join(soup.get_text(" ").split())
            return text[:4000]
    except Exception:
        return ""

def _summarize(snippets: List[str], limit_chars=400) -> str:
    text = " ".join([s for s in snippets if s]).strip()
    if not text:
        return "لم أجد معلومات كافية."
    return (text[:limit_chars] + "…") if len(text) > limit_chars else text

# --- المنطق الرئيسي المجاني ---

def run_free_agent(query: str) -> str:
    q = query.strip()

    # 1) رياضيات
    if _looks_math(q):
        # حاول استخراج التعبير (إزالة كلمات عربية شائعة)
        expr = q.replace("ما هو", "").replace("احسب", "").replace("=", "")
        expr = expr.replace("الجذر", "sqrt").replace("جذر", "sqrt")
        expr = expr.replace("^", "**").replace("π", "pi")
        try:
            val = _safe_eval(expr)
            return f"النتيجة الحسابية: {val}"
        except Exception as e:
            # لو فشل، نكمل كبحث
            pass

    # 2) بحث ويب
    if _is_search(q):
        results = []
        try:
            with DDGS() as ddg:
                for hit in ddg.text(q, max_results=5):
                    title = hit.get("title", "")
                    href  = hit.get("href", "")
                    body  = hit.get("body", "")
                    page  = _fetch_text(href)
                    snippet = f"{title}. {body}. {page[:600]}"
                    results.append(snippet)
        except Exception:
            results = []

        summary = _summarize(results, limit_chars=500)
        return f"ملخص سريع:\n{summary}\n\n(نتائج مجمّعة من بحث ويب مجاني)"

    # 3) رد افتراضي
    return f"تم استلام سؤالك بنجاح: {q}\n(وضع مجاني خفيف — اسأل عن عملية حسابية أو اطلب بحثًا)"
