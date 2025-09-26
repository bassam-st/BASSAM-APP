# brain/guard.py
MASTER_PASSWORD = "saa"

def check_auth(secret: str) -> bool:
    """يتحقق أنّ الطلب مصرح له بكلمة السر."""
    return (secret or "").strip() == MASTER_PASSWORD

def sanitize(text: str) -> str:
    """تنظيف بسيط للمدخلات لتفادي أشياء مزعجة."""
    if not isinstance(text, str):
        text = str(text)
    return text.strip()[:5000]
