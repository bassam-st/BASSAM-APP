# core/services/learning.py
import os, json, time

# المجلد المخصص لحفظ التعلم الذاتي
LEARNING_DIR = "knowledge"
LOG_FILE = "logs/learning_log.json"


def ensure_dirs():
    """يتأكد من وجود المجلدات اللازمة"""
    os.makedirs(LEARNING_DIR, exist_ok=True)
    os.makedirs("logs", exist_ok=True)


def save_feedback(query: str, answer: str):
    """يحفظ تعلم المستخدم"""
    ensure_dirs()
    data = {"time": time.ctime(), "query": query, "answer": answer}
    try:
        # حفظ في ملف رئيسي بسيط
        file_path = os.path.join(LEARNING_DIR, "user_learning.txt")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n\nسؤال: {query}\nجواب: {answer}\n---\n")

        # حفظ أيضًا في JSON log
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    logs = json.load(f)
                except Exception:
                    logs = []
        logs.append(data)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"[LEARNING ERROR] {e}")


def log_search(query: str, summary: str, results: list):
    """يسجل عمليات البحث في سجل منفصل"""
    ensure_dirs()
    try:
        log_path = os.path.join("logs", "search_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.ctime()}]\nسؤال: {query}\nنتيجة: {summary[:500]}...\n---\n")
    except Exception as e:
        print(f"[LOG ERROR] {e}")


def learn_from_sources(source_type: str, text: str):
    """يتعلم من مصادر جديدة (صور / PDF / بحث)"""
    ensure_dirs()
    try:
        file_path = os.path.join(LEARNING_DIR, f"learn_{source_type}.txt")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n# مصدر: {source_type}\n{text}\n---\n")
    except Exception as e:
        print(f"[SOURCE LEARN ERROR] {e}")
