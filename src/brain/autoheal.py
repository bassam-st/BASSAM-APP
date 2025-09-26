# brain/autoheal.py
def safe_run(fn, *args, **kwargs):
    """
    يلفّ أي عملية بمحاولة/التقاط أخطاء ويرجع رسالة مفيدة بدل الانهيار.
    """
    try:
        return "ok", fn(*args, **kwargs)
    except Exception as e:
        # هنا يمكن لاحقًا إضافة محاولات إصلاح ذكية
        return "error", f"تم التقاط خطأ: {e}"
