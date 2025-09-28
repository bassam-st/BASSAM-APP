(function () {
  const chat = document.getElementById("chat");
  const qEl  = document.getElementById("q");
  const userEl = document.getElementById("user");

  // حمّل الاسم المخزَّن محليًا
  const saved = localStorage.getItem("bassam_user") || "guest";
  userEl.value = saved;

  function addMsg(text, who="bot") {
    const div = document.createElement("div");
    div.className = `msg ${who}`;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }

  function saveUser() {
    const u = (userEl.value || "guest").trim() || "guest";
    localStorage.setItem("bassam_user", u);
    addMsg(`تم حفظ الاسم: ${u}`, "sys");
  }
  window.saveUser = saveUser;

  async function send() {
    const q = (qEl.value || "").trim();
    const user = (userEl.value || "guest").trim() || "guest";
    if (!q) return;
    qEl.value = "";

    addMsg(q, "me");
    const holder = addMsg("…", "bot");

    // جرّب SSE أولًا
    const url = `/ask/stream?` + new URLSearchParams({ q, user }).toString();
    let usedSSE = false;

    try {
      // إذا المتصفح لا يدعم EventSource، سيرمي خطأ
      const es = new EventSource(url);
      usedSSE = true;

      let buf = "";
      es.onmessage = (e) => {
        buf += (buf ? " " : "") + e.data;
        holder.textContent = buf;
      };
      es.addEventListener("done", () => es.close());
      es.onerror = () => {
        es.close();
        if (!buf) fallbackFetch(q, user, holder);
      };
    } catch (e) {
      // لا يدعم SSE
      fallbackFetch(q, user, holder);
    }

    if (!usedSSE) {
      // متصفح قديم جدًا
      fallbackFetch(q, user, holder);
    }
  }
  window.send = send;

  async function fallbackFetch(q, user, holder) {
    try {
      const r = await fetch("/api/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ q, user })
      });
      const data = await r.json();
      holder.textContent = data.answer || data.result || "لم يصل رد.";
    } catch (e) {
      holder.textContent = "تعذر الحصول على الرد.";
    }
  }

  // Enter لإرسال السؤال
  qEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      send();
    }
  });
})();
