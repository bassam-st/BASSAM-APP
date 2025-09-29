# دليل بسّام البرمجي – مرجع سريع
وسوم: #برمجة #Python #JavaScript #واجهات #خلفية #قواعد_بيانات #ذكاء_اصطناعي #شبكات #DevOps

## مبادئ كتابة كود نظيف
- اكتب دوالًا قصيرة بوظيفة واحدة.
- سمِّ المتغيرات بوضوح: `user_name` بدل `u`.
- غطِّ الوظائف المهمة باختبارات.
- سجّل الأخطاء برسائل واضحة وقابلة للتشخيص.

## Python – أساسيات سريعة
```py
# قراءة ملف
with open("input.txt","r",encoding="utf-8") as f:
    data = f.read()

# REST بسيط
import requests
r = requests.get("https://api.example.com/items", timeout=15)
print(r.status_code, r.json())

# حلقة + توليد قائمة
squares = [i*i for i in range(10)]
