from core.summarizer import smart_summarize
from core.search import deep_search
from core.services.learning import save_feedback, log_search

@app.post("/search")
async def search(q: str = Form(...), want_prices: bool = Form(False)):
    try:
        q_norm = (q or "").strip()
        # 1) نفّذ البحث (بدون await لأن deep_search ليست async)
        results = deep_search(q_norm, include_prices=want_prices)

        # 2) أنشئ ملخّصًا ذكيًا من المقتطفات
        corpus = " ".join(r.get("snippet", "") for r in results)
        summary = smart_summarize(corpus, max_sentences=5) if corpus else ""

        # 3) سجّل التعلّم والبحث (توقيعات متوافقة)
        try:
            log_search(q_norm, [r["url"] for r in results])
            save_feedback(q_norm, summary)
        except Exception as e:
            print(f"[learning/log error] {e}")

        return JSONResponse({
            "answer": summary or "لم أجد إجابة واضحة الآن.",
            "sources": results,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
