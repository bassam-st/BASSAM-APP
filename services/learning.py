# core/services/learning.py
# وحدة تعلم وتحسين ذاتي لتطبيق بسام الذكي
# تحفظ سجل الأسئلة والإجابات وتتعلم منها مستقبلاً

import os, json, time
from datetime import datetime
from typing import Dict, List

# مجلد لحفظ سجل التعلم الذاتي
LOG_DIR = "data/learning_logs"
os.makedirs(LOG_DIR, exist_ok=True)


def save_feedback(query: str, answer: str, feedback: str = "auto") -> None:
    """حفظ نتيجة البحث والإجابة والتغذية الراجعة"""
    log = {
        "query": query,
        "answer": answer,
        "feedback": feedback,
        "timestamp": datetime.now().isoformat(),
    }
    path = os.path.join(LOG_DIR, "feedback_log.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")


def log_search(query: str, sources: List[str]) -> None:
    """تسجيل عمليات البحث والمصادر"""
    log = {
        "query": query,
        "sources": sources,
        "timestamp": datetime.now().isoformat(),
    }
    path = os.path.join(LOG_DIR, "search_log.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")


def learn_from_sources() -> Dict[str, int]:
    """تحليل السجلات لتعلم المواضيع الأكثر بحثًا"""
    counts = {}
    path = os.path.join(LOG_DIR, "search_log.jsonl")
    if not os.path.exists(path):
        return counts

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                q = log.get("query", "")
                for word in q.split():
                    counts[word] = counts.get(word, 0) + 1
            except Exception:
                pass
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def self_improve():
    """آلية بسيطة للتعلم الذاتي عبر تحليل السجلات"""
    stats = learn_from_sources()
    if not stats:
        print("📭 لا توجد بيانات للتعلم بعد.")
        return
    top = list(stats.items())[:10]
    print("📈 أكثر الكلمات بحثًا:")
    for word, freq in top:
        print(f"  - {word}: {freq} مرة")


# (اختياري) يمكن استدعاؤها يدويًا لتحليل الأداء
if __name__ == "__main__":
    self_improve()
