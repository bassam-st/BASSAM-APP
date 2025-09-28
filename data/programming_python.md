# برمجة بايثون — سريعة
## أساسي
```python
# قراءة/كتابة ملف نصي
with open("notes.txt","w",encoding="utf-8") as f: f.write("hello")
with open("notes.txt","r",encoding="utf-8") as f: print(f.read())
