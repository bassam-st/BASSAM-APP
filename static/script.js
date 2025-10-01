// ===== Helpers =====
async function postJSON(url, data) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(data)
  });
  return r.json();
}

function el(id){ return document.getElementById(id); }

// يحوّل أي نص يحوي روابط إلى <a> تفتح في تبويب جديد
function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s)]+|(?:www\.)[^\s)]+)/g;
  return String(text || "")
    .replace(urlRegex, (m) => {
      const url = m.startsWith("http") ? m : `https://${m}`;
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${m}</a>`;
    });
}

// ===== Search =====
async function doSearch(e){
  e.preventDefault();
  el("answer").textContent = "… جاري البحث";
  el("sources").innerHTML = "";
  const q = el("q").value.trim();
  const want_prices = el("want_prices").checked;

  try{
    const res = await postJSON("/search", { q, want_prices });
    if(!res.ok){ throw new Error(res.error || "search_failed"); }

    el("latency").textContent = `الوقت: ${res.latency_ms}ms`;

    // عرض الإجابة مع تحويل الروابط إلى <a>
    el("answer").innerHTML = linkify(res.answer || "—");

    // عرض المصادر كرLinks حقيقية
    const srcs = (res.sources || []).map(s => {
      const url = s.url || "";
      const title = s.title || url;
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`;
    });
    el("sources").innerHTML = srcs.length ? srcs.join("<br/>") : "—";
  }catch(err){
    el("answer").textContent = "حدث خطأ في البحث";
    console.error(err);
  }
}

// ===== People / Profiles =====
async function doPeople(e){
  e.preventDefault();
  el("profiles").innerHTML = "…";
  const name = el("name").value.trim();

  try{
    const res = await postJSON("/people", { name });
    if(!res.ok){ throw new Error(res.error || "people_failed"); }

    const items = (res.sources || []).map(s => {
      const url = s.url || "";
      const title = s.title || url;
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`;
    });

    el("profiles").innerHTML = items.length ? items.join("<br/>") : "لا توجد نتائج.";
  }catch(err){
    el("profiles").textContent = "حدث خطأ";
    console.error(err);
  }
}

// ===== Event bindings =====
document.getElementById("searchForm").addEventListener("submit", doSearch);
// إصلاح المعرف ليتوافق مع index.html
document.getElementById("profileForm").addEventListener("submit", doPeople);
